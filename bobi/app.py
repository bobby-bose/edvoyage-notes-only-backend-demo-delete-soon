"""BOBI Flask Application - PDF Processing Service with Django Integration
Accepts PDF uploads from Django admin, applies watermarks, returns JSON+Base64 images.
"""
from flask import Flask, request, jsonify
import fitz
import os
import uuid
import base64
import time
import logging
import io
from werkzeug.utils import secure_filename
from watermark import apply_watermark_to_image





logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp_uploads")
LOGO_SVG = os.path.join(BASE_DIR, "logo.svg")

os.makedirs(TEMP_DIR, exist_ok=True)



@app.route("/api/process", methods=["POST"])
def process_flashcard_pdf():
    """API endpoint for Django Flashcard integration"""
    start_time = time.time()
    try:
        if "pdf_file" not in request.files:
            return jsonify({"status": "error", "error": "No pdf_file provided"}), 400
        pdf_file = request.files["pdf_file"]
        flashcard_id = request.form.get("flashcard_id")
        dpi = int(request.form.get("dpi", 200))
        output_format = request.form.get("format", "png").lower()
        logger.info(f"Processing flashcard {flashcard_id}: {pdf_file.filename}")
        if not pdf_file.filename.lower().endswith(".pdf"):
            return jsonify({
                "status": "error",
                "flashcard_id": flashcard_id,
                "error": "File must be PDF format",
                "error_code": "INVALID_FORMAT"
            }), 400
        temp_filename = f"{uuid.uuid4()}_{secure_filename(pdf_file.filename)}"
        temp_path = os.path.join(TEMP_DIR, temp_filename)
        pdf_file.save(temp_path)
        logger.info(f"Saved temporary PDF: {temp_path}")
        try:
            doc = fitz.open(temp_path)
            total_pages = len(doc)
            if total_pages == 0:
                return jsonify({
                    "status": "error",
                    "flashcard_id": flashcard_id,
                    "error": "PDF has no pages",
                    "error_code": "EMPTY_PDF"
                }), 400
            logger.info(f"PDF has {total_pages} pages")
            pages_data = []
            for page_num in range(total_pages):
                try:
                    page = doc[page_num]
                    zoom_factor = dpi / 72.0
                    mat = fitz.Matrix(zoom_factor, zoom_factor)
                    pix = page.get_pixmap(matrix=mat)
                    from PIL import Image
                    img_data = pix.tobytes("ppm")
                    img = Image.open(io.BytesIO(img_data))
                    img = img.convert("RGB")
                    watermarked_img = apply_watermark_to_image(img)
                    output_buffer = io.BytesIO()
                    watermarked_img.save(output_buffer, format=output_format.upper())
                    output_buffer.seek(0)
                    image_bytes = output_buffer.getvalue()
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    pages_data.append({
                        "page_num": page_num + 1,
                        "image_base64": image_base64,
                        "format": output_format,
                        "width": watermarked_img.width,
                        "height": watermarked_img.height,
                        "size_bytes": len(image_bytes)
                    })
                    logger.info(f"Processed page {page_num + 1}/{total_pages}")
                except Exception as e:
                    logger.error(f"Error processing page {page_num + 1}: {str(e)}")
                    return jsonify({
                        "status": "error",
                        "flashcard_id": flashcard_id,
                        "error": f"Failed to process page {page_num + 1}: {str(e)}",
                        "error_code": "PAGE_PROCESSING_ERROR"
                    }), 500
            doc.close()
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Successfully processed {len(pages_data)} pages in {processing_time_ms}ms")
            return jsonify({
                "status": "success",
                "flashcard_id": flashcard_id,
                "total_pages": total_pages,
                "pages": pages_data,
                "processing_time_ms": processing_time_ms
            }), 200
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.info(f"Cleaned up temporary file: {temp_path}")
                except Exception as e:
                    logger.error(f"Failed to delete temp file: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error in /api/process: {str(e)}")
        return jsonify({"status": "error", "error": str(e), "error_code": "PROCESSING_ERROR"}), 500

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "service": "BOBI PDF Processor", "version": "1.0.0"}), 200




if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)

"""
PDF Processing Module for Django
Handles PDF to image conversion with watermarking
Migrated from bobi/ Flask service into Django
"""

import io
import os
import logging
from pathlib import Path
from PIL import Image
import fitz  # PyMUPDF
import cairosvg
from django.conf import settings

logger = logging.getLogger(__name__)


def apply_watermark_to_image(
    img,
    opacity=None,
    angle=None,
    scale_fraction=None,
    spacing=None,
    svg_path=None,
):
    """
    Apply SVG watermark onto a PIL Image.
    Watermark is tiled across the image with configurable spacing and rotation.

    Args:
        img: PIL Image (RGB or RGBA)
        opacity: Watermark transparency (0.0-1.0). Uses WATERMARK_OPACITY if None
        angle: Rotation angle in degrees. Uses WATERMARK_ANGLE if None
        scale_fraction: Size as fraction of image. Uses WATERMARK_SCALE if None
        spacing: (x_step, y_step) for tiling. Uses WATERMARK_SPACING if None
        svg_path: Path to SVG file. Uses WATERMARK_SVG_PATH if None

    Returns:
        PIL Image (RGB) with watermark applied
    """
    # Use Django settings as defaults
    if opacity is None:
        opacity = getattr(settings, 'WATERMARK_OPACITY', 0.5)
    if angle is None:
        angle = getattr(settings, 'WATERMARK_ANGLE', 0)
    if scale_fraction is None:
        scale_fraction = getattr(settings, 'WATERMARK_SCALE', 0.25)
    if spacing is None:
        spacing = getattr(settings, 'WATERMARK_SPACING', (320, 380))
    if svg_path is None:
        svg_path = getattr(settings, 'WATERMARK_SVG_PATH', None)

    logger.info(f"[WATERMARK] Applying with opacity={opacity}, angle={angle}, scale={scale_fraction}, spacing={spacing}")

    # If no SVG path, return original image
    if not svg_path:
        logger.warning("[WATERMARK] No SVG path configured, skipping watermark")
        return img

    # Ensure SVG path exists
    if not os.path.exists(svg_path):
        logger.warning(f"[WATERMARK] SVG not found: {svg_path}, skipping watermark")
        return img

    try:
        # Render SVG to PNG
        logger.debug(f"[WATERMARK] Rendering SVG: {svg_path}")
        # Ensure path is string for cairosvg
        svg_path_str = str(svg_path)
        png_bytes = cairosvg.svg2png(url=svg_path_str)
        wm = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        logger.debug(f"[WATERMARK] SVG rendered, size=({wm.width}x{wm.height})")
    except Exception as e:
        logger.exception(f"[WATERMARK] Failed to render SVG: {e}")
        return img

    try:
        # Convert base image to RGBA for compositing
        base = img.convert("RGBA")
        logger.debug(f"[WATERMARK] Base image: ({base.width}x{base.height})")

        # Calculate watermark size
        min_dim = min(base.width, base.height)
        target_w = max(32, int(min_dim * float(scale_fraction)))
        scale = target_w / max(1, wm.width)
        wm_resized = wm.resize(
            (int(wm.width * scale), int(wm.height * scale)),
            Image.LANCZOS
        )
        logger.debug(f"[WATERMARK] Resized to ({wm_resized.width}x{wm_resized.height})")

        # Rotate watermark
        wm_rotated = wm_resized.rotate(angle, expand=True)
        logger.debug(f"[WATERMARK] Rotated by {angle}°, new size=({wm_rotated.width}x{wm_rotated.height})")

        # Apply opacity
        if opacity < 1.0:
            alpha = wm_rotated.split()[3].point(lambda p: int(p * opacity))
            wm_rotated.putalpha(alpha)
            logger.debug(f"[WATERMARK] Opacity applied: {opacity}")

        # Create overlay and tile watermark
        overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
        step_x, step_y = spacing

        tile_count = 0
        for y in range(0, base.height, step_y):
            for x in range(0, base.width, step_x):
                overlay.paste(wm_rotated, (x, y), wm_rotated)
                tile_count += 1
        logger.debug(f"[WATERMARK] Tiled {tile_count} times")

        # Additionally, paste one centered logo on top so it's clearly visible
        try:
            center_scale = min(0.5, max(0.15, getattr(settings, 'WATERMARK_CENTER_SCALE', 0.35)))
            min_dim = min(base.width, base.height)
            target_center_w = max(32, int(min_dim * float(center_scale)))
            scale_c = target_center_w / max(1, wm.width)
            wm_center = wm.resize(
                (int(wm.width * scale_c), int(wm.height * scale_c)),
                Image.LANCZOS
            ).rotate(angle, expand=True)
            if opacity < 1.0:
                alpha_c = wm_center.split()[3].point(lambda p: int(p * opacity))
                wm_center.putalpha(alpha_c)

            cx = (base.width - wm_center.width) // 2
            cy = (base.height - wm_center.height) // 2
            overlay.paste(wm_center, (cx, cy), wm_center)
            logger.debug(f"[WATERMARK] Pasted centered watermark at ({cx},{cy}) size=({wm_center.width}x{wm_center.height})")
        except Exception:
            logger.exception("[WATERMARK] Failed to paste centered watermark, continuing")

        # Composite and convert to RGB
        final_img = Image.alpha_composite(base, overlay).convert("RGB")
        logger.debug(f"[WATERMARK] Compositing complete")
        
        return final_img

    except Exception as e:
        logger.exception(f"[WATERMARK] Failed to apply watermark: {e}")
        return img


def process_pdf_to_images(pdf_path, dpi=None, image_format=None):
    """
    Convert PDF pages to images with watermark.
    Processes one page at a time to minimize memory usage.
    
    Args:
        pdf_path: Path to PDF file
        dpi: Dots per inch (resolution). Uses BOBI_DPI if None
        image_format: Output format ('png' or 'jpeg'). Uses BOBI_FORMAT if None
    
    Yields:
        Tuples of (PIL.Image, page_num) for each page
    
    Raises:
        FileNotFoundError: PDF doesn't exist
        ValueError: PDF invalid or empty
        Exception: Processing error
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Use Django settings as defaults
    dpi = dpi or getattr(settings, 'BOBI_DPI', 300)
    image_format = image_format or getattr(settings, 'BOBI_FORMAT', 'png')

    doc = None
    try:
        # Open the PDF
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            raise ValueError("PDF is empty")

        logger.info(f"[PDF] Processing {doc.page_count} pages from {os.path.basename(pdf_path)}")

        # Process each page one at a time
        for page_num in range(doc.page_count):
            try:
                # Load and process one page at a time
                page = doc.load_page(page_num)
                
                # Render page to an image
                pix = page.get_pixmap(dpi=dpi)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                logger.debug(f"[PDF] Rendered page {page_num + 1}: {img.size[0]}x{img.size[1]} pixels")
                
                # Apply watermark with original settings
                img = apply_watermark_to_image(img)
                
                # Yield the result immediately
                yield (img, page_num + 1)
                
                # Clean up explicitly
                del img
                del pix
                del page
                
                # Force garbage collection every 5 pages
                if (page_num + 1) % 5 == 0:
                    import gc
                    gc.collect()
                
            except Exception as e:
                logger.error(f"[PDF] Error processing page {page_num + 1}: {str(e)}")
                # Continue with next page even if one fails
                continue
                
    except Exception as e:
        logger.error(f"[PDF] PDF processing failed: {str(e)}")
        raise
        
    finally:
        if doc:
            doc.close()
            logger.debug("[PDF] Closed PDF document")


def save_image_from_pil(pil_image, output_format='png'):
    """
    Convert PIL Image to bytes (PNG or JPEG).
    
    Args:
        pil_image: PIL Image object
        output_format: 'png' or 'jpeg'
    
    Returns:
        Binary image data
    """
    output_buffer = io.BytesIO()
    format_upper = output_format.upper()
    pil_image.save(output_buffer, format=format_upper)
    output_buffer.seek(0)
    return output_buffer.getvalue()

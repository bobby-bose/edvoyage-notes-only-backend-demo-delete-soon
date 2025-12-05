import io
from PyPDF2 import PdfReader, PdfWriter, PageObject
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import cairosvg


def create_watermark_from_svg(svg_path, opacity=0.3, angle=30):
    png_bytes = cairosvg.svg2png(url=svg_path)
    img = ImageReader(io.BytesIO(png_bytes))

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)

    for x in range(-400, 1200, 200):
        for y in range(-400, 1200, 400):
            c.saveState()
            c.rotate(angle)
            c.setFillAlpha(opacity)
            c.drawImage(img, x, y, width=200, height=200, mask='auto')
            c.restoreState()

    c.save()
    packet.seek(0)
    return packet


def apply_watermark(pdf_path, svg_path, output_path):
    watermark_pdf = create_watermark_from_svg(svg_path)
    watermark_reader = PdfReader(watermark_pdf)
    watermark_page = watermark_reader.pages[0]

    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        new_page = PageObject.create_blank_page(None, page.mediabox.width, page.mediabox.height)
        new_page.merge_page(page)
        new_page.merge_page(watermark_page)
        writer.add_page(new_page)

    with open(output_path, "wb") as f:
        writer.write(f)


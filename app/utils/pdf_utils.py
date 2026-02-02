from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader, PdfWriter
import io
import tempfile

from app.models.plan import PlanSlug
from app.services.exceptions import FileStorageServiceException


def create_limited_preview_docx(full_doc_path: Path, plan_slug: PlanSlug) -> Path:
    if not full_doc_path.exists():
        raise FileStorageServiceException(f"Document not found: {full_doc_path}")
    
    doc = Document(str(full_doc_path))
    preview_doc = Document()
    
    sections_to_include = 3 if plan_slug == PlanSlug.BASIC else 4
    
    section_count = 0
    for paragraph in doc.paragraphs:
        if paragraph.style.name.startswith('Heading 1'):
            section_count += 1
            if section_count > sections_to_include:
                break
        
        new_para = preview_doc.add_paragraph(paragraph.text, style=paragraph.style.name)
        new_para.alignment = paragraph.alignment
        
        for run in paragraph.runs:
            if run.text:
                new_run = new_para.runs[-1] if new_para.runs else new_para.add_run(run.text)
                new_run.bold = run.bold
                new_run.italic = run.italic
                new_run.underline = run.underline
                if run.font.size:
                    new_run.font.size = run.font.size
    
    for table in doc.tables:
        if section_count > sections_to_include:
            break
        new_table = preview_doc.add_table(rows=len(table.rows), cols=len(table.columns))
        new_table.style = table.style
        
        for i, row in enumerate(table.rows):
            for j, cell in enumerate(row.cells):
                new_table.rows[i].cells[j].text = cell.text
    
    preview_doc.add_paragraph()
    watermark_para = preview_doc.add_paragraph()
    watermark_run = watermark_para.add_run("\n\n--- PREVIEW VERSION ---")
    watermark_run.font.size = Pt(16)
    watermark_run.font.bold = True
    watermark_run.font.color.rgb = RGBColor(200, 0, 0)
    watermark_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    preview_para = preview_doc.add_paragraph()
    preview_run = preview_para.add_run(
        "This is a limited preview. Purchase to access the complete manual with all sections, "
        "procedures, and templates."
    )
    preview_run.font.size = Pt(12)
    preview_run.italic = True
    preview_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    preview_path = full_doc_path.parent / f"preview_{full_doc_path.name}"
    preview_doc.save(str(preview_path))
    
    return preview_path


def docx_to_pdf_simple(docx_path: Path) -> Path:
    if not docx_path.exists():
        raise FileStorageServiceException(f"DOCX file not found: {docx_path}")
    
    doc = Document(str(docx_path))
    
    pdf_path = docx_path.with_suffix('.pdf')
    
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    
    y_position = height - 50
    page_number = 1
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 30, "PREVIEW - Limited Content")
    y_position -= 40
    
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            y_position -= 10
            continue
        
        if paragraph.style.name.startswith('Heading'):
            c.setFont("Helvetica-Bold", 14)
            font_size = 14
        else:
            c.setFont("Helvetica", 11)
            font_size = 11
        
        words = text.split()
        line = ""
        for word in words:
            test_line = f"{line} {word}".strip()
            if c.stringWidth(test_line, "Helvetica", font_size) < width - 100:
                line = test_line
            else:
                if line:
                    c.drawString(50, y_position, line)
                    y_position -= 15
                line = word
            
            if y_position < 50:
                c.showPage()
                page_number += 1
                c.setFont("Helvetica-Bold", 16)
                c.drawString(50, height - 30, f"PREVIEW - Limited Content (Page {page_number})")
                y_position = height - 60
                c.setFont("Helvetica", 11)
        
        if line:
            c.drawString(50, y_position, line)
            y_position -= 20
        
        if y_position < 50:
            c.showPage()
            page_number += 1
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 30, f"PREVIEW - Limited Content (Page {page_number})")
            y_position = height - 60
    
    c.save()
    
    return pdf_path


def add_watermark_to_pdf(pdf_path: Path, watermark_text: str = "PREVIEW") -> Path:
    if not pdf_path.exists():
        raise FileStorageServiceException(f"PDF file not found: {pdf_path}")
    
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    
    watermark_buffer = io.BytesIO()
    watermark_canvas = canvas.Canvas(watermark_buffer, pagesize=letter)
    width, height = letter
    
    watermark_canvas.saveState()
    watermark_canvas.setFont("Helvetica-Bold", 60)
    watermark_canvas.setFillColorRGB(0.9, 0.9, 0.9, alpha=0.3)
    watermark_canvas.translate(width / 2, height / 2)
    watermark_canvas.rotate(45)
    watermark_canvas.drawCentredString(0, 0, watermark_text)
    watermark_canvas.restoreState()
    watermark_canvas.save()
    
    watermark_buffer.seek(0)
    watermark_pdf = PdfReader(watermark_buffer)
    watermark_page = watermark_pdf.pages[0]
    
    for page in reader.pages:
        page.merge_page(watermark_page)
        writer.add_page(page)
    
    watermarked_path = pdf_path.parent / f"watermarked_{pdf_path.name}"
    with open(watermarked_path, 'wb') as output_file:
        writer.write(output_file)
    
    return watermarked_path


def create_secure_preview_pdf(full_doc_path: Path, plan_slug: PlanSlug) -> Path:
    limited_docx_path = create_limited_preview_docx(full_doc_path, plan_slug)
    
    pdf_path = docx_to_pdf_simple(limited_docx_path)
    
    watermarked_pdf_path = add_watermark_to_pdf(pdf_path, "PREVIEW - LIMITED CONTENT")
    
    limited_docx_path.unlink()
    pdf_path.unlink()
    
    return watermarked_pdf_path

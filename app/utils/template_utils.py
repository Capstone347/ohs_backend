from pathlib import Path
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image
import io

from app.models.company import Company
from app.models.plan import PlanSlug
from app.services.exceptions import (
    FileStorageServiceException,
    FileNotFoundServiceException,
)


TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "documents"
MAX_LOGO_WIDTH = 2.5
MAX_LOGO_HEIGHT = 1.5


class TemplateLoader:
    @staticmethod
    def load_template(plan_slug: PlanSlug) -> Path:
        if not plan_slug:
            raise ValueError("plan_slug is required to load template")
        
        template_map = {
            PlanSlug.BASIC: "basic_manual_template.docx",
            PlanSlug.COMPREHENSIVE: "comprehensive_manual_template.docx",
        }
        
        template_filename = template_map.get(plan_slug)
        if not template_filename:
            raise ValueError(f"Unknown plan type: {plan_slug}")
        
        template_path = TEMPLATES_DIR / template_filename
        if not template_path.exists():
            raise FileNotFoundServiceException(f"Template not found: {template_path}")
        
        return template_path


def replace_template_variables(doc: Document, replacements: dict[str, str]) -> Document:
    if not doc:
        raise ValueError("Document cannot be None")
    
    if not replacements:
        raise ValueError("Replacements dictionary cannot be empty")
    
    for paragraph in doc.paragraphs:
        for key, value in replacements.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in paragraph.text:
                inline = paragraph.runs
                for run in inline:
                    if placeholder in run.text:
                        run.text = run.text.replace(placeholder, value)
    
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for key, value in replacements.items():
                        placeholder = f"{{{{{key}}}}}"
                        if placeholder in paragraph.text:
                            inline = paragraph.runs
                            for run in inline:
                                if placeholder in run.text:
                                    run.text = run.text.replace(placeholder, value)
    
    return doc


def resize_logo_image(logo_path: Path) -> tuple[bytes, float, float]:
    if not logo_path:
        raise ValueError("logo_path is required")
    
    if not logo_path.exists():
        raise FileNotFoundServiceException(f"Logo file not found: {logo_path}")
    
    try:
        image = Image.open(logo_path)
    except Exception as e:
        raise FileStorageServiceException(f"Failed to open logo image: {str(e)}")
    
    original_width, original_height = image.size
    aspect_ratio = original_width / original_height
    
    if original_width > original_height:
        new_width = min(MAX_LOGO_WIDTH, original_width / 96)
        new_height = new_width / aspect_ratio
        if new_height > MAX_LOGO_HEIGHT:
            new_height = MAX_LOGO_HEIGHT
            new_width = new_height * aspect_ratio
    else:
        new_height = min(MAX_LOGO_HEIGHT, original_height / 96)
        new_width = new_height * aspect_ratio
        if new_width > MAX_LOGO_WIDTH:
            new_width = MAX_LOGO_WIDTH
            new_height = new_width / aspect_ratio
    
    img_byte_arr = io.BytesIO()
    if logo_path.suffix.lower() == '.png':
        image.save(img_byte_arr, format='PNG')
    else:
        image.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    
    return img_byte_arr.getvalue(), new_width, new_height


def insert_company_logo(doc: Document, logo_path: Path, placeholder: str = "{{logo}}") -> Document:
    if not doc:
        raise ValueError("Document cannot be None")
    
    if not logo_path:
        raise ValueError("logo_path is required")
    
    if not placeholder:
        raise ValueError("placeholder is required")
    
    logo_bytes, width_inches, height_inches = resize_logo_image(logo_path)
    
    logo_inserted = False
    
    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            paragraph.text = paragraph.text.replace(placeholder, "")
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run()
            run.add_picture(io.BytesIO(logo_bytes), width=Inches(width_inches))
            logo_inserted = True
    
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    if placeholder in paragraph.text:
                        paragraph.text = paragraph.text.replace(placeholder, "")
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        run = paragraph.add_run()
                        run.add_picture(io.BytesIO(logo_bytes), width=Inches(width_inches))
                        logo_inserted = True
    
    if not logo_inserted:
        raise ValueError(f"Logo placeholder '{placeholder}' not found in document")
    
    return doc


def build_company_replacements(company: Company, order_id: int) -> dict[str, str]:
    if not company:
        raise ValueError("Company cannot be None")
    
    if not order_id:
        raise ValueError("order_id is required")
    
    company_name = company.name if company.name else "N/A"
    
    return {
        "company_name": company_name,
        "order_id": str(order_id),
        "generation_date": datetime.now().strftime("%B %d, %Y"),
        "year": str(datetime.now().year),
    }

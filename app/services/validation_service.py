import re
from pathlib import Path
from PIL import Image
import io

from app.services.exceptions import (
    ValidationServiceException,
    InvalidNAICSCodeException,
    InvalidEmailException,
    InvalidProvinceException,
    InvalidFileException,
    FileSizeLimitExceededException,
    UnsupportedFileTypeException,
)

CANADIAN_PROVINCES = {
    "AB": "Alberta",
    "BC": "British Columbia",
    "MB": "Manitoba",
    "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador",
    "NS": "Nova Scotia",
    "NT": "Northwest Territories",
    "NU": "Nunavut",
    "ON": "Ontario",
    "PE": "Prince Edward Island",
    "QC": "Quebec",
    "SK": "Saskatchewan",
    "YT": "Yukon",
}

NAICS_CODE_LENGTH = 6

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


class ValidationService:
    def __init__(self, max_logo_size_mb: int = 5, allowed_extensions: list[str] | None = None):
        self.max_logo_size_mb = max_logo_size_mb
        self.max_logo_size_bytes = max_logo_size_mb * 1024 * 1024
        self.allowed_extensions = allowed_extensions or [".png", ".jpg", ".jpeg", ".svg"]

    def validate_naics_code(self, naics_code: str) -> bool:
        if not naics_code:
            raise InvalidNAICSCodeException("NAICS code cannot be empty")
        
        if not isinstance(naics_code, str):
            raise InvalidNAICSCodeException("NAICS code must be a string")
        
        naics_clean = naics_code.strip()
        
        if len(naics_clean) != NAICS_CODE_LENGTH:
            raise InvalidNAICSCodeException(
                f"NAICS code must be exactly {NAICS_CODE_LENGTH} digits, got {len(naics_clean)}"
            )
        
        if not naics_clean.isdigit():
            raise InvalidNAICSCodeException("NAICS code must contain only numeric digits")
        
        return True

    def validate_naics_codes(self, naics_codes: list[str]) -> bool:
        if not naics_codes:
            raise InvalidNAICSCodeException("At least one NAICS code is required")
        
        if not isinstance(naics_codes, list):
            raise InvalidNAICSCodeException("NAICS codes must be provided as a list")
        
        for code in naics_codes:
            self.validate_naics_code(code)
        
        return True

    def validate_email(self, email: str) -> bool:
        if not email:
            raise InvalidEmailException("Email cannot be empty")
        
        if not isinstance(email, str):
            raise InvalidEmailException("Email must be a string")
        
        email_clean = email.strip().lower()
        
        if len(email_clean) > 255:
            raise InvalidEmailException("Email cannot exceed 255 characters")
        
        if not EMAIL_REGEX.match(email_clean):
            raise InvalidEmailException(f"Invalid email format: {email}")
        
        return True

    def validate_province(self, province_code: str) -> bool:
        if not province_code:
            raise InvalidProvinceException("Province code cannot be empty")
        
        if not isinstance(province_code, str):
            raise InvalidProvinceException("Province code must be a string")
        
        province_upper = province_code.strip().upper()
        
        if province_upper not in CANADIAN_PROVINCES:
            raise InvalidProvinceException(
                f"Invalid province code: {province_code}. Must be one of: {', '.join(CANADIAN_PROVINCES.keys())}"
            )
        
        return True

    def get_province_name(self, province_code: str) -> str:
        if not self.validate_province(province_code):
            return ""
        
        return CANADIAN_PROVINCES[province_code.strip().upper()]

    def validate_file_size(self, file_content: bytes) -> bool:
        if not file_content:
            raise InvalidFileException("File content cannot be empty")
        
        file_size = len(file_content)
        
        if file_size > self.max_logo_size_bytes:
            size_mb = file_size / (1024 * 1024)
            raise FileSizeLimitExceededException(
                f"File size {size_mb:.2f}MB exceeds maximum allowed size of {self.max_logo_size_mb}MB"
            )
        
        return True

    def validate_file_extension(self, filename: str) -> bool:
        if not filename:
            raise InvalidFileException("Filename cannot be empty")
        
        file_path = Path(filename)
        extension = file_path.suffix.lower()
        
        if not extension:
            raise UnsupportedFileTypeException("File has no extension")
        
        if extension not in self.allowed_extensions:
            raise UnsupportedFileTypeException(
                f"File type {extension} not supported. Allowed types: {', '.join(self.allowed_extensions)}"
            )
        
        return True

    def validate_image_file(self, file_content: bytes, filename: str) -> bool:
        self.validate_file_size(file_content)
        self.validate_file_extension(filename)
        
        extension = Path(filename).suffix.lower()
        
        if extension == ".svg":
            if not file_content.startswith(b'<svg') and b'<svg' not in file_content[:1000]:
                raise InvalidFileException("Invalid SVG file format")
            return True
        
        if extension in [".png", ".jpg", ".jpeg"]:
            try:
                image = Image.open(io.BytesIO(file_content))
                image.verify()
                return True
            except Exception as e:
                raise InvalidFileException(f"Invalid image file: {str(e)}")
        
        return True

    def validate_company_name(self, company_name: str) -> bool:
        if not company_name:
            raise ValidationServiceException("Company name cannot be empty")
        
        if not isinstance(company_name, str):
            raise ValidationServiceException("Company name must be a string")
        
        company_clean = company_name.strip()
        
        if len(company_clean) < 2:
            raise ValidationServiceException("Company name must be at least 2 characters")
        
        if len(company_clean) > 255:
            raise ValidationServiceException("Company name cannot exceed 255 characters")
        
        return True

    def validate_jurisdiction(self, jurisdiction: str) -> bool:
        return self.validate_province(jurisdiction)

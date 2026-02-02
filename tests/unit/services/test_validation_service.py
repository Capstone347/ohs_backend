import pytest

from app.services.validation_service import ValidationService, CANADIAN_PROVINCES
from app.services.exceptions import (
    InvalidNAICSCodeException,
    InvalidEmailException,
    InvalidProvinceException,
    InvalidFileException,
    FileSizeLimitExceededException,
    UnsupportedFileTypeException,
    ValidationServiceException,
)


@pytest.fixture
def validation_service():
    return ValidationService(max_logo_size_mb=5, allowed_extensions=[".png", ".jpg", ".jpeg", ".svg"])


class TestValidationService:
    def test_validate_naics_code_valid(self, validation_service):
        assert validation_service.validate_naics_code("123456") is True
        assert validation_service.validate_naics_code("000000") is True
        assert validation_service.validate_naics_code("999999") is True

    def test_validate_naics_code_empty_fails(self, validation_service):
        with pytest.raises(InvalidNAICSCodeException, match="cannot be empty"):
            validation_service.validate_naics_code("")

    def test_validate_naics_code_none_fails(self, validation_service):
        with pytest.raises(InvalidNAICSCodeException, match="cannot be empty"):
            validation_service.validate_naics_code(None)

    def test_validate_naics_code_wrong_length_fails(self, validation_service):
        with pytest.raises(InvalidNAICSCodeException, match="exactly 6 digits"):
            validation_service.validate_naics_code("12345")
        
        with pytest.raises(InvalidNAICSCodeException, match="exactly 6 digits"):
            validation_service.validate_naics_code("1234567")

    def test_validate_naics_code_non_numeric_fails(self, validation_service):
        with pytest.raises(InvalidNAICSCodeException, match="only numeric digits"):
            validation_service.validate_naics_code("12345a")
        
        with pytest.raises(InvalidNAICSCodeException, match="only numeric digits"):
            validation_service.validate_naics_code("abc123")

    def test_validate_naics_code_with_spaces_fails(self, validation_service):
        with pytest.raises(InvalidNAICSCodeException):
            validation_service.validate_naics_code("123 456")

    def test_validate_naics_codes_valid_list(self, validation_service):
        codes = ["123456", "234567", "345678"]
        assert validation_service.validate_naics_codes(codes) is True

    def test_validate_naics_codes_empty_list_fails(self, validation_service):
        with pytest.raises(InvalidNAICSCodeException, match="At least one NAICS code"):
            validation_service.validate_naics_codes([])

    def test_validate_naics_codes_with_invalid_code_fails(self, validation_service):
        codes = ["123456", "invalid", "345678"]
        with pytest.raises(InvalidNAICSCodeException):
            validation_service.validate_naics_codes(codes)

    def test_validate_email_valid(self, validation_service):
        assert validation_service.validate_email("test@example.com") is True
        assert validation_service.validate_email("user.name+tag@example.co.uk") is True
        assert validation_service.validate_email("test123@test-domain.com") is True

    def test_validate_email_empty_fails(self, validation_service):
        with pytest.raises(InvalidEmailException, match="cannot be empty"):
            validation_service.validate_email("")

    def test_validate_email_none_fails(self, validation_service):
        with pytest.raises(InvalidEmailException, match="cannot be empty"):
            validation_service.validate_email(None)

    def test_validate_email_invalid_format_fails(self, validation_service):
        with pytest.raises(InvalidEmailException, match="Invalid email format"):
            validation_service.validate_email("invalid-email")
        
        with pytest.raises(InvalidEmailException, match="Invalid email format"):
            validation_service.validate_email("@example.com")
        
        with pytest.raises(InvalidEmailException, match="Invalid email format"):
            validation_service.validate_email("user@")

    def test_validate_email_too_long_fails(self, validation_service):
        long_email = "a" * 250 + "@example.com"
        with pytest.raises(InvalidEmailException, match="cannot exceed 255 characters"):
            validation_service.validate_email(long_email)

    def test_validate_province_valid(self, validation_service):
        assert validation_service.validate_province("ON") is True
        assert validation_service.validate_province("BC") is True
        assert validation_service.validate_province("QC") is True
        assert validation_service.validate_province("on") is True
        assert validation_service.validate_province("On") is True

    def test_validate_province_empty_fails(self, validation_service):
        with pytest.raises(InvalidProvinceException, match="cannot be empty"):
            validation_service.validate_province("")

    def test_validate_province_none_fails(self, validation_service):
        with pytest.raises(InvalidProvinceException, match="cannot be empty"):
            validation_service.validate_province(None)

    def test_validate_province_invalid_code_fails(self, validation_service):
        with pytest.raises(InvalidProvinceException, match="Invalid province code"):
            validation_service.validate_province("XX")
        
        with pytest.raises(InvalidProvinceException, match="Invalid province code"):
            validation_service.validate_province("ZZ")

    def test_get_province_name(self, validation_service):
        assert validation_service.get_province_name("ON") == "Ontario"
        assert validation_service.get_province_name("BC") == "British Columbia"
        assert validation_service.get_province_name("QC") == "Quebec"
        assert validation_service.get_province_name("on") == "Ontario"

    def test_validate_file_size_valid(self, validation_service):
        small_file = b"x" * 1024 * 1024
        assert validation_service.validate_file_size(small_file) is True

    def test_validate_file_size_empty_fails(self, validation_service):
        with pytest.raises(InvalidFileException, match="cannot be empty"):
            validation_service.validate_file_size(b"")

    def test_validate_file_size_exceeds_limit_fails(self, validation_service):
        large_file = b"x" * (6 * 1024 * 1024)
        with pytest.raises(FileSizeLimitExceededException, match="exceeds maximum"):
            validation_service.validate_file_size(large_file)

    def test_validate_file_extension_valid(self, validation_service):
        assert validation_service.validate_file_extension("logo.png") is True
        assert validation_service.validate_file_extension("image.jpg") is True
        assert validation_service.validate_file_extension("photo.JPEG") is True
        assert validation_service.validate_file_extension("vector.svg") is True

    def test_validate_file_extension_empty_fails(self, validation_service):
        with pytest.raises(InvalidFileException, match="cannot be empty"):
            validation_service.validate_file_extension("")

    def test_validate_file_extension_no_extension_fails(self, validation_service):
        with pytest.raises(UnsupportedFileTypeException, match="no extension"):
            validation_service.validate_file_extension("filename")

    def test_validate_file_extension_unsupported_fails(self, validation_service):
        with pytest.raises(UnsupportedFileTypeException, match="not supported"):
            validation_service.validate_file_extension("document.pdf")
        
        with pytest.raises(UnsupportedFileTypeException, match="not supported"):
            validation_service.validate_file_extension("script.exe")

    def test_validate_company_name_valid(self, validation_service):
        assert validation_service.validate_company_name("Test Company") is True
        assert validation_service.validate_company_name("ABC Corp.") is True
        assert validation_service.validate_company_name("Company123") is True

    def test_validate_company_name_empty_fails(self, validation_service):
        with pytest.raises(ValidationServiceException, match="cannot be empty"):
            validation_service.validate_company_name("")

    def test_validate_company_name_too_short_fails(self, validation_service):
        with pytest.raises(ValidationServiceException, match="at least 2 characters"):
            validation_service.validate_company_name("A")

    def test_validate_company_name_too_long_fails(self, validation_service):
        long_name = "A" * 256
        with pytest.raises(ValidationServiceException, match="cannot exceed 255"):
            validation_service.validate_company_name(long_name)

    def test_validate_jurisdiction(self, validation_service):
        assert validation_service.validate_jurisdiction("ON") is True
        assert validation_service.validate_jurisdiction("BC") is True

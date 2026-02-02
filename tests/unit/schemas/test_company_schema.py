import pytest
from pydantic import ValidationError
from app.schemas.company import CompanyCreate

valid_company = {
    "company_name": "Acme Safety Inc.",
    "province": "Ontario",
    "naics_codes": ["123456", "654321"],
}


def test_company_valid():
    obj = CompanyCreate(**valid_company)
    assert obj.company_name == "Acme Safety Inc."
    assert obj.naics_codes == ["123456", "654321"]


@pytest.mark.parametrize("bad", [
    {"company_name": "", "province": "Ontario", "naics_codes": ["123456"]},
    {"company_name": "X", "province": "ON", "naics_codes": []},
    {"company_name": "A", "province": "Ontario", "naics_codes": ["12345"]},
    {"company_name": "A", "province": "Ontario", "naics_codes": ["12a456"]},
])
def test_company_invalid(bad):
    with pytest.raises(ValidationError):
        CompanyCreate(**bad)

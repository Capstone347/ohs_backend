import logging

import pytest

from app.schemas.jurisdiction import JurisdictionPromptPack
from app.services.exceptions import InvalidProvinceException, JurisdictionPackLoadError
from app.services.jurisdiction_service import JurisdictionService

_VALID_ON_PACK = """\
province_code: "ON"
province_name: "Ontario"
legislation_name: "Occupational Health and Safety Act (OHSA), R.S.O. 1990, c. O.1"
regulatory_body: "Ontario Ministry of Labour, Immigration, Training and Skills Development"
key_regulations:
  - "O. Reg. 213/91 — Construction Projects"
  - "O. Reg. 851 — Industrial Establishments"
terminology_notes: "Workers have the right to refuse unsafe work under Section 43 of the OHSA."
prompt_preamble: "The following Safe Job Procedure is intended to reflect Ontario OHSA requirements."
"""

_VALID_GENERIC_PACK = """\
province_code: "CA"
province_name: "Canada (Generic)"
legislation_name: "Canada Labour Code, R.S.C. 1985, c. L-2"
regulatory_body: "Employment and Social Development Canada (ESDC)"
key_regulations:
  - "Canada Occupational Health and Safety Regulations, SOR/86-304"
terminology_notes: "Generic Canadian OHS preamble for unsupported provinces."
prompt_preamble: "The following Safe Job Procedure is aligned with general Canadian OHS best practices."
"""


@pytest.fixture
def packs_dir(tmp_path):
    (tmp_path / "on.yaml").write_text(_VALID_ON_PACK, encoding="utf-8")
    (tmp_path / "generic.yaml").write_text(_VALID_GENERIC_PACK, encoding="utf-8")
    return tmp_path


@pytest.fixture
def service(packs_dir):
    return JurisdictionService(packs_dir=packs_dir)


class TestJurisdictionServiceHappyPath:
    def test_get_pack_returns_jurisdiction_prompt_pack_instance(self, service):
        pack = service.get_pack("ON")
        assert isinstance(pack, JurisdictionPromptPack)

    def test_get_pack_province_code_matches_yaml(self, service):
        pack = service.get_pack("ON")
        assert pack.province_code == "ON"

    def test_get_pack_province_name_matches_yaml(self, service):
        pack = service.get_pack("ON")
        assert pack.province_name == "Ontario"

    def test_get_pack_legislation_name_matches_yaml(self, service):
        pack = service.get_pack("ON")
        assert "OHSA" in pack.legislation_name

    def test_get_pack_regulatory_body_matches_yaml(self, service):
        pack = service.get_pack("ON")
        assert "Ontario Ministry" in pack.regulatory_body

    def test_get_pack_key_regulations_is_populated_list(self, service):
        pack = service.get_pack("ON")
        assert isinstance(pack.key_regulations, list)
        assert len(pack.key_regulations) == 2

    def test_get_pack_terminology_notes_is_populated(self, service):
        pack = service.get_pack("ON")
        assert len(pack.terminology_notes) > 0

    def test_get_pack_prompt_preamble_is_populated(self, service):
        pack = service.get_pack("ON")
        assert len(pack.prompt_preamble) > 0

    def test_get_pack_is_generic_false_for_known_province_with_pack(self, service):
        pack = service.get_pack("ON")
        assert pack.is_generic is False


class TestJurisdictionServiceCaseInsensitivity:
    def test_lowercase_province_code_resolves(self, service):
        pack = service.get_pack("on")
        assert pack.province_code == "ON"

    def test_mixed_case_province_code_resolves(self, service):
        pack = service.get_pack("On")
        assert pack.province_code == "ON"

    def test_uppercase_province_code_resolves(self, service):
        pack = service.get_pack("ON")
        assert pack.province_code == "ON"

    def test_province_code_with_surrounding_whitespace_resolves(self, service):
        pack = service.get_pack("  ON  ")
        assert pack.province_code == "ON"


class TestJurisdictionServiceFallback:
    def test_valid_province_without_dedicated_pack_returns_generic(self, service):
        pack = service.get_pack("MB")
        assert isinstance(pack, JurisdictionPromptPack)

    def test_fallback_pack_is_generic_true(self, service):
        pack = service.get_pack("MB")
        assert pack.is_generic is True

    def test_fallback_pack_has_generic_province_code(self, service):
        pack = service.get_pack("SK")
        assert pack.province_code == "CA"

    def test_fallback_pack_prompt_preamble_is_populated(self, service):
        pack = service.get_pack("NT")
        assert len(pack.prompt_preamble) > 0

    def test_fallback_applies_for_all_provinces_without_packs(self, packs_dir):
        service = JurisdictionService(packs_dir=packs_dir)
        provinces_without_packs = ["MB", "NB", "NL", "NS", "NT", "NU", "PE", "SK", "YT"]
        for province in provinces_without_packs:
            pack = service.get_pack(province)
            assert pack.is_generic is True, f"Expected is_generic=True for {province}"

    def test_fallback_emits_warning_log(self, service, caplog):
        with caplog.at_level(logging.WARNING, logger="app.services.jurisdiction_service"):
            service.get_pack("MB")
        assert "MB" in caplog.text
        assert any(r.levelname == "WARNING" for r in caplog.records)

    def test_no_warning_emitted_for_province_with_dedicated_pack(self, service, caplog):
        with caplog.at_level(logging.WARNING, logger="app.services.jurisdiction_service"):
            service.get_pack("ON")
        assert not any(r.levelname == "WARNING" for r in caplog.records)


class TestJurisdictionServiceRealPackFiles:
    def test_all_four_required_province_packs_load_successfully(self):
        service = JurisdictionService()
        for province_code in ["ON", "BC", "AB", "QC"]:
            pack = service.get_pack(province_code)
            assert isinstance(pack, JurisdictionPromptPack), f"Failed to load pack for {province_code}"
            assert pack.is_generic is False, f"Expected real pack for {province_code}"

    def test_real_on_pack_has_correct_legislation(self):
        service = JurisdictionService()
        pack = service.get_pack("ON")
        assert "OHSA" in pack.legislation_name
        assert "Ontario" in pack.regulatory_body

    def test_real_bc_pack_has_correct_legislation(self):
        service = JurisdictionService()
        pack = service.get_pack("BC")
        assert "Workers Compensation Act" in pack.legislation_name
        assert "WorkSafeBC" in pack.regulatory_body

    def test_real_ab_pack_has_correct_legislation(self):
        service = JurisdictionService()
        pack = service.get_pack("AB")
        assert "Occupational Health and Safety Act" in pack.legislation_name
        assert "Alberta" in pack.regulatory_body

    def test_real_qc_pack_has_correct_legislation(self):
        service = JurisdictionService()
        pack = service.get_pack("QC")
        assert "LSST" in pack.legislation_name or "Occupational Health and Safety" in pack.legislation_name
        assert "CNESST" in pack.regulatory_body

    def test_all_real_packs_have_non_empty_prompt_preamble(self):
        service = JurisdictionService()
        for province_code in ["ON", "BC", "AB", "QC"]:
            pack = service.get_pack(province_code)
            assert len(pack.prompt_preamble.strip()) > 0, f"Empty preamble for {province_code}"

    def test_all_real_packs_have_at_least_one_key_regulation(self):
        service = JurisdictionService()
        for province_code in ["ON", "BC", "AB", "QC"]:
            pack = service.get_pack(province_code)
            assert len(pack.key_regulations) >= 1, f"No key regulations for {province_code}"

    def test_all_real_packs_preamble_does_not_claim_legal_compliance(self):
        service = JurisdictionService()
        forbidden_phrases = ["ensures compliance", "guarantees compliance", "legally compliant"]
        for province_code in ["ON", "BC", "AB", "QC"]:
            pack = service.get_pack(province_code)
            for phrase in forbidden_phrases:
                assert phrase.lower() not in pack.prompt_preamble.lower(), (
                    f"Forbidden phrase '{phrase}' found in {province_code} preamble"
                )

    def test_all_real_packs_preamble_contains_intended_to_reflect_language(self):
        service = JurisdictionService()
        for province_code in ["ON", "BC", "AB", "QC"]:
            pack = service.get_pack(province_code)
            preamble_lower = pack.prompt_preamble.lower()
            has_safe_language = (
                "intended to reflect" in preamble_lower
                or "aligned with" in preamble_lower
                or "intended to support" in preamble_lower
            )
            assert has_safe_language, (
                f"Pack for {province_code} preamble is missing 'intended to reflect' / 'aligned with' language"
            )

    def test_all_real_packs_preamble_contains_no_legal_advice_disclaimer(self):
        service = JurisdictionService()
        for province_code in ["ON", "BC", "AB", "QC"]:
            pack = service.get_pack(province_code)
            assert "does not constitute legal advice" in pack.prompt_preamble.lower(), (
                f"Pack for {province_code} is missing 'does not constitute legal advice' disclaimer"
            )


class TestJurisdictionServiceErrors:
    def test_empty_province_code_raises_value_error(self, service):
        with pytest.raises(ValueError, match="province_code is required"):
            service.get_pack("")

    def test_none_province_code_raises_value_error(self, service):
        with pytest.raises(ValueError, match="province_code is required"):
            service.get_pack(None)

    def test_unrecognized_province_code_raises_invalid_province_exception(self, service):
        with pytest.raises(InvalidProvinceException):
            service.get_pack("XX")

    def test_unrecognized_province_code_error_includes_bad_code(self, service):
        with pytest.raises(InvalidProvinceException, match="ZZ"):
            service.get_pack("ZZ")

    def test_malformed_yaml_raises_jurisdiction_pack_load_error(self, packs_dir):
        (packs_dir / "on.yaml").write_text("key: [unclosed bracket", encoding="utf-8")
        broken_service = JurisdictionService(packs_dir=packs_dir)
        with pytest.raises(JurisdictionPackLoadError, match="Failed to parse"):
            broken_service.get_pack("ON")

    def test_non_mapping_yaml_raises_jurisdiction_pack_load_error(self, packs_dir):
        (packs_dir / "on.yaml").write_text("- just\n- a\n- list\n", encoding="utf-8")
        broken_service = JurisdictionService(packs_dir=packs_dir)
        with pytest.raises(JurisdictionPackLoadError, match="must be a YAML mapping"):
            broken_service.get_pack("ON")

    def test_schema_validation_failure_raises_jurisdiction_pack_load_error(self, packs_dir):
        (packs_dir / "on.yaml").write_text(
            "province_code: 'ON'\nprovince_name: 'Ontario'\n", encoding="utf-8"
        )
        broken_service = JurisdictionService(packs_dir=packs_dir)
        with pytest.raises(JurisdictionPackLoadError, match="failed schema validation"):
            broken_service.get_pack("ON")

    def test_missing_generic_fallback_raises_jurisdiction_pack_load_error(self, tmp_path):
        (tmp_path / "on.yaml").write_text(_VALID_ON_PACK, encoding="utf-8")
        service_no_generic = JurisdictionService(packs_dir=tmp_path)
        with pytest.raises(JurisdictionPackLoadError, match="generic fallback pack is missing"):
            service_no_generic.get_pack("MB")

    def test_none_packs_dir_raises_value_error(self):
        with pytest.raises(ValueError, match="packs_dir is required"):
            JurisdictionService(packs_dir=None)


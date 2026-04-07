import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.schemas.jurisdiction import JurisdictionPromptPack
from app.services.exceptions import JurisdictionPackLoadError
from app.services.validation_service import CANADIAN_PROVINCES

logger = logging.getLogger(__name__)

_GENERIC_PACK_FILENAME = "generic.yaml"
_DEFAULT_PACKS_DIR = Path(__file__).parent.parent / "config" / "jurisdiction_packs"


class JurisdictionService:
    def __init__(self, packs_dir: Path | None = _DEFAULT_PACKS_DIR):
        if not packs_dir:
            raise ValueError("packs_dir is required")

        self.packs_dir = packs_dir

    def get_pack(self, province_code: str | None) -> JurisdictionPromptPack:
        if not province_code:
            raise ValueError("province_code is required")

        normalized_code = province_code.strip().upper()

        if normalized_code not in CANADIAN_PROVINCES:
            from app.services.exceptions import InvalidProvinceException
            raise InvalidProvinceException(
                f"'{province_code}' is not a recognized Canadian province or territory code"
            )

        province_pack_path = self.packs_dir / f"{normalized_code.lower()}.yaml"

        if province_pack_path.exists():
            return self._load_pack_file(province_pack_path, is_generic=False)

        logger.warning(
            "No jurisdiction pack found for province '%s', falling back to generic pack",
            normalized_code,
        )

        generic_pack_path = self.packs_dir / _GENERIC_PACK_FILENAME

        if not generic_pack_path.exists():
            raise JurisdictionPackLoadError(
                f"No pack found for province '{normalized_code}' and generic fallback pack is missing at {generic_pack_path}"
            )

        return self._load_pack_file(generic_pack_path, is_generic=True)

    def _load_pack_file(self, path: Path, is_generic: bool) -> JurisdictionPromptPack:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise JurisdictionPackLoadError(
                f"Failed to parse jurisdiction pack at {path}: {exc}"
            ) from exc
        except OSError as exc:
            raise JurisdictionPackLoadError(
                f"Failed to read jurisdiction pack at {path}: {exc}"
            ) from exc

        if not isinstance(raw, dict):
            raise JurisdictionPackLoadError(
                f"Jurisdiction pack at {path} must be a YAML mapping, got {type(raw).__name__}"
            )

        try:
            return JurisdictionPromptPack(**raw, is_generic=is_generic)
        except ValidationError as exc:
            raise JurisdictionPackLoadError(
                f"Jurisdiction pack at {path} failed schema validation: {exc}"
            ) from exc


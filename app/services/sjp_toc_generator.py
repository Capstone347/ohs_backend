import logging
import re

from pydantic import BaseModel, Field

from app.services.jurisdiction_service import JurisdictionService
from app.services.llm_provider import BaseLlmProvider, LlmResponse

logger = logging.getLogger(__name__)


class TocGenerationResult(BaseModel):
    titles: list[str] = Field(..., min_length=1)
    llm_response: LlmResponse


SYSTEM_PROMPT_TEMPLATE = (
    "You are an occupational health and safety expert specializing in Canadian workplace safety.\n\n"
    "{prompt_preamble}\n\n"
    "Province: {province_name}\n"
    "Regulatory Body: {regulatory_body}\n"
    "Primary Legislation: {legislation_name}\n"
    "Key Regulations:\n{key_regulations}\n\n"
    "Terminology Notes:\n{terminology_notes}\n\n"
    "Your task is to generate a Table of Contents listing all applicable Safe Job Procedures "
    "for the given industry codes. Each title must be specific and actionable — not generic. "
    "Return ONLY a numbered list of SJP titles, one per line, in the format:\n"
    "1. Title Here\n"
    "2. Title Here\n"
    "Do not include any other text, explanations, or commentary."
)

USER_PROMPT_TEMPLATE = (
    "Generate a Table of Contents listing all applicable Safe Job Procedures for the following "
    "industry NAICS code(s): {naics_codes}.\n\n"
    "{business_description_block}"
    "Generate between 10 and 25 specific Safe Job Procedure titles that are relevant to the "
    "hazards and work activities associated with these industry codes in {province_name}. "
    "Each title should describe a specific workplace task or activity that requires a safety procedure."
)


class SjpTocGenerator:
    def __init__(
        self,
        llm_provider: BaseLlmProvider,
        jurisdiction_service: JurisdictionService,
    ):
        self.llm_provider = llm_provider
        self.jurisdiction_service = jurisdiction_service

    async def generate_toc(
        self,
        province: str,
        naics_codes: list[str],
        business_description: str | None = None,
    ) -> TocGenerationResult:
        if not province:
            raise ValueError("province is required")
        if not naics_codes:
            raise ValueError("naics_codes is required")

        pack = self.jurisdiction_service.get_pack(province)

        key_regulations_text = "\n".join(f"- {reg}" for reg in pack.key_regulations)

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            prompt_preamble=pack.prompt_preamble,
            province_name=pack.province_name,
            regulatory_body=pack.regulatory_body,
            legislation_name=pack.legislation_name,
            key_regulations=key_regulations_text,
            terminology_notes=pack.terminology_notes,
        )

        business_description_block = ""
        if business_description:
            business_description_block = (
                f"Business Description: {business_description}\n\n"
            )

        user_prompt = USER_PROMPT_TEMPLATE.format(
            naics_codes=", ".join(naics_codes),
            business_description_block=business_description_block,
            province_name=pack.province_name,
        )

        llm_response = await self.llm_provider.complete(system_prompt, user_prompt)

        titles = self._parse_titles(llm_response.content)
        titles = self._deduplicate_titles(titles)

        if not titles:
            raise ValueError("LLM returned no parseable SJP titles")

        return TocGenerationResult(titles=titles, llm_response=llm_response)

    def _parse_titles(self, content: str) -> list[str]:
        pattern = re.compile(r"^\s*\d+[\.\)]\s*(.+)$", re.MULTILINE)
        matches = pattern.findall(content)
        return [title.strip() for title in matches if title.strip()]

    def _deduplicate_titles(self, titles: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for title in titles:
            normalized = title.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(title)
        return unique

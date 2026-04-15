import json
import logging

from pydantic import BaseModel, ValidationError

from app.schemas.sjp import SjpContentSections
from app.services.exceptions import LlmProviderException
from app.services.jurisdiction_service import JurisdictionService
from app.services.llm_provider import BaseLlmProvider, LlmResponse

logger = logging.getLogger(__name__)


class ContentGenerationResult(BaseModel):
    sections: SjpContentSections
    llm_response: LlmResponse


SYSTEM_PROMPT_TEMPLATE = (
    "You are an occupational health and safety expert specializing in Canadian workplace safety.\n\n"
    "{prompt_preamble}\n\n"
    "Province: {province_name}\n"
    "Regulatory Body: {regulatory_body}\n"
    "Primary Legislation: {legislation_name}\n"
    "Key Regulations:\n{key_regulations}\n\n"
    "Terminology Notes:\n{terminology_notes}\n\n"
    "You must generate a detailed Safe Job Procedure (SJP) for the given task title. "
    "Return your response as a JSON object with exactly these keys:\n"
    '{{\n'
    '  "task_description": "A detailed description of the task and its context",\n'
    '  "required_ppe": ["item1", "item2", ...],\n'
    '  "step_by_step_instructions": ["Step 1 description", "Step 2 description", ...],\n'
    '  "identified_hazards": ["hazard1", "hazard2", ...],\n'
    '  "control_measures": ["measure1", "measure2", ...],\n'
    '  "training_requirements": ["requirement1", "requirement2", ...],\n'
    '  "emergency_procedures": "Detailed emergency response procedures",\n'
    '  "legislative_references": "Specific legislative references from {province_name} OHS legislation"\n'
    '}}\n\n'
    "IMPORTANT:\n"
    "- Be specific to the industry and task, not generic.\n"
    "- Use language that is 'intended to reflect' or 'aligned with' provincial legislation. "
    "Never say 'compliant with' or 'meets requirements'.\n"
    "- Reference specific sections and regulations from {province_name} legislation where applicable.\n"
    "- All list fields must contain at least 2 items.\n"
    "- Return ONLY valid JSON, no other text."
)

USER_PROMPT_TEMPLATE = (
    "Generate a complete Safe Job Procedure for the following task:\n\n"
    "Title: {title}\n"
    "Industry NAICS Code(s): {naics_codes}\n"
    "{business_description_block}"
    "Province: {province_name}\n\n"
    "Provide detailed, industry-specific content for all 7 sections. "
    "The procedure should be practical and actionable for workers in this industry."
)


class SjpContentGenerator:
    def __init__(
        self,
        llm_provider: BaseLlmProvider,
        jurisdiction_service: JurisdictionService,
    ):
        self.llm_provider = llm_provider
        self.jurisdiction_service = jurisdiction_service

    async def generate_content(
        self,
        title: str,
        province: str,
        naics_codes: list[str],
        business_description: str | None = None,
    ) -> ContentGenerationResult:
        if not title:
            raise ValueError("title is required")
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
            business_description_block = f"Business Description: {business_description}\n"

        user_prompt = USER_PROMPT_TEMPLATE.format(
            title=title,
            naics_codes=", ".join(naics_codes),
            business_description_block=business_description_block,
            province_name=pack.province_name,
        )

        llm_response = await self.llm_provider.complete(
            system_prompt,
            user_prompt,
            response_format={"type": "json_object"},
        )

        try:
            sections = self._parse_response(llm_response.content)
        except (ValidationError, ValueError) as first_error:
            logger.warning(
                "First parse attempt failed for SJP '%s': %s. Retrying with correction prompt.",
                title,
                str(first_error),
            )
            sections = await self._retry_with_correction(
                system_prompt, user_prompt, llm_response.content, str(first_error)
            )

        return ContentGenerationResult(sections=sections, llm_response=llm_response)

    def _parse_response(self, content: str) -> SjpContentSections:
        parsed = json.loads(content)
        return SjpContentSections.model_validate(parsed)

    async def _retry_with_correction(
        self,
        system_prompt: str,
        original_user_prompt: str,
        bad_response: str,
        error_message: str,
    ) -> SjpContentSections:
        correction_prompt = (
            f"{original_user_prompt}\n\n"
            f"Your previous response was invalid. Error: {error_message}\n"
            f"Previous response: {bad_response[:500]}\n\n"
            "Please fix the response and return valid JSON matching the exact schema specified."
        )

        retry_response = await self.llm_provider.complete(
            system_prompt,
            correction_prompt,
            response_format={"type": "json_object"},
        )

        try:
            return self._parse_response(retry_response.content)
        except (ValidationError, ValueError) as e:
            raise LlmProviderException(
                f"Failed to parse SJP content after retry: {str(e)}"
            ) from e

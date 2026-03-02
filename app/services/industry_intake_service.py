from app.repositories.base_repository import RecordNotFoundError
from app.repositories.industry_intake_response_repository import IndustryIntakeResponseRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.industry_intake import (
    HeadcountBand,
    IntakeQuestion,
    IntakeQuestionsResponse,
    IndustryIntakeAnswersResponse,
    QuestionOption,
    QuestionTier,
    QuestionType,
    WorksiteType,
)
from app.services.exceptions import OrderServiceException

_CONSTRUCTION_NAICS_PREFIXES = ("23",)
_MANUFACTURING_NAICS_PREFIXES = ("31", "32", "33")
_HEALTHCARE_NAICS_PREFIXES = ("62",)
_TRANSPORT_NAICS_PREFIXES = ("48", "49")

_BASE_HIGH_RISK_OPTIONS = [
    QuestionOption(value="working_at_heights", label="Working at heights"),
    QuestionOption(value="heavy_equipment", label="Heavy equipment or machinery"),
    QuestionOption(value="electrical_work", label="Electrical work"),
    QuestionOption(value="confined_spaces", label="Confined spaces"),
    QuestionOption(value="none", label="None of the above"),
]

_CHEMICALS_OPTION = QuestionOption(
    value="chemicals_or_hazardous_materials",
    label="Chemicals or hazardous materials",
)

_BIOLOGICAL_OPTION = QuestionOption(
    value="biological_hazards",
    label="Biological hazards or patient handling",
)


def _naics_matches(code: str, prefixes: tuple[str, ...]) -> bool:
    return any(code.startswith(p) for p in prefixes)


def _build_high_risk_options(naics_codes: list[str]) -> list[QuestionOption]:
    options = list(_BASE_HIGH_RISK_OPTIONS)
    extra: list[QuestionOption] = []

    is_manufacturing = any(
        _naics_matches(c, _MANUFACTURING_NAICS_PREFIXES) for c in naics_codes
    )
    is_healthcare = any(
        _naics_matches(c, _HEALTHCARE_NAICS_PREFIXES) for c in naics_codes
    )

    if is_manufacturing:
        extra.append(_CHEMICALS_OPTION)

    if is_healthcare:
        extra.append(_BIOLOGICAL_OPTION)

    none_option = options.pop()
    return options + extra + [none_option]


def _build_core_questions(naics_codes: list[str]) -> list[IntakeQuestion]:
    return [
        IntakeQuestion(
            id="worksite_type",
            tier=QuestionTier.CORE,
            question_type=QuestionType.SINGLE_CHOICE,
            text="What best describes your primary worksite?",
            options=[
                QuestionOption(value=WorksiteType.OFFICE, label="Office"),
                QuestionOption(value=WorksiteType.FIELD, label="Field / outdoor site"),
                QuestionOption(value=WorksiteType.MIXED, label="Mixed (office and field)"),
            ],
        ),
        IntakeQuestion(
            id="headcount_band",
            tier=QuestionTier.CORE,
            question_type=QuestionType.SINGLE_CHOICE,
            text="How many workers does your company employ?",
            options=[
                QuestionOption(value=HeadcountBand.MICRO, label="1–4 workers"),
                QuestionOption(value=HeadcountBand.SMALL, label="5–19 workers"),
                QuestionOption(value=HeadcountBand.MEDIUM, label="20–99 workers"),
                QuestionOption(value=HeadcountBand.LARGE, label="100+ workers"),
            ],
        ),
        IntakeQuestion(
            id="high_risk_flags",
            tier=QuestionTier.CORE,
            question_type=QuestionType.MULTI_CHOICE,
            text="Select all high-risk activities that apply to your operations.",
            options=_build_high_risk_options(naics_codes),
        ),
        IntakeQuestion(
            id="has_subcontractors",
            tier=QuestionTier.CORE,
            question_type=QuestionType.BOOLEAN,
            text="Do you engage subcontractors or contract workers on site?",
            triggers_conditional=["subcontractor_management"],
        ),
        IntakeQuestion(
            id="emergency_readiness",
            tier=QuestionTier.CORE,
            question_type=QuestionType.SINGLE_CHOICE,
            text="Who is responsible for emergency response on your worksite?",
            options=[
                QuestionOption(value="designated_worker", label="A designated worker"),
                QuestionOption(value="supervisor", label="Site supervisor"),
                QuestionOption(value="external_provider", label="External emergency provider"),
                QuestionOption(value="not_defined", label="Not yet defined"),
            ],
        ),
    ]


_CONDITIONAL_QUESTIONS: list[IntakeQuestion] = [
    IntakeQuestion(
        id="subcontractor_management",
        tier=QuestionTier.CONDITIONAL,
        question_type=QuestionType.SINGLE_CHOICE,
        text="How are subcontractor safety requirements communicated?",
        options=[
            QuestionOption(value="written_contracts", label="Written contracts / agreements"),
            QuestionOption(value="site_orientation", label="Site-specific orientation"),
            QuestionOption(value="informal", label="Informally / verbally"),
            QuestionOption(value="not_defined", label="Not yet defined"),
        ],
    ),
    IntakeQuestion(
        id="chemical_inventory",
        tier=QuestionTier.CONDITIONAL,
        question_type=QuestionType.BOOLEAN,
        text="Do you maintain a current inventory of hazardous materials (SDS on file)?",
    ),
    IntakeQuestion(
        id="ppe_program",
        tier=QuestionTier.CONDITIONAL,
        question_type=QuestionType.BOOLEAN,
        text="Does your workplace have a formal PPE selection and training program?",
    ),
]

_TRIGGER_MAP: dict[str, list[str]] = {
    "has_subcontractors": ["subcontractor_management"],
    "chemicals_or_hazardous_materials": ["chemical_inventory"],
}


def _resolve_unlocked_conditionals(answers: dict) -> list[str]:
    unlocked: list[str] = []

    subcontractors_answer = answers.get("has_subcontractors")
    if subcontractors_answer is True or subcontractors_answer == "true":
        unlocked.extend(_TRIGGER_MAP["has_subcontractors"])

    high_risk = answers.get("high_risk_flags", [])
    if isinstance(high_risk, list) and "chemicals_or_hazardous_materials" in high_risk:
        unlocked.extend(_TRIGGER_MAP["chemicals_or_hazardous_materials"])

    return unlocked


class IndustryIntakeService:
    def __init__(
        self,
        order_repo: OrderRepository,
        intake_repo: IndustryIntakeResponseRepository,
    ):
        self.order_repo = order_repo
        self.intake_repo = intake_repo

    def get_intake_questions(self, naics_codes: list[str]) -> IntakeQuestionsResponse:
        if not naics_codes:
            raise OrderServiceException("naics_codes is required")

        return IntakeQuestionsResponse(
            naics_codes=naics_codes,
            core_questions=_build_core_questions(naics_codes),
            conditional_questions=_CONDITIONAL_QUESTIONS,
        )

    def save_intake_answers(
        self,
        order_id: int,
        answers: dict,
    ) -> IndustryIntakeAnswersResponse:
        if not order_id:
            raise OrderServiceException("order_id is required")

        if not answers:
            raise OrderServiceException("answers cannot be empty")

        self.order_repo.get_by_id_or_fail(order_id)

        record = self.intake_repo.upsert(order_id, answers)

        return IndustryIntakeAnswersResponse(
            order_id=record.order_id,
            answers=record.answers,
            conditional_questions_unlocked=_resolve_unlocked_conditionals(answers),
        )

    def get_intake_answers(self, order_id: int) -> IndustryIntakeAnswersResponse:
        if not order_id:
            raise OrderServiceException("order_id is required")

        self.order_repo.get_by_id_or_fail(order_id)

        record = self.intake_repo.get_by_order_id_or_fail(order_id)

        return IndustryIntakeAnswersResponse(
            order_id=record.order_id,
            answers=record.answers,
            conditional_questions_unlocked=_resolve_unlocked_conditionals(record.answers),
        )

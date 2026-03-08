from enum import Enum

from pydantic import BaseModel, Field


class WorksiteType(str, Enum):
    OFFICE = "office"
    FIELD = "field"
    MIXED = "mixed"


class HeadcountBand(str, Enum):
    MICRO = "1-4"
    SMALL = "5-19"
    MEDIUM = "20-99"
    LARGE = "100+"


class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    BOOLEAN = "boolean"


class QuestionTier(str, Enum):
    CORE = "core"
    CONDITIONAL = "conditional"


class QuestionOption(BaseModel):
    value: str
    label: str


class IntakeQuestion(BaseModel):
    id: str
    tier: QuestionTier
    question_type: QuestionType
    text: str
    options: list[QuestionOption] | None = None
    triggers_conditional: list[str] | None = None


class IntakeQuestionsResponse(BaseModel):
    naics_codes: list[str]
    core_questions: list[IntakeQuestion]
    conditional_questions: list[IntakeQuestion]


class IndustryIntakeAnswersRequest(BaseModel):
    answers: dict[str, str | list[str] | bool] = Field(
        ...,
        description="Map of question id to answer value(s)",
    )


class IndustryIntakeAnswersResponse(BaseModel):
    order_id: int
    answers: dict[str, str | list[str] | bool]
    conditional_questions_unlocked: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True

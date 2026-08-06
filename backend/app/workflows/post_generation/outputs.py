from pydantic import BaseModel, Field


class PlanOutput(BaseModel):
    angle: str
    outline: list[str] = Field(min_length=1)
    key_points: list[str] = Field(min_length=1)
    hook_direction: str


class ContentOutput(BaseModel):
    content: str = Field(min_length=1)


class ReviewOutput(ContentOutput):
    feedback: list[str] = []


class HookOutput(ContentOutput):
    hook: str = Field(min_length=1)


class CTAOutput(ContentOutput):
    cta: str = Field(min_length=1)


class GrammarOutput(ContentOutput):
    corrections: list[str] = []


class JudgeOutput(ContentOutput):
    approved: bool
    score: float = Field(ge=0, le=100)
    reasoning: str
    hook: str = Field(min_length=1)
    cta: str = Field(min_length=1)
    hashtags: list[str] = []

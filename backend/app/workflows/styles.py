from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Tone(StrEnum):
    PROFESSIONAL = "professional"
    CONVERSATIONAL = "conversational"
    AUTHORITATIVE = "authoritative"
    INSPIRATIONAL = "inspirational"
    EDUCATIONAL = "educational"


class Voice(StrEnum):
    FIRST_PERSON = "first_person"
    SECOND_PERSON = "second_person"
    THIRD_PERSON = "third_person"
    BRAND = "brand"


class SentenceRhythm(StrEnum):
    SHORT = "short"
    BALANCED = "balanced"
    VARIED = "varied"
    LONG_FORM = "long_form"


class VocabularyLevel(StrEnum):
    SIMPLE = "simple"
    GENERAL = "general"
    TECHNICAL = "technical"
    EXECUTIVE = "executive"


class FormattingStyle(BaseModel):
    model_config = ConfigDict(frozen=True)

    use_paragraph_breaks: bool = True
    use_bullets: bool = False
    use_numbered_lists: bool = False
    max_paragraph_sentences: int = Field(default=3, ge=1, le=10)


class EngagementStyle(BaseModel):
    model_config = ConfigDict(frozen=True)

    use_hook: bool = True
    use_storytelling: bool = False
    ask_questions: bool = True
    include_call_to_action: bool = True


class EmojiStyle(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    maximum_count: int = Field(default=3, ge=0, le=20)
    placement: str = Field(default="inline", pattern="^(inline|line_start|line_end)$")


class HashtagStyle(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    minimum_count: int = Field(default=3, ge=0, le=30)
    maximum_count: int = Field(default=5, ge=0, le=30)
    placement: str = Field(default="end", pattern="^(inline|end)$")

    @model_validator(mode="after")
    def validate_range(self) -> "HashtagStyle":
        if self.minimum_count > self.maximum_count:
            raise ValueError("minimum_count cannot exceed maximum_count")
        return self


class StyleProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=255)
    tone: Tone = Tone.PROFESSIONAL
    voice: Voice = Voice.FIRST_PERSON
    rhythm: SentenceRhythm = SentenceRhythm.VARIED
    vocabulary: VocabularyLevel = VocabularyLevel.GENERAL
    formatting: FormattingStyle = Field(default_factory=FormattingStyle)
    engagement: EngagementStyle = Field(default_factory=EngagementStyle)
    emoji: EmojiStyle = Field(default_factory=EmojiStyle)
    hashtags: HashtagStyle = Field(default_factory=HashtagStyle)
    preferred_terms: tuple[str, ...] = ()
    avoided_terms: tuple[str, ...] = ()
    custom_rules: tuple[str, ...] = ()


class StyleEngine:
    def merge(self, base: StyleProfile, overrides: dict) -> StyleProfile:
        values = base.model_dump(mode="python")
        self._deep_merge(values, overrides)
        return StyleProfile.model_validate(values)

    def prompt_variables(self, style: StyleProfile) -> dict[str, str]:
        return {
            "style_name": style.name,
            "style_tone": style.tone.value,
            "style_voice": style.voice.value,
            "style_rhythm": style.rhythm.value,
            "style_vocabulary": style.vocabulary.value,
            "style_instructions": self.render_instructions(style),
        }

    def render_instructions(self, style: StyleProfile) -> str:
        instructions = [
            f"Tone: {style.tone.value}.",
            f"Voice: {style.voice.value}.",
            f"Sentence rhythm: {style.rhythm.value}.",
            f"Vocabulary: {style.vocabulary.value}.",
            f"Keep paragraphs to at most {style.formatting.max_paragraph_sentences} sentences.",
        ]
        if style.formatting.use_paragraph_breaks:
            instructions.append("Use clear paragraph breaks for readability.")
        if style.formatting.use_bullets:
            instructions.append("Use bullet points where they improve clarity.")
        if style.formatting.use_numbered_lists:
            instructions.append("Use numbered lists for ordered steps or ranked points.")
        if style.engagement.use_hook:
            instructions.append("Open with a concise, relevant hook.")
        if style.engagement.use_storytelling:
            instructions.append("Use a concise storytelling structure.")
        if style.engagement.ask_questions:
            instructions.append("Use relevant questions to encourage reflection.")
        if style.engagement.include_call_to_action:
            instructions.append("Close with a clear call to action.")
        if style.emoji.enabled:
            instructions.append(
                f"Use at most {style.emoji.maximum_count} emojis with "
                f"{style.emoji.placement} placement."
            )
        else:
            instructions.append("Do not use emojis.")
        if style.hashtags.enabled:
            instructions.append(
                "Use between "
                f"{style.hashtags.minimum_count} and {style.hashtags.maximum_count} hashtags "
                f"with {style.hashtags.placement} placement."
            )
        else:
            instructions.append("Do not use hashtags.")
        if style.preferred_terms:
            instructions.append(f"Prefer these terms: {', '.join(style.preferred_terms)}.")
        if style.avoided_terms:
            instructions.append(f"Avoid these terms: {', '.join(style.avoided_terms)}.")
        instructions.extend(style.custom_rules)
        return "\n".join(instructions)

    @classmethod
    def _deep_merge(cls, target: dict, overrides: dict) -> None:
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                cls._deep_merge(target[key], value)
            else:
                target[key] = value

from typing import Literal
import unicodedata
from pydantic import BaseModel, ConfigDict, Field, field_validator
import regex


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    description: str = Field(min_length=3, max_length=1000)
    language: Literal['en', 'hi', 'both'] = 'en'
    starting_letter: str | None = Field(default=None, max_length=8)
    approximate_length: int | None = Field(default=None, ge=1, le=60, strict=True)
    part_of_speech: Literal['noun', 'verb', 'adjective', 'adverb'] | None = None
    limit: int = Field(default=5, ge=1, le=10, strict=True)

    @field_validator('starting_letter')
    @classmethod
    def validate_prefix(cls, value):
        if not value:
            return None
        value = unicodedata.normalize('NFC', value)
        if not regex.fullmatch(r'[\p{L}\p{M}]+', value):
            raise ValueError('Starting letters may contain only letters and combining marks')
        return value.casefold()


class Suggestion(BaseModel):
    word: str
    definition: str
    definition_language: Literal['en', 'hi']
    language: Literal['en', 'hi']
    part_of_speech: str
    score: float
    semantic_score: float
    tfidf_score: float
    source: str
    source_url: str


class PredictionResponse(BaseModel):
    translated_query: str | None = None
    suggestions: list[Suggestion]
    method: str
    elapsed_ms: float
    warnings: list[str] = Field(default_factory=list)

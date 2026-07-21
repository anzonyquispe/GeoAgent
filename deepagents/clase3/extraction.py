from typing import Literal
from pydantic import BaseModel, Field
from agent import local_llm


class FireQuery(BaseModel):
    """Structured representation of what the user is asking for, extracted from free text."""
    region: str | None = Field(
        default=None, description="Peru department/region mentioned by the user, if any"
    )
    year: int | None = Field(
        default=None, description="Year mentioned for fire analysis, if any"
    )
    intent: Literal["fire_analysis", "general_question", "other"] = Field(
        description="What the user is trying to do"
    )


_extractor = local_llm.with_structured_output(FireQuery)


def extract_query(text: str) -> FireQuery:
    """Extract structured intent/parameters from a free-text user message."""
    return _extractor.invoke(
        f"Extract the structured query from this user message:\n\n{text}"
    )

from pydantic import BaseModel
from typing import Literal

class ParsedChunk(BaseModel):
    doc_id: str
    source_file: str
    page_num: int
    chunk_id: str
    chunk_type: Literal["text", "table", "header"]
    chunk_txt: str


class RawTriplets(ParsedChunk):
    question: str
    answer: str
    context: str

class ScoredTriplets(RawTriplets):
    faithfulness: float
    answer_relevancy: float
    scored_at: str

class TieredTriplets(ScoredTriplets):
    quality_tier: Literal["bronze", "silver", "gold"]
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class DimensionGroup:
    id: Optional[int]
    docket_id: Optional[int]
    group_index: int
    length: float
    breadth: float
    height: float
    num_packages: int
    dimension_weight: float
    ai_original_length: str
    ai_original_breadth: str
    ai_original_height: str
    ai_original_num_packages: str

@dataclass
class Docket:
    id: Optional[int]
    job_id: Optional[int]
    image_filename: str
    image_hash: str
    original_filename: str
    uploaded_at: str
    status: str
    docket_number: Optional[str]
    actual_weight: Optional[float]
    total_packages: Optional[int]
    ai_raw_response: str
    ai_confidence_notes: str
    rejection_reasons: str
    processed_at: Optional[str]
    human_reviewed: bool
    human_reviewer: Optional[str]
    human_reviewed_at: Optional[str]
    dimensions: List[DimensionGroup]

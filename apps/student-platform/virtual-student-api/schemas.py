from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


# ── Feature Definitions ──────────────────────────────────────────────────────

class FeatureDefinitionCreate(BaseModel):
    key: str
    display_name: str
    description: str
    value_type: str
    value_options: Optional[List[str]] = None
    value_range: Optional[dict] = None
    default_value: Optional[str] = None
    category: str


class FeatureDefinitionUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    value_options: Optional[List[str]] = None
    value_range: Optional[dict] = None
    default_value: Optional[str] = None
    category: Optional[str] = None


class FeatureDefinitionResponse(BaseModel):
    key: str
    display_name: str
    description: str
    value_type: str
    value_options: Optional[List[str]] = None
    value_range: Optional[dict] = None
    default_value: Optional[str] = None
    category: str
    is_builtin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Feature Values ────────────────────────────────────────────────────────────

class FeatureValueInput(BaseModel):
    feature_key: str
    value: str


class FeatureValueResponse(BaseModel):
    feature_key: str
    display_name: str
    description: str
    category: str
    value: str


# ── Virtual Students ──────────────────────────────────────────────────────────

class VirtualStudentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    subject_id: str
    feature_values: Optional[List[FeatureValueInput]] = []


class VirtualStudentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    subject_id: Optional[str] = None
    feature_values: Optional[List[FeatureValueInput]] = None


class VirtualStudentListItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    subject_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VirtualStudentDetail(VirtualStudentListItem):
    feature_values: List[FeatureValueResponse]


class VirtualStudentList(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[VirtualStudentListItem]


# ── Seed ──────────────────────────────────────────────────────────────────────

class SeedTemplate(BaseModel):
    name: str
    description: Optional[str] = None
    feature_values: Optional[dict] = {}


class SeedRequest(BaseModel):
    subject_id: str
    templates: List[SeedTemplate]


# ── Stats ─────────────────────────────────────────────────────────────────────

class CategoryDistributionItem(BaseModel):
    value: str
    count: int
    ratio: float


class NumericBucket(BaseModel):
    range: str
    count: int


class NumericDistribution(BaseModel):
    min: float
    max: float
    mean: float
    buckets: List[NumericBucket]


class FeatureDistribution(BaseModel):
    feature_key: str
    display_name: str
    category: str
    value_type: str
    distribution: Any


class StatsResponse(BaseModel):
    subject_id: Optional[str] = None
    total_students: int
    feature_distributions: List[FeatureDistribution]

"""Pydantic response and request schemas for the FastAPI backend."""

from backend.api.schemas.advanced_ai import (
    AdvancedAIRequest,
    AdvancedAIResultResponse,
)
from backend.api.schemas.analytics import (
    AnalyticsResponse,
    AssigneeAnalyticsModel,
    CorpusAnalyticsModel,
    QualityAnalyticsModel,
    TechnologyAnalyticsModel,
    TrendAnalyticsModel,
)
from backend.api.schemas.common import HealthResponse, MessageResponse
from backend.api.schemas.data_sources import (
    DataSourceLoadResponse,
    DataSourceStatusResponse,
)
from backend.api.schemas.insights import DatasetInsightsResponse
from backend.api.schemas.landscape import (
    LandscapeEdgeModel,
    LandscapeNodeModel,
    LandscapeResponse,
)
from backend.api.schemas.patents import (
    FilterOptionsResponse,
    PatentCardModel,
    PatentProfileResponse,
    PatentSearchResponse,
    RelatedPatentModel,
    RelatedPatentsResponse,
)

__all__ = [
    "AdvancedAIRequest",
    "AdvancedAIResultResponse",
    "AnalyticsResponse",
    "AssigneeAnalyticsModel",
    "CorpusAnalyticsModel",
    "DataSourceLoadResponse",
    "DataSourceStatusResponse",
    "DatasetInsightsResponse",
    "FilterOptionsResponse",
    "HealthResponse",
    "LandscapeEdgeModel",
    "LandscapeNodeModel",
    "LandscapeResponse",
    "MessageResponse",
    "PatentCardModel",
    "PatentProfileResponse",
    "PatentSearchResponse",
    "QualityAnalyticsModel",
    "RelatedPatentModel",
    "RelatedPatentsResponse",
    "TechnologyAnalyticsModel",
    "TrendAnalyticsModel",
]

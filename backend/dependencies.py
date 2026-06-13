"""Dependency providers wiring application services into FastAPI routes.

Routes stay thin: they receive ready-to-use application services through
``Depends(...)`` and call them with request data. No analysis, clustering,
search ranking, similarity, or GA logic lives here or in routes — only
shared service construction and small read-only helpers around the local
storage repository.
"""

from functools import lru_cache

from fastapi import Depends

from backend.core.config import BackendConfig, get_backend_config
from src.application import (
    AdvancedAIService,
    AnalyticsService,
    DataSourceService,
    InsightsService,
    LandscapeService,
    PatentProfileService,
    PatentSearchService,
)
from src.models.patent import PatentRecord
from src.services.pipeline_service import PipelineService


@lru_cache(maxsize=1)
def _build_pipeline_service() -> PipelineService:
    """Construct the shared pipeline service exactly once per process."""
    config = get_backend_config()
    service = PipelineService.from_settings(config.app_settings)
    service.initialize_storage()
    service.ensure_canonical_corpus_loaded()
    return service


def get_pipeline_service() -> PipelineService:
    """FastAPI dependency: shared pipeline service backed by local SQLite."""
    return _build_pipeline_service()


def get_patent_search_service() -> PatentSearchService:
    """FastAPI dependency: stateless patent search service."""
    return PatentSearchService()


def get_patent_profile_service() -> PatentProfileService:
    """FastAPI dependency: patent profile + related-patents service."""
    return PatentProfileService()


def get_landscape_service() -> LandscapeService:
    """FastAPI dependency: landscape graph assembly service."""
    return LandscapeService()


def get_insights_service() -> InsightsService:
    """FastAPI dependency: dataset-level insights service."""
    return InsightsService()


def get_analytics_service() -> AnalyticsService:
    """FastAPI dependency: filter-aware visual analytics service."""
    return AnalyticsService()


def get_advanced_ai_service() -> AdvancedAIService:
    """FastAPI dependency: Genetic Algorithm optimization service."""
    return AdvancedAIService()


def get_data_source_service() -> DataSourceService:
    """FastAPI dependency: local data-source status and loading service."""
    return DataSourceService()


def get_records(
    pipeline_service: PipelineService = Depends(get_pipeline_service),
) -> list[PatentRecord]:
    """FastAPI dependency: fresh patent records from local storage."""
    return pipeline_service.fetch_saved_patents()


def reset_pipeline_service_cache() -> None:
    """Reset the cached pipeline service. Used by tests to swap settings."""
    _build_pipeline_service.cache_clear()


__all__ = [
    "BackendConfig",
    "get_advanced_ai_service",
    "get_analytics_service",
    "get_backend_config",
    "get_data_source_service",
    "get_insights_service",
    "get_landscape_service",
    "get_patent_profile_service",
    "get_patent_search_service",
    "get_pipeline_service",
    "get_records",
    "reset_pipeline_service_cache",
]

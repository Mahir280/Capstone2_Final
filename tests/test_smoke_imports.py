"""Smoke tests for scaffold module imports."""

import importlib


def test_project_modules_import() -> None:
    modules = [
        "backend.main",
        "backend.dependencies",
        "backend.api.routes",
        "backend.api.schemas",
        "src.config.settings",
        "src.models.enums",
        "src.models.patent",
        "src.models.analysis",
        "src.acquisition.file_importer",
        "src.acquisition.patent_page_fetcher",
        "src.acquisition.source_adapter_base",
        "src.preprocessing.normalizer",
        "src.features",
        "src.clustering",
        "src.optimization",
        "src.insights",
        "src.application",
        "src.application._formatting",
        "src.application.advanced_ai_service",
        "src.application.data_source_service",
        "src.application.dto",
        "src.application.insights_service",
        "src.application.landscape_service",
        "src.application.patent_profile_service",
        "src.application.patent_search_service",
        "src.visualization",
        "src.storage.sqlite_repository",
        "src.services.pipeline_service",
        "src.utils.paths",
    ]

    for module in modules:
        importlib.import_module(module)

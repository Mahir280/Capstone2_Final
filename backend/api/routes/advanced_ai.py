"""Advanced AI (Genetic Algorithm) optimization endpoint."""

from dataclasses import asdict

from fastapi import APIRouter, Depends

from backend.api.schemas import AdvancedAIRequest, AdvancedAIResultResponse
from backend.dependencies import get_advanced_ai_service, get_records
from src.application import AdvancedAIService
from src.models.patent import PatentRecord

router = APIRouter(prefix="/api/advanced-ai", tags=["advanced-ai"])


@router.post("/run", response_model=AdvancedAIResultResponse)
def run_advanced_ai(
    request: AdvancedAIRequest | None = None,
    records: list[PatentRecord] = Depends(get_records),
    advanced_ai_service: AdvancedAIService = Depends(get_advanced_ai_service),
) -> AdvancedAIResultResponse:
    """Run Genetic Algorithm optimization through the application service."""
    config = request or AdvancedAIRequest()
    result_dto = advanced_ai_service.run_optimization(
        records,
        baseline_cluster_count=config.baseline_cluster_count,
        population_size=config.population_size,
        generations=config.generations,
        mutation_rate=config.mutation_rate,
        random_state=config.random_state,
    )
    return AdvancedAIResultResponse.model_validate(asdict(result_dto))

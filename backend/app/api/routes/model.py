"""Prediction endpoints for trained ML models."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.core.security import require_permission
from app.schemas.schemas import FailurePredictionRequest, FailurePredictionResponse
from app.services import audit_service
from app.services.failure_prediction_service import (
    FailurePredictionError,
    FailurePredictionUnavailable,
    predict_failure,
)

router = APIRouter()


@router.post("/predict-failure", response_model=FailurePredictionResponse)
async def predict_failure_endpoint(
    request: FailurePredictionRequest,
    current_user: dict = Depends(require_permission("failures:predict")),
    db: AsyncSession = Depends(get_db),
):
    """Classify CI/CD failure logs and return the most likely root cause."""
    actor = current_user.get("username") or current_user.get("sub") or "unknown"
    try:
        result = predict_failure(request.log_text)

        # Log the successful prediction
        await audit_service.log_prediction(
            db,
            log_text=request.log_text,
            predicted_label=result.get("label", "unknown_failure"),
            confidence=result.get("confidence"),
            suggested_fix=result.get("suggested_fix"),
            actor=actor,
            source="api",
        )
        if result.get("recommendation"):
            await audit_service.log_fix_recommendation(
                db,
                failure_label=result.get("label", "unknown_failure"),
                recommendation=result.get("recommendation"),
                actor=actor,
                source="api",
            )

        return result
    except FailurePredictionUnavailable as exc:
        await audit_service.log_execution(
            db,
            tool_name="failure_prediction_model",
            action_summary="Failure prediction model unavailable",
            status="failed",
            actor=actor,
            tool_input={"log_length": len(request.log_text or "")},
            tool_output={},
            error=str(exc),
            source="api",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except FailurePredictionError as exc:
        await audit_service.log_execution(
            db,
            tool_name="failure_prediction_model",
            action_summary="Failure prediction failed",
            status="failed",
            actor=actor,
            tool_input={"log_length": len(request.log_text or "")},
            tool_output={},
            error=str(exc),
            source="api",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failure prediction failed. Please try again.",
        ) from exc
    except Exception as exc:
        logger.error(
            "failure_prediction.endpoint_failed",
            error_type=exc.__class__.__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failure prediction failed. Please try again.",
        ) from exc

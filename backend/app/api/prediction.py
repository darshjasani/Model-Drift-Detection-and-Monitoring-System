"""Prediction API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    PredictionRequest, PredictionResponse,
    FeedbackRequest, FeedbackResponse,
    ModelInfo
)
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/api/v1", tags=["predictions"])


@router.post("/predict", response_model=PredictionResponse)
async def make_prediction(
    request: PredictionRequest,
    db: Session = Depends(get_db)
):
    """
    Make a prediction on transaction
    
    - **transaction_id**: Unique transaction identifier
    - **features**: Dictionary of feature values
    - **timestamp**: Optional timestamp
    """
    try:
        service = PredictionService(db)
        result = await service.make_prediction(
            transaction_id=request.transaction_id,
            features=request.features,
            timestamp=request.timestamp
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db)
):
    """
    Submit ground truth feedback for a prediction
    
    - **transaction_id**: Transaction ID to provide feedback for
    - **actual_label**: Actual label (0 or 1)
    - **label_source**: Source of the label (e.g., "manual", "customer_report")
    """
    try:
        service = PredictionService(db)
        result = await service.submit_feedback(
            transaction_id=request.transaction_id,
            actual_label=request.actual_label,
            label_source=request.label_source,
            feedback_timestamp=request.feedback_timestamp,
            confidence=request.confidence,
            notes=request.notes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {str(e)}")


@router.get("/model/info", response_model=ModelInfo)
async def get_model_info(db: Session = Depends(get_db)):
    """Get current model information"""
    try:
        service = PredictionService(db)
        info = service.get_model_info()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


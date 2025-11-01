from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from ..database import get_db
from ..rag import models
from . import schemas

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("", response_model=List[schemas.CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """Get all active categories with their insight types"""
    categories = db.query(models.AnalysisCategory)\
        .filter(models.AnalysisCategory.is_active == True)\
        .options(
            joinedload(models.AnalysisCategory.insight_types)
            .joinedload(models.CategoryInsightType.insight_type)
        )\
        .all()
    
    return [schemas.CategoryResponse.from_orm(cat) for cat in categories]


@router.get("/{category_id}/insights", response_model=List[schemas.InsightTypeResponse])
def get_category_insights(
    category_id: str,
    db: Session = Depends(get_db)
):
    """Get all insight types for a specific category"""
    category = db.query(models.AnalysisCategory)\
        .options(
            joinedload(models.AnalysisCategory.insight_types)
            .joinedload(models.CategoryInsightType.insight_type)
        )\
        .filter(models.AnalysisCategory.id == category_id)\
        .first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Sort by display_order
    sorted_insights = sorted(
        category.insight_types, 
        key=lambda x: x.display_order
    )
    
    return [
        schemas.InsightTypeResponse.from_orm(cit.insight_type) 
        for cit in sorted_insights
    ]
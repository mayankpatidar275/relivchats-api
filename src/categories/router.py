from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import time
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from ..database import get_async_db
from ..rag import models
from . import schemas
from ..logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=List[schemas.CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_async_db)):
    """Get all active categories with their insight types"""
    
    logger.debug("Fetching categories")
    
    try:

        start = time.time()
        await db.execute(select(1))  # tiniest possible query
        logger.info(f"select(1) took {(time.time()-start)*1000:.1f}ms")

        start = time.time()
        logger.info(f"DB query START")
        
        result = await db.execute(
            select(models.AnalysisCategory)
            .where(models.AnalysisCategory.is_active)
            .options(
                selectinload(models.AnalysisCategory.insight_types)
                .selectinload(models.CategoryInsightType.insight_type)
            )
        )
        logger.info(f"DB query DONE in {(time.time()-start)*1000:.1f}ms")
        categories = result.scalars().all()
        
        logger.debug(f"Found {len(categories)} categories")
        
        return [schemas.CategoryResponse.from_orm(cat) for cat in categories]
        
    except Exception as e:
        logger.error(f"Failed to fetch categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch categories")


@router.get("/{category_id}/insights", response_model=List[schemas.InsightTypeResponse])
async def get_category_insights(
    category_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """Get all insight types for a specific category"""
    
    logger.debug(f"Fetching insights for category {category_id}")
    
    try:
        result = await db.execute(
            select(models.AnalysisCategory)
            .where(models.AnalysisCategory.id == category_id)
            .options(
                selectinload(models.AnalysisCategory.insight_types)
                .selectinload(models.CategoryInsightType.insight_type)
            )
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Sort by display_order
        sorted_insights = sorted(
            category.insight_types,
            key=lambda x: x.display_order
        )
        
        logger.debug(f"Found {len(sorted_insights)} insights")
        
        return [
            schemas.InsightTypeResponse.from_orm(cit.insight_type)
            for cit in sorted_insights
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch insights")
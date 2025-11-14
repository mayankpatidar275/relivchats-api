from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

class InsightTypeResponse(BaseModel):
    id: UUID
    name: str
    display_title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    is_premium: bool
    credit_cost: int
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, db_insight_type):
        return cls(
            id=db_insight_type.id,
            name=db_insight_type.name,
            display_title=db_insight_type.display_title,
            description=db_insight_type.description,
            icon=db_insight_type.icon,
            is_premium=db_insight_type.is_premium,
            credit_cost=db_insight_type.credit_cost
        )

class CategoryResponse(BaseModel):
    id: UUID
    name: str  # slug like 'romantic', 'friendship'
    display_name: str  # 'Romantic Relationship'
    description: Optional[str] = None
    icon: Optional[str] = None
    insight_types: List[InsightTypeResponse] = []
    insights_count: int
    base_cost: int  # Total cost of all insights
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, db_category):
        # Calculate insights count and base cost
        insights = [
            cit.insight_type 
            for cit in db_category.insight_types 
            if cit.insight_type.is_active
        ]
        
        return cls(
            id=db_category.id,
            name=db_category.name,
            display_name=db_category.display_name,
            description=db_category.description,
            icon=db_category.icon,
            insight_types=[
                InsightTypeResponse.from_orm(insight) 
                for insight in sorted(
                    insights, 
                    key=lambda x: next(
                        (cit.display_order for cit in db_category.insight_types 
                         if cit.insight_type_id == x.id), 
                        0
                    )
                )
            ],
            insights_count=len(insights),
            # base_cost=sum(insight.credit_cost for insight in insights)
            base_cost=db_category.credit_cost
        )

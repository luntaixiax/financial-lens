from datetime import date
from functools import partial
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field

from src.app.utils.base import EnhancedBaseModel
from src.app.model.enums import PropertyType, PropertyTransactionType
from src.app.utils.tools import id_generator

class Property(EnhancedBaseModel):
    property_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='prop-',
            length=8,
        ),
        frozen=True,
    )
    property_name: str
    property_type: PropertyType
    pur_dt: date
    pur_price: float = Field(
        description="Purchase price, expressed in account curreny"
    )
    pur_acct_id: str
    
class PropertyTransaction(EnhancedBaseModel):
    trans_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='proptrans-',
            length=8,
        ),
        frozen=True,
    )
    property_id: str
    trans_dt: date
    trans_type: PropertyTransactionType
    trans_amount: float = Field(
        description="Depreciation/Impairment/Appreciation amount, expressed in purchase curreny"
    )

class _PropertyPriceBrief(EnhancedBaseModel):
    pur_price: float = 0.0
    acc_depreciation: float = 0.0
    acc_appreciation: float = 0.0
    acc_impairment: float = 0.0
    
    @computed_field
    def value(self) -> float:
        return self.pur_price + self.acc_depreciation - self.acc_appreciation - self.acc_impairment
    
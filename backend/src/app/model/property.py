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
    tax: float = Field(
        default=0.0,
        description="Sales tax, expressed in account curreny, only include if need to record as input tax credit"
    )
    pur_acct_id: str
    
    @computed_field
    def pur_cost(self) -> float:
        return self.pur_price - self.tax
    
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
    pur_cost: float = 0.0 # purchase cost, net of sales tax
    acc_depreciation: float = 0.0
    acc_appreciation: float = 0.0
    acc_impairment: float = 0.0
    
    @computed_field
    def value(self) -> float:
        return self.pur_cost + self.acc_depreciation - self.acc_appreciation - self.acc_impairment
    
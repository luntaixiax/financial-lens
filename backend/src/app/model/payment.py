from datetime import date
from functools import partial
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field
from src.app.model.enums import CurType, PaymentDirection
from src.app.utils.tools import get_default_tax_rate, id_generator
from src.app.utils.base import EnhancedBaseModel

class PaymentItem(EnhancedBaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    payment_item_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='pmtitem-',
            length=8,
        ),
        frozen=True,
    )
    


class Payment(EnhancedBaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    payment_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='pmt-',
            length=8,
        ),
        frozen=True,
    )
    payment_num: str
    direction: PaymentDirection
    payment_dt: date
    payment_acct_id: str = Field(
        description='Use which account to make/receive payment (Debit/Credit to)'
    )
    payment_amount: float = Field(
        description='Payment amount (before bank fee), in payment account currency.'
    )
    payment_fee: float = Field(
        0.0,
        description='Payment fee charged by bank, expressed in payment currency'
    )
    ref_num: str | None = Field(None)
    note: str | None = Field(None)
    
from datetime import date
from functools import partial
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field
from src.app.model.enums import CurType, EntityType
from src.app.utils.tools import id_generator
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
    invoice_id: str = Field(
        description='Sales/Purchase invoice id associated'
    )
    payment_amount: float = Field(
        description='Payment amount (before bank fee), in payment account currency.'
    )
    payment_amount_raw: float = Field(
        description='Payment amount (before bank fee), in invoice account currency. The difference will be recorded as FX gain/loss'
    )

class _PaymentBrief(EnhancedBaseModel):
    payment_id: str
    payment_num: str
    payment_dt: date
    entity_type: EntityType
    currency: CurType
    payment_acct_name: str
    num_invoices: int
    invoice_num_strs: str
    gross_payment_base: float = Field(description='payment amount before fee, in base currency')
    gross_payment_raw: float = Field(description='payment amount before fee, in raw currency for that payment')
    
    @computed_field
    def invoice_nums(self) -> list[str]:
        return self.invoice_num_strs.split(',')

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
    payment_dt: date
    entity_type: EntityType = Field(
        description='Indicate whether a customer (receive) or supplier (pay) payment'
    )
    payment_items: list[PaymentItem] = Field(
        min_length=1
    )
    payment_acct_id: str = Field(
        description='Use which account to make/receive payment (Debit/Credit to)'
    )
    payment_fee: float = Field(
        0.0,
        description='Payment fee charged by bank, expressed in payment currency'
    )
    ref_num: str | None = Field(
        None,
        description='Bank transfer reference number'
    )
    note: str | None = Field(None)
    
    @computed_field()
    def gross_payment(self) -> float:
        # total payment in payment currency (before payment fee)
        return sum(payment_item.payment_amount for payment_item in self.payment_items)
    
    @computed_field()
    def net_payment(self) -> float:
        # total payment in payment currency (after payment fee)
        if self.entity_type == EntityType.CUSTOMER:
            # net payment received will be lower (we pay fee)
            return self.gross_payment - self.payment_fee
        else:
            # net payment paid will be higher (we pay fee)
            return self.gross_payment + self.payment_fee
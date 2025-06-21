from datetime import date
from functools import partial
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field
from src.app.model.enums import CurType
from src.app.utils.tools import get_default_tax_rate, id_generator
from src.app.utils.base import EnhancedBaseModel

class Merchant(BaseModel):
    merchant: str | None = Field(None)
    platform: str | None = Field(None)
    ref_no: str | None = Field(None)

class ExpInfo(BaseModel):
    merchant: Merchant
    external_pmt_acct: str | None = Field(None)


class ExpenseItem(EnhancedBaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    expense_item_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='expitem-',
            length=12,
        ),
        frozen=True,
    )
    expense_acct_id: str = Field(
        description='Expense account (Dedit to)'
    )
    amount_pre_tax: float = Field(
        description='Amount pretax, expressed in currency charged'
    )
    tax_rate: float = Field(
        default_factory=get_default_tax_rate
    )
    description: str | None = Field(None)
    
    @computed_field()
    def tax_amount(self) -> float:
        # in item currency
        return self.amount_pre_tax * self.tax_rate
    
    @computed_field()
    def amount_after_tax(self) -> float:
        # in item currency
        return self.amount_pre_tax * (1 + self.tax_rate)

class _ExpenseBrief(EnhancedBaseModel):
    expense_id: str
    expense_dt: date
    merchant: str | None
    currency: CurType
    payment_acct_name: str
    expense_acct_name_strs: str
    total_raw_amount: float = Field(description='Total amount in expense currency (after tax)')
    total_base_amount: float = Field(description='Total amount in base currency (after tax)')
    has_receipt: bool
    
    @computed_field
    def expense_acct_names(self) -> list[str]:
        return self.expense_acct_name_strs.split(',')
    
class _ExpenseSummaryBrief(EnhancedBaseModel):
    expense_type: str
    total_base_amount: float

class Expense(EnhancedBaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    expense_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='exp-',
            length=11,
        ),
        frozen=True,
    )
    #billable: bool = Field(False)
    expense_dt: date
    currency: CurType = Field(
        description='Curreny charged (can be different from curreny paid)'
    )
    expense_items: list[ExpenseItem] = Field(min_length=1)
    payment_acct_id: str = Field(
        description='Use which account to make payment (Credit to)'
    )
    payment_amount: float = Field(
        description='Payment amount, in payment account currency. If payment currency equals expense currency, this amount should equal to self.total'
    )
    exp_info: ExpInfo
    note: str | None = Field(None)
    receipts: list[str] | None =  Field(
        None,
        description='List of Receipt artifact path (relative)'
    )
    
    @computed_field()
    def subtotal(self) -> float:
        # in item currency, all item before shipping
        return sum(item.amount_pre_tax for item in self.expense_items)
    
    @computed_field()
    def tax_amount(self) -> float:
        # in item currency
        return sum(item.tax_amount for item in self.expense_items)
    
    @computed_field()
    def total(self) -> float:
        # in item currency
        return self.subtotal + self.tax_amount
    
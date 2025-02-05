from datetime import date
from functools import partial
import math
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field
from src.app.model.enums import CurType, EntityType, ItemType, UnitType
from src.app.utils.tools import get_default_tax_rate, id_generator
from src.app.utils.base import EnhancedBaseModel

class Item(EnhancedBaseModel):
    item_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='item-',
            length=8,
        ),
        frozen=True,
    )
    name: str
    item_type: ItemType = Field(ItemType.SERVICE)
    entity_type: EntityType
    unit: UnitType = Field(UnitType.HOUR)
    unit_price: float
    currency: CurType
    default_acct_id: str
    
class InvoiceItem(EnhancedBaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    invoice_item_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='invitem-',
            length=8,
        ),
        frozen=True,
    )
    item: Item
    quantity: float = Field(ge=0)
    acct_id: str = Field("") # will be overwritten in validator
    tax_rate: float = Field(
        default_factory=get_default_tax_rate
    )
    discount_rate: float = Field(
        default=0, 
        ge=0, 
        le=1
    ) # discount rate
    description: str | None = Field(None)
    
    @model_validator(mode='after')
    def set_default_acct(self):
        if self.acct_id == "":
            self.acct_id = self.item.default_acct_id
        return self
    
    @computed_field()
    def amount_pre_discount(self) -> float:
        # in item currency
        return self.quantity * self.item.unit_price
    
    @computed_field()
    def amount_pre_tax(self) -> float:
        # in item currency
        return self.amount_pre_discount * (1 - self.discount_rate)
    
    @computed_field()
    def tax_amount(self) -> float:
        # in item currency
        return self.amount_pre_tax * self.tax_rate
    
    @computed_field()
    def amount_after_tax(self) -> float:
        # in item currency
        return self.amount_pre_tax * (1 + self.tax_rate)
    
class GeneralInvoiceItem(EnhancedBaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    ginv_item_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='ginvitem-',
            length=8,
        ),
        frozen=True,
        description='General Invoice Item ID'
    )
    incur_dt: date = Field(
        description='Incur date, can be different from invoice date'
    )
    acct_id: str = Field(
        description='Inc/Exp Account to be credit(sales)/debit(purchase) to'
    )
    currency: CurType = Field(
        description='Incured currency, can be different from invoice currency'
    )
    amount_pre_tax_raw: float = Field(
        description='Amount pretax, expressed in the incurred currency'
    )
    amount_pre_tax: float = Field(
        description='Amount pretax, expressed in the invoice currency'
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
    
    
class _InvoiceBrief(EnhancedBaseModel):
    invoice_id: str = Field(description='Invoice ID')
    invoice_num: str = Field(description='Invoice number')
    invoice_dt: date = Field(description='Invoice Date')
    entity_name: str = Field(description='Customer/Supplier to sent the invoice')
    entity_type: EntityType
    is_business: bool = Field(description='Is business or individual')
    subject: str = Field(description='Subject line of the invoice')
    currency: CurType = Field(description='Currency used for the invoice')
    num_invoice_items: int = Field(description='Total # of invoice items')
    total_raw_amount: float = Field(description='Total amount in invoice currency')
    total_base_amount: float = Field(description='Total amount in base currency')
    
class _InvoiceBalance(EnhancedBaseModel):
    invoice_id: str = Field(description='Invoice ID')
    currency: CurType = Field(description='Currency used for the invoice')
    raw_amount: float = Field(description='Total amount invoiced in invoice currency')
    paid_amount: float = Field(description='Total amount paid in invoice currency')
    
    @computed_field()
    def balance(self) -> float:
        return self.raw_amount - self.paid_amount
    
class Invoice(EnhancedBaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    invoice_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='inv-',
            length=8,
        ),
        frozen=True,
    )
    entity_type: EntityType
    entity_id: str = Field(
        description='Customer/Supplier Id'
    )
    invoice_num: str
    invoice_dt: date
    due_dt: date | None = Field(None)
    subject: str
    currency: CurType
    invoice_items: list[InvoiceItem] = Field([])
    ginvoice_items: list[GeneralInvoiceItem] = Field(
        [],
        description='General invoice item, e.g., billable expense'
    )
    shipping: float = Field(0) # shipping or handling (after tax)
    note: str | None = Field(None)
    
    @model_validator(mode='after')
    def validate_item_length(self):
        assert len(self.invoice_items) + len(self.ginvoice_items) >= 1, \
            "At least 1 of Invoice item or general invoice item should be sent, all missing!"
            
        return self
    
    @model_validator(mode='after')
    def validate_currency(self):
        if len(self.invoice_items) > 0:
            # make sure currency within all items are in same currency
            all_currency = set(inv_item.item.currency for inv_item in self.invoice_items)
            assert len(all_currency) == 1, \
                f"Only allow 1 currency across all invoice items, found: {all_currency}"
            # should match with main currency
            item_currency = list(all_currency)[0]
            assert item_currency == self.currency, \
                f"Invoice currency is set to be {self.currency}, while invoice items are of currency {item_currency}"
        return self
    
    @model_validator(mode='after')
    def validate_ginv_item(self):
        # if invoice currency=general incur currency, amount should be equal
        for ginv_item in self.ginvoice_items:
            if self.currency == ginv_item.currency:
                assert math.isclose(ginv_item.amount_pre_tax_raw, ginv_item.amount_pre_tax), \
                    f"Invoice currency = General Item currency ({self.currency}, but amount_pre_tax_raw ({ginv_item.amount_pre_tax_raw}) != amount_pre_tax ({ginv_item.amount_pre_tax})); General Item {ginv_item}"
        return self
    
    @model_validator(mode='after')
    def validate_item_type(self):
        # make sure entity type within all items are in same entity type
        all_etype = set(inv_item.item.entity_type for inv_item in self.invoice_items)
        assert len(all_etype) == 1, \
            f"Only allow 1 entity type across all invoice items, found: {all_etype}"
        # should match with main entity type
        item_entity = list(all_etype)[0]
        assert item_entity == self.entity_type, \
            f"Invoice entity type is set to be {self.entity_type}, while invoice items are of entity type {item_entity}"
        return self
        
    @computed_field()
    def subtotal_invitems(self) -> float:
        # in item currency (same as invoice currency), all item before shipping
        return sum(item.amount_pre_tax for item in self.invoice_items)
    
    @computed_field()
    def subtotal_ginvitems(self) -> float:
        # in invoice currency
        return sum(item.amount_pre_tax for item in self.ginvoice_items)
    
    @computed_field()
    def subtotal(self) -> float:
        # in item currency, all item before shipping
        return self.subtotal_invitems + self.subtotal_ginvitems
    
    @computed_field()
    def tax_amount(self) -> float:
        # in item currency
        tax = sum(item.tax_amount for item in self.invoice_items) \
            + sum(item.tax_amount for item in self.ginvoice_items)
        return tax
    
    @computed_field()
    def total(self) -> float:
        # in item currency
        return self.subtotal + self.tax_amount + self.shipping
from datetime import date
from functools import partial
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field
from src.app.model.enums import CurType, ItemType, UnitType
from src.app.utils.tools import get_default_tax_rate, id_generator


class Item(BaseModel):
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
    unit: UnitType = Field(UnitType.HOUR)
    unit_price: float
    currency: CurType
    default_acct_id: str
    
class InvoiceItem(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
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
    

class Invoice(BaseModel):
    invoice_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='inv-',
            length=8,
        ),
        frozen=True,
    )
    invoice_num: str
    invoice_dt: date
    due_dt: date | None = None
    customer_id: str
    subject: str
    invoice_items: list[InvoiceItem] = Field(min_length=1)
    shipping: float = Field(0) # shipping or handling (after tax)
    note: str | None = Field(None)
    
    @model_validator(mode='after')
    def validate_currency(self):
        # make sure currency within all items are in same currency
        all_currency = set(inv_item.item.currency for inv_item in self.invoice_items)
        assert len(all_currency) == 1
        return self
    
    @computed_field()
    def currency(self) -> CurType:
        return set(inv_item.item.currency for inv_item in self.invoice_items)[0]
    
    @computed_field()
    def subtotal(self) -> float:
        # in item currency, all item before shipping
        return sum(item.amount_pre_tax for item in self.invoice_items)
    
    @computed_field()
    def tax_amount(self) -> float:
        # in item currency
        return sum(item.tax_amount for item in self.invoice_items)
    
    @computed_field()
    def total(self) -> float:
        # in item currency
        return self.subtotal + self.tax_amount + self.shipping
from functools import partial
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.app.model.enums import BankAcctType, CurType
from src.app.utils.tools import id_generator

class Address(BaseModel):
    address1: str
    address2: str | None = Field(None)
    suite_no: str | int | None = Field(None)
    city: str
    state: str
    country: str
    postal_code: str
    
    @property
    def address_line(self) -> str:
        adress_line = ""
        if self.suite_no is not None:
            adress_line += f"{self.suite_no} - "
        adress_line += self.address1
        if self.address2 is not None:
            adress_line += f", {self.address2}"
            
        return adress_line
            
    @property
    def post_code_line(self) -> str:
        return f"{self.city}, {self.state}, {self.country}, {self.postal_code}"
    
class Contact(BaseModel):
    name: str
    email: str
    phone: str | None = Field(None)
    address: Address | None = Field(None)
    
class Customer(BaseModel):
    cust_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='cust-',
            length=8,
        ),
        frozen=True,
    )
    customer_name: str
    is_business: bool = Field(True)
    default_bill_curreny: CurType
    bill_contact: Contact
    ship_same_as_bill: bool = Field(True)
    ship_contact: Contact | None = Field(None)
    
    @model_validator(mode='after')
    def copy_ship_contact(self):
        if self.ship_same_as_bill:
            self.ship_contact = self.bill_contact
        return self
    
class Supplier(BaseModel):
    supplier_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='supp-',
            length=8,
        ),
        frozen=True,
    )
    supplier_name: str
    is_business: bool = Field(True)
    default_bill_curreny: CurType
    bill_contact: Contact
    ship_same_as_bill: bool = Field(True)
    ship_contact: Contact | None = Field(None)
    
    @model_validator(mode='after')
    def copy_ship_contact(self):
        if self.ship_same_as_bill:
            self.ship_contact = self.bill_contact
        return self
    
class Employee(BaseModel):
    employee_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='emply-',
            length=8,
        ),
        frozen=True,
    )
    employee_name: str
    contact: Contact
    
    
class BankAcct(BaseModel):
    bank_name: str
    bank_acct_number: str
    bank_acct_type: BankAcctType = Field(
        frozen=True
    )
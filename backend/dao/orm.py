from __future__ import annotations
import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from typing import List, Dict, Tuple
from sqlmodel import Field, SQLModel, Column, create_engine
from sqlalchemy import ForeignKey, Boolean, JSON, Integer, String, Text, Date, DateTime, Float, Numeric, DECIMAL, UniqueConstraint, inspect, INT, CHAR
from sqlalchemy_utils import EmailType, PasswordType, PhoneNumberType, ChoiceType, CurrencyType, PhoneNumber
from datetime import date, datetime
from model.enums import EntityType, BalShType, IncExpType, CurType, EntryType, EventType


class FxORM(SQLModel, table=True):
    __tablename__ = "currency"
    
    currency: CurType = Field(sa_column=Column(ChoiceType(CurType, impl = Integer()), primary_key = True, nullable = False))
    cur_dt: date = Field(sa_column=Column(Date(), primary_key = True, nullable = False))
    rate: float = Field(sa_column=Column(Float(), nullable = False))

class EntityORM(SQLModel, table=True):
    
    __tablename__ = "entity"
    
    entity_id: str = Field(sa_column=Column(String(length = 10), primary_key = True, nullable = False))
    name: str = Field(sa_column=Column(String(length = 50), nullable = False, unique = True))
    entity_type: EntityType = Field(sa_column=Column(ChoiceType(EntityType, impl = Integer()), nullable = False))
    email: str = Field(sa_column=Column(EmailType(), nullable = False))
    phone: str = Field(sa_column=Column(PhoneNumberType(), nullable = True))
    address: dict = Field(sa_column=Column(JSON(), nullable = True))
    avatar: str = Field(sa_column=Column(String(length = 50), nullable = True))


class AcctBalshORM(SQLModel, table=True):
    
    __tablename__ = "acct_balsh"
    
    acct_id: str = Field(sa_column=Column(String(length = 10), primary_key = True, nullable = False))
    acct_name: str = Field(sa_column=Column(String(length = 50), nullable = False, unique = False))
    entity_id: str = Field(sa_column=Column(String(length = 10), ForeignKey('entity.entity_id', onupdate = 'CASCADE'), primary_key = False, nullable = False))
    acct_type: BalShType = Field(sa_column=Column(ChoiceType(BalShType, impl = Integer()), nullable = False))
    currency: CurType = Field(sa_column=Column(ChoiceType(CurType, impl = Integer()), nullable = False))
    accrual: bool = Field(sa_column=Column(Boolean(), nullable = False, unique = False))
    
class AcctIncExpORM(SQLModel, table=True):
    
    __tablename__ = "acct_incexp"
    
    acct_id: str = Field(sa_column=Column(String(length = 10), primary_key = True, nullable = False))
    acct_name: str = Field(sa_column=Column(String(length = 50), nullable = False, unique = False))
    entity_id: str = Field(sa_column=Column(String(length = 10), ForeignKey('entity.entity_id', onupdate = 'CASCADE'), primary_key = False, nullable = False))
    acct_type: IncExpType = Field(sa_column=Column(ChoiceType(IncExpType, impl = Integer()), nullable = False))
    
    __table_args__ = (
        UniqueConstraint('entity_id', 'acct_name', name='uc_entity_acctname'),
    )
    
class TransactionORM(SQLModel, table=True):
    
    __tablename__ = "transaction"

    trans_id: str = Field(sa_column=Column(String(length = 15), primary_key = True, nullable = False))
    trans_dt: datetime = Field(sa_column=Column(DateTime(), nullable = False))
    entity_id: str = Field(sa_column=Column(String(length = 10), ForeignKey('entity.entity_id', onupdate = 'CASCADE'), nullable = False))
    note: str = Field(sa_column=Column(Text(), nullable = True))
    
class EntryORM(SQLModel, table=True):
    
    __tablename__ = "entry"

    entry_id: str = Field(sa_column=Column(String(length = 20), primary_key = True, nullable = False))
    trans_id: str = Field(sa_column=Column(String(length = 15), ForeignKey('transaction.trans_id', ondelete = 'CASCADE' ,onupdate = 'CASCADE'), nullable = False))
    entry_type: EntryType = Field(sa_column=Column(ChoiceType(EntryType, impl = Integer()), nullable = False)) # debit/credit
    acct_id_balsh: str = Field(sa_column=Column(String(length = 10), ForeignKey('acct_balsh.acct_id', onupdate = 'CASCADE'), nullable = True)) # account transfer case
    acct_id_incexp: str = Field(sa_column=Column(String(length = 10), ForeignKey('acct_incexp.acct_id', onupdate = 'CASCADE'), nullable = True)) # income/expense case
    incexp_cur: CurType = Field(sa_column=Column(ChoiceType(CurType, impl = Integer()), nullable = True)) # category currency
    amount: float = Field(sa_column=Column(Float(), nullable = False, server_default = "0.0"))
    event: EventType = Field(sa_column=Column(ChoiceType(EventType, impl = Integer()), nullable = False)) # event
    project: str = Field(sa_column=Column(String(length = 10), nullable = True))  # daily/investment/other
    
class InvoiceORM(SQLModel, table=True):
    
    __tablename__ = "invoice"
    
    invoice_id: str = Field(sa_column=Column(String(length = 15), primary_key = True, nullable = False))
    invoice_dt: datetime = Field(sa_column=Column(DateTime(), nullable = False))
    entity_id_provider: str = Field(sa_column=Column(String(length = 10), ForeignKey('entity.entity_id', onupdate = 'CASCADE'), nullable = False))
    entity_id_payer: str = Field(sa_column=Column(String(length = 10), ForeignKey('entity.entity_id', onupdate = 'CASCADE'), nullable = False))
    currency: CurType = Field(sa_column=Column(ChoiceType(CurType, impl = Integer()), nullable = False)) # category currency
    items: List[dict] = Field(sa_column=Column(JSON(), nullable = False))
    discount: float = Field(sa_column=Column(Float(), default = 0))
    shipping: float = Field(sa_column=Column(Float(), default = 0))
    note: str = Field(sa_column=Column(Text(), nullable = True))
    
    
if __name__ == '__main__':
    pass

from typing import List, Dict, Tuple
from sqlmodel import Field, SQLModel, Column, create_engine
from sqlalchemy import ForeignKey, Boolean, JSON, Integer, String, Text, Date, DateTime, Float, Numeric, DECIMAL, UniqueConstraint, inspect, INT, CHAR
from sqlalchemy_utils import EmailType, PasswordType, PhoneNumberType, ChoiceType, CurrencyType, PhoneNumber
from datetime import date, datetime

from src.app.model.enums import AcctType, BankAcctType, CurType, EntryType


class FxORM(SQLModel, table=True):
    __tablename__ = "currency"
    
    currency: CurType = Field(
        sa_column=Column(
            ChoiceType(CurType, impl = Integer()), 
            primary_key = True, 
            nullable = False
        )
    )
    cur_dt: date = Field(
        sa_column=Column(Date(), primary_key = True, nullable = False)
    )
    rate: float = Field(
        sa_column=Column(Float(), nullable = False)
    )

class ChartOfAccountORM(SQLModel, table=True):
    
    __tablename__ = "chart_of_account"
    
    chart_id: str = Field(
        sa_column=Column(String(length = 13), primary_key = True, nullable = False)
    )
    node_name: str = Field(
        sa_column=Column(String(length = 50), primary_key = False, nullable = False, unique = True)
    )
    acct_type: AcctType = Field(
        sa_column=Column(ChoiceType(AcctType, impl = Integer()), nullable = False)
    )
    parent_chart_id: str | None = Field(
        sa_column=Column(
            String(length = 13),
            ForeignKey(
                'chart_of_account.chart_id', 
                onupdate = 'CASCADE', 
                ondelete = 'CASCADE'
            ),
            nullable = True
        )
    )
    
    
class AcctORM(SQLModel, table=True):
    
    __tablename__ = "accounts"
    
    acct_id: str = Field(
        sa_column=Column(String(length = 13), primary_key = True, nullable = False)
    )
    acct_name: str = Field(
        sa_column=Column(String(length = 50), nullable = False, unique = True)
    )
    acct_type: AcctType = Field(
        sa_column=Column(ChoiceType(AcctType, impl = Integer()), nullable = False)
    )
    currency: CurType | None = Field(
        sa_column=Column(ChoiceType(CurType, impl = Integer()), nullable = True)
    )
    chart_id: str = Field(
        sa_column=Column(
            String(length = 13),
            ForeignKey(
                'chart_of_account.chart_id', 
                onupdate = 'CASCADE', 
                ondelete = 'CASCADE'
            ),
            nullable = False
        )
    )
    
class BankAcctORM(SQLModel, table=True):
    
    __tablename__ = "bank_accounts"
    
    linked_acct_id: str = Field(
        sa_column=Column(
            String(length = 13), 
            ForeignKey(
                'accounts.acct_id', 
                onupdate = 'CASCADE', 
                ondelete = 'CASCADE'
            ),
            primary_key = True, 
            nullable = False
        )
    )
    bank_name: str = Field(
        sa_column=Column(String(length = 50), nullable = False, unique = False)
    )
    bank_acct_number: str = Field(
        sa_column=Column(String(length = 50), nullable = False, unique = False)
    )
    bank_acct_type: BankAcctType = Field(
        sa_column=Column(ChoiceType(BankAcctType, impl = Integer()), nullable = False)
    )
    
class JournalORM(SQLModel, table=True):
    
    __tablename__ = "journals"
    
    journal_id: str = Field(
        sa_column=Column(String(length = 17), primary_key = True, nullable = False)
    )
    jrn_date: date = Field(sa_column=Column(Date(), nullable = False))
    is_manual: EntryType = Field(
        sa_column=Column(Boolean(), nullable = False)
    )
    note: str | None = Field(sa_column=Column(Text(), nullable = True))
    
class EntryORM(SQLModel, table=True):
    __tablename__ = "entries"
    
    journal_id: str = Field(
        sa_column=Column(
            String(length = 17),
            ForeignKey(
                'journals.journal_id', 
                onupdate = 'CASCADE', 
                ondelete = 'CASCADE'
            ),
            primary_key = False, 
            nullable = False
        )
    )
    entry_type: EntryType = Field(
        sa_column=Column(ChoiceType(EntryType, impl = Integer()), nullable = False)
    )
    acct_id: str = Field(
        sa_column=Column(
            String(length = 13), 
            ForeignKey(
                'accounts.acct_id', 
                onupdate = 'CASCADE', 
                ondelete = 'CASCADE'
            ),
            primary_key = True, 
            nullable = False
        )
    )
    amount: float = Field(sa_column=Column(Float(), nullable = False, server_default = "0.0"))
    amount_base: float = Field(sa_column=Column(Float(), nullable = False, server_default = "0.0"))
    description: str | None = Field(sa_column=Column(Text(), nullable = True))
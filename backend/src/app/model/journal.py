

from datetime import date
from functools import partial
from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.app.model.accounts import Account, BankAccount
from src.app.model.enums import EntryType
from src.app.utils.tools import get_base_cur, id_generator


class Entry(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    entry_type: EntryType
    acct: Account | BankAccount
    amount: float
    amount_base: float
    description: str | None = Field(None)

    @model_validator(mode='after')
    def validate_amount_base(self):
        if self.acct.currency is None or self.acct.currency == get_base_cur():
            assert self.amount == self.amount_base
        return self
    
class Journal(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    journal_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='jrn-',
            length=13,
        ),
        frozen=True,
    )
    jrn_date: date
    entries: list[Entry] = Field(
        min_length=2
    )
    is_manual: bool = Field(True)
    note: str | None = Field(None)
    
    @model_validator(mode='after')
    def validate_balance(self):
        debits = sum(
            map(
                lambda e: e.amount_base, 
                filter(
                    lambda e: e.entry_type == EntryType.DEBIT, 
                    self.entries
                )
            )
        )
        credits = sum(
            map(
                lambda e: e.amount_base, 
                filter(
                    lambda e: e.entry_type == EntryType.CREDIT, 
                    self.entries
                )
            )
        )
        assert abs(debits - credits) <= 1e-4
        return self
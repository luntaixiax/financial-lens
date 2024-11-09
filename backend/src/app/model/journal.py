

from datetime import date
from functools import partial
from typing import Tuple
from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.app.model.accounts import Account
from src.app.model.enums import CurType, EntryType
from src.app.utils.tools import get_base_cur, id_generator


class Entry(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    entry_type: EntryType
    acct: Account
    cur_incexp: CurType | None = Field(None) # for inc/exp account, need specify currency
    amount: float
    amount_base: float
    description: str | None = Field(None)
    
    @model_validator(mode='after')
    def validate_currency(self):
        if self.acct.is_balance_sheet:
            assert self.cur_incexp is None, \
                f"Acct type is {self.acct.acct_type}, should not specify cur_incexp"
        else:
            assert self.cur_incexp is not None, \
                f"Acct type is {self.acct.acct_type}, must specify cur_incexp"
                
            # validate for inc/exp entry, if base currency is used, amount must equal
            if self.cur_incexp == get_base_cur():
                assert self.amount == self.amount_base, \
                f"Acct Currency is base currency, Amount {self.amount} not equal to base amount {self.amount_base}"
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
    
    def reduce_entries(self):
        # combine same entry and add up amounts
        # description will be combined as well
        reduced: dict[Tuple[Account, EntryType, CurType | None], Entry] = {}
        for entry in self.entries:
            pk = (entry.acct.acct_id, entry.entry_type, entry.cur_incexp)
            if pk in reduced:
                _entry = reduced[pk]
                reduced[pk] = Entry(
                    entry_type = entry.entry_type,
                    acct = entry.acct,
                    cur_incexp = entry.cur_incexp,
                    amount = _entry.amount + entry.amount,
                    amount_base = _entry.amount_base + entry.amount_base,
                    description = (_entry.description or "") + " | " + (entry.description or "")
                )
            else:
                reduced[pk] = entry
        
        self.entries =  list(reduced.values())

        
    
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
        assert abs(debits - credits) <= 1e-4, \
            f"Total debits: {debits} not equal to total credits: {credits}"
        return self
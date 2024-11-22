

from datetime import date
from functools import partial
from typing import Tuple
from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.app.model.accounts import Account
from src.app.model.enums import CurType, EntryType
from src.app.utils.tools import get_base_cur, id_generator
from src.app.utils.base import EnhancedBaseModel

class Entry(EnhancedBaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    entry_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='entr-',
            length=13,
        ),
        frozen=True,
    )
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

    
class Journal(EnhancedBaseModel):
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
    
    @property
    def is_redundant(self) -> bool:
        # whether there are entries can be reduced/combined
        # convert to list of unique key set
        reduced = map(lambda x: (x.acct.acct_id, x.entry_type, x.cur_incexp), self.entries)
        
        return len(self.entries) > len(set(reduced))
    
    def reduce_entries(self):
        # combine same entry and add up amounts
        # description will be combined as well
        reduced: dict[Tuple[Account, EntryType, CurType | None], Entry] = {}
        for entry in self.entries:
            pk = (entry.acct.acct_id, entry.entry_type, entry.cur_incexp)
            if pk in reduced:
                _entry = reduced[pk]
                reduced[pk] = Entry(
                    # entry id will be the new one
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

    @property
    def total_debits(self) -> float:
        # in base amount
        return sum(
            map(
                lambda e: e.amount_base, 
                filter(
                    lambda e: e.entry_type == EntryType.DEBIT, 
                    self.entries
                )
            )
        )
        
    @property
    def total_credits(self) -> float:
        # in base amount
        return sum(
            map(
                lambda e: e.amount_base, 
                filter(
                    lambda e: e.entry_type == EntryType.CREDIT, 
                    self.entries
                )
            )
        )
    
    @model_validator(mode='after')
    def validate_balance(self):
        debits = self.total_debits
        credits = self.total_credits
        assert abs(debits - credits) <= 1e-4, \
            f"Total debits: {debits} not equal to total credits: {credits}"
        return self
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Journal):
            return False
        
        if (
            other.journal_id == self.journal_id
            and other.jrn_date == self.jrn_date
            and other.is_manual == self.is_manual
            and other.note == self.note
        ):
            # sequence not important
            if len(self.entries) == len(other.entries):
                # sort both entries by entry id
                sort_func = lambda e: e.entry_id
                for e, o in zip(
                    sorted(self.entries, key=sort_func), 
                    sorted(other.entries, key=sort_func)
                ):
                    if not e == o:
                        return False
                
                return True
            else:
                return False
        
        else:
            return False
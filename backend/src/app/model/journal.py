

from datetime import date
from functools import partial
import math
from typing import Tuple
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field
from src.app.model.accounts import Account
from src.app.model.enums import AcctType, CurType, EntryType, JournalSrc
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

class _AcctFlowAGG(EnhancedBaseModel):
    acct_type: AcctType
    num_journal: int = 0
    num_debit_entry: int = 0
    num_credit_entry: int = 0
    debit_amount_raw: float = 0
    credit_amount_raw: float = 0
    debit_amount_base: float = 0
    credit_amount_base: float = 0
    
    @computed_field
    def num_entry(self) -> int:
        return self.num_debit_entry + self.num_credit_entry
    
    @computed_field
    def net_raw(self) -> float:
        if self.acct_type in (AcctType.AST, AcctType.EXP):
            return self.debit_amount_raw - self.credit_amount_raw
        else:
            return self.credit_amount_raw - self.debit_amount_raw
    
    @computed_field
    def net_base(self) -> float:
        if self.acct_type in (AcctType.AST, AcctType.EXP):
            return self.debit_amount_base - self.credit_amount_base
        else:
            return self.credit_amount_base - self.debit_amount_base
    

class _JournalBrief(EnhancedBaseModel):
    journal_id: str
    jrn_date: date
    jrn_src: JournalSrc
    acct_name_strs: str
    num_entries: int
    total_base_amount: float
    note: str | None
    
    @computed_field
    def acct_names(self) -> list[str]:
        return self.acct_name_strs.split(',')
    
class _EntryBrief(EnhancedBaseModel):
    # used by list by account
    entry_id: str
    journal_id: str
    jrn_date: date
    entry_type: EntryType
    cur_incexp: CurType | None = Field(None)
    amount_raw: float
    cum_acount_raw: float = Field(
        description='(Debit - Credit) Cumulative amount expressed in raw entry/account currency, only meaningful for balance sheet account'
    )
    amount_base: float
    cum_account_base: float = Field(
        description='(Debit - Credit) Cumulative amount expressed in base currency'
    )
    description: str | None = Field(None)
    
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
    jrn_src: JournalSrc = Field(
        JournalSrc.MANUAL,
        description='Journal Source, e.g., Manual/Expense/Invoice/Purchase/Payment'
    )
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
        # TODO: remove entry with 0 amount
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
        assert math.isclose(debits, credits, rel_tol=1e-6), \
            f"Total debits: {debits} not equal to total credits: {credits}"
        return self
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Journal):
            return False
        
        if (
            other.journal_id == self.journal_id
            and other.jrn_date == self.jrn_date
            and other.jrn_src == self.jrn_src
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
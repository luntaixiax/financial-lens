from datetime import datetime
from typing import List, Dict, Union, Tuple, Optional, ClassVar
from dataclasses import dataclass
from legacy.model.enums import CurType, EventType, EntryType

@dataclass(kw_only=True)
class Entry:
    entry_id: str | None = None
    entry_type: EntryType # debit/credit
    acct_id_balsh: str | None = None # can be account id from balance sheet item
    acct_id_incexp: str | None = None # can be account id from income/expense item
    incexp_cur: CurType | None = None # entry currency
    amount: float # dollar amount
    event: EventType # event type
    project: str = None # customized project type for better income/expense classification (housing, food, etc.)
    
    
@dataclass(kw_only=True)
class Transaction:
    trans_id: str | None = None
    trans_dt: datetime
    entity_id: str # on transaction must be associated to one entity
    entries: List[Entry] = None
    note: str
        
    def getEntryIdx(self, entry_id: str) -> int:
        for i, entry in enumerate(self.entries):
            if entry.entry_id == entry_id:
                return i
            
    def getEntry(self, entry_id: str) -> Entry:
        idx = self.getEntryIdx(entity_id = entry_id)
        return self.entries[idx]
    
    def addEntries(self, *entries: Entry):
        self.entries.extend(entries)
        
    def updateEntry(self, entry_id: str, entry: Entry):
        idx = self.getEntryIdx(entry_id=entry_id)
        entry.entry_id = entry_id # make sure they have same id
        self.entries[idx] = entry
        
    def deleteEntry(self, entry_id: str):
        idx = self.getEntryIdx(entry_id=entry_id)
        self.entries.pop(idx)
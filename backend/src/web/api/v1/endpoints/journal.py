from datetime import date
from typing import Any
from fastapi import APIRouter
from src.app.model.enums import JournalSrc
from src.app.model.journal import _JournalBrief, Journal
from src.app.service.journal import JournalService

router = APIRouter(prefix="/journal", tags=["journal"])

@router.post("/journal/add")
def add_journal(journal: Journal):
    JournalService.add_journal(
        journal=journal
    )
    
@router.put("/journal/update")
def update_journal(journal: Journal):
    JournalService.update_journal(
        journal=journal
    )
    
@router.delete("/journal/delete/{journal_id}")
def delete_journal(journal_id: str):
    JournalService.delete_journal(journal_id=journal_id)
    
@router.get("/journal/get/{journal_id}")
def get_journal(journal_id: str) -> Journal:
    return JournalService.get_journal(journal_id=journal_id)

@router.post("/journal/list")
def list_journal(
    limit: int = 50,
    offset: int = 0,
    jrn_ids: list[str] | None = None,
    jrn_src: JournalSrc | None = None, 
    min_dt: date = date(1970, 1, 1), 
    max_dt: date = date(2099, 12, 31), 
    acct_ids: list[str] | None = None,
    acct_names: list[str] | None = None, 
    note_keyword: str = '', 
    min_amount: float = -999999999,
    max_amount: float = 999999999,
    num_entries: int | None = None
) -> list[_JournalBrief]:
    return JournalService.list_journal(
        limit = limit,
        offset = offset,
        jrn_ids = jrn_ids,
        jrn_src = jrn_src,
        min_dt = min_dt,
        max_dt = max_dt,
        acct_ids=acct_ids,
        acct_names=acct_names,
        note_keyword = note_keyword,
        min_amount = min_amount,
        max_amount = max_amount,
        num_entries = num_entries
    )
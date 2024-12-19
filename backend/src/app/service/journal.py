
from datetime import date
from src.app.model.enums import CurType, EntryType
from src.app.model.exceptions import FKNoDeleteUpdateError, NotExistError, AlreadyExistError, FKNotExistError
from src.app.dao.journal import journalDao
from src.app.model.journal import _JournalBrief, Entry, Journal


class JournalService:
    
    @classmethod
    def create_sample(cls):
        from src.app.model.const import SystemAcctNumber
        from src.app.utils.tools import get_base_cur
        from src.app.service.acct import AcctService

        journal1 = Journal(
            journal_id='jrn-1',
            jrn_date=date(2024, 1, 1),
            entries=[
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=AcctService.get_account('acct-meal'),
                    cur_incexp=get_base_cur(),
                    amount=105.83,
                    amount_base=105.83,
                    description='Have KFC with client'
                ),
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=AcctService.get_account('acct-tip'),
                    cur_incexp=get_base_cur(),
                    amount=13.93,
                    amount_base=13.93,
                    description='Tip for KFC'
                ),
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=AcctService.get_account(SystemAcctNumber.INPUT_TAX),
                    amount=13.35,
                    amount_base=13.35,
                    description=None
                ),
                Entry(
                    entry_type=EntryType.CREDIT,
                    acct=AcctService.get_account('acct-bank'),
                    amount=133.11,
                    amount_base=133.11,
                    description=None
                ),
            ],
            is_manual=True,
            note='sample meal journal'
        )
        journal2 = Journal(
            journal_id='jrn-2',
            jrn_date=date(2024, 1, 2),
            entries=[
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=AcctService.get_account('acct-rental'),
                    cur_incexp=CurType.JPY,
                    amount=25000,
                    amount_base=250,
                    description='Stay at hotel in Japan'
                ),
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=AcctService.get_account('acct-tip'),
                    cur_incexp=CurType.USD,
                    amount=10,
                    amount_base=13.93,
                    description='Tip for the hotel, paid in USD'
                ),
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=AcctService.get_account(SystemAcctNumber.INPUT_TAX),
                    amount=45,
                    amount_base=45,
                    description='HST paid during booking'
                ),
                Entry(
                    entry_type=EntryType.CREDIT,
                    acct=AcctService.get_account('acct-fbank'),
                    amount=25000,
                    amount_base=295,
                    description=None
                ),
                Entry(
                    entry_type=EntryType.CREDIT,
                    acct=AcctService.get_account('acct-credit'),
                    amount=13.93,
                    amount_base=13.93,
                    description='pay HST with credit card'
                ),
            ],
            is_manual=True,
            note='samples rental at foreign country'
        )
        journal3 = Journal(
            journal_id='jrn-3',
            jrn_date=date(2024, 1, 2),
            entries=[
                Entry(
                    entry_type=EntryType.CREDIT,
                    acct=AcctService.get_account('acct-consul'),
                    cur_incexp=CurType.USD,
                    amount=5000,
                    amount_base=6700,
                    description='Invoice client USD5000=CAD6700'
                ),
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=AcctService.get_account(SystemAcctNumber.ACCT_RECEIV),
                    amount=6700,
                    amount_base=6700,
                    description='Record as A/R'
                ),
            ],
            is_manual=False, # this is non-manual entry journal
            note='sample invoice journal'
        )
        cls.add_journal(journal1)
        cls.add_journal(journal2)
        cls.add_journal(journal3)
        
    @classmethod
    def clear_sample(cls):
        cls.delete_journal('jrn-1')
        cls.delete_journal('jrn-2')
        cls.delete_journal('jrn-3')
        
    @classmethod
    def add_journal(cls, journal: Journal):
        # add journal and entries
        try:
            journalDao.add(journal)
        except AlreadyExistError as e:
            raise e
        except FKNotExistError as e:
            raise e
        
    @classmethod
    def get_journal(cls, journal_id: str) -> Journal:
        try:
            journal = journalDao.get(journal_id)
        except NotExistError as e:
            raise NotExistError(
                f"Journal/Entry not found: {journal_id}",
                details=e.details
            )
        return journal
    
    @classmethod
    def delete_journal(cls, journal_id: str):
        try:
            journalDao.remove(journal_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError()
        
    @classmethod
    def update_journal(cls, journal: Journal):
        cls.delete_journal(journal_id = journal.journal_id)
        cls.add_journal(journal)
        
    @classmethod
    def list_journal(
        cls,
        limit: int = 50,
        offset: int = 0,
        jrn_ids: list[str] | None = None,
        is_manual: bool | None = None, 
        min_dt: date = date(1970, 1, 1), 
        max_dt: date = date(2099, 12, 31), 
        note_keyword: str = '', 
        min_amount: float = -999999999,
        max_amount: float = 999999999,
        num_entries: int | None = None
    ) -> list[_JournalBrief]:
        return journalDao.list(
            limit = limit,
            offset = offset,
            jrn_ids = jrn_ids,
            is_manual = is_manual,
            min_dt = min_dt,
            max_dt = max_dt,
            note_keyword = note_keyword,
            min_amount = min_amount,
            max_amount = max_amount,
            num_entries = num_entries
        )
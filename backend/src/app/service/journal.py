
from datetime import date
from typing import Tuple
from src.app.model.enums import AcctType, CurType, EntryType, JournalSrc
from src.app.model.exceptions import FKNoDeleteUpdateError, NotExistError, AlreadyExistError, FKNotExistError
from src.app.dao.journal import journalDao
from src.app.model.journal import _AcctFlowAGG, _EntryBrief, _JournalBrief, Entry, Journal


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
            jrn_src=JournalSrc.MANUAL,
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
            jrn_src=JournalSrc.MANUAL,
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
            jrn_src=JournalSrc.EXPENSE, # this is non-manual entry journal
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
        except NotExistError as e:
            raise NotExistError(
                message=f'Journal {journal_id} not exist, cannot delete',
                details=e.details
            )
        
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
        jrn_src: JournalSrc | None = None, 
        min_dt: date = date(1970, 1, 1), 
        max_dt: date = date(2099, 12, 31),
        acct_ids: list[str] | None = None,
        acct_names: list[str] | None = None, 
        note_keyword: str = '', 
        min_amount: float = -999999999,
        max_amount: float = 999999999,
        num_entries: int | None = None
    ) -> Tuple[list[_JournalBrief], int]:
        return journalDao.list_journal(
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
        
    @classmethod
    def stat_journal_by_src(cls) -> list[Tuple[JournalSrc, int, float]]:
        return journalDao.stat_journal_by_src()
        
    @classmethod
    def list_entry_by_acct(cls, acct_id: str) -> list[_EntryBrief]:
        return journalDao.list_entry_by_acct(
            acct_id = acct_id
        )
        
    @classmethod
    def get_incexp_flow(cls, acct_id: str, start_dt: date, end_dt: date) -> _AcctFlowAGG:
        # get total flow amount for income statement accounts
        try:
            flow = journalDao.sum_acct_flow(
                acct_id = acct_id,
                start_dt = start_dt,
                end_dt = end_dt
            )
        except NotExistError as e:
            raise NotExistError(
                f'Account {acct_id} does not exist'
            )
        return flow
        
    @classmethod
    def get_blsh_balance(cls, acct_id: str, report_dt: date) -> _AcctFlowAGG:
        # get balance for balance sheet account at report date
        try:
            bal = journalDao.sum_acct_flow(
                acct_id = acct_id,
                start_dt = date(1900, 1, 1),
                end_dt = report_dt
            )
        except NotExistError as e:
            raise NotExistError(
                f'Account {acct_id} does not exist'
            )
        return bal
        
    @classmethod
    def get_incexp_flows(cls, start_dt: date, end_dt: date) -> dict[str, _AcctFlowAGG]:
        # get total flow amount for ALL income statement accounts
        inc = journalDao.agg_accts_flow(
            start_dt = start_dt,
            end_dt = end_dt,
            acct_type = AcctType.INC
        )
        exp = journalDao.agg_accts_flow(
            start_dt = start_dt,
            end_dt = end_dt,
            acct_type = AcctType.EXP
        )
        return inc | exp
        
        
    @classmethod
    def get_blsh_balances(cls, report_dt: date) -> dict[str, _AcctFlowAGG]:
        # get balance for ALL balance sheet account at report date
        ast = journalDao.agg_accts_flow(
            start_dt = date(1900, 1, 1),
            end_dt = report_dt,
            acct_type = AcctType.AST
        )
        liab = journalDao.agg_accts_flow(
            start_dt = date(1900, 1, 1),
            end_dt = report_dt,
            acct_type = AcctType.LIB
        )
        equity = journalDao.agg_accts_flow(
            start_dt = date(1900, 1, 1),
            end_dt = report_dt,
            acct_type = AcctType.EQU
        )
        return ast | liab | equity
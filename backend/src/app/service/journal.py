
from datetime import date
from typing import Tuple
from src.app.utils.tools import get_base_cur
from src.app.model.const import SystemAcctNumber
from src.app.model.enums import AcctType, CurType, EntryType, JournalSrc
from src.app.model.exceptions import FKNoDeleteUpdateError, NotExistError, AlreadyExistError, FKNotExistError
from src.app.dao.journal import journalDao
from src.app.model.journal import _AcctFlowAGG, _EntryBrief, _JournalBrief, Entry, Journal
from src.app.service.acct import AcctService

class JournalService:
    
    def __init__(self, journal_dao: journalDao, acct_service: AcctService):
        self.journal_dao = journal_dao
        self.acct_service = acct_service
    
    def create_sample(self):
        journal1 = Journal(
            journal_id='jrn-1',
            jrn_date=date(2024, 1, 1),
            entries=[
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=self.acct_service.get_account('acct-meal'),
                    cur_incexp=get_base_cur(),
                    amount=105.83,
                    amount_base=105.83,
                    description='Have KFC with client'
                ),
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=self.acct_service.get_account('acct-tip'),
                    cur_incexp=get_base_cur(),
                    amount=13.93,
                    amount_base=13.93,
                    description='Tip for KFC'
                ),
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=self.acct_service.get_account(SystemAcctNumber.INPUT_TAX),
                    cur_incexp=None,
                    amount=13.35,
                    amount_base=13.35,
                    description=None
                ),
                Entry(
                    entry_type=EntryType.CREDIT,
                    acct=self.acct_service.get_account('acct-bank'),
                    cur_incexp=None,
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
                    acct=self.acct_service.get_account('acct-rental'),
                    cur_incexp=CurType.JPY,
                    amount=25000,
                    amount_base=250,
                    description='Stay at hotel in Japan'
                ),
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=self.acct_service.get_account('acct-tip'),
                    cur_incexp=CurType.USD,
                    amount=10,
                    amount_base=13.93,
                    description='Tip for the hotel, paid in USD'
                ),
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=self.acct_service.get_account(SystemAcctNumber.INPUT_TAX),
                    cur_incexp=None,
                    amount=45,
                    amount_base=45,
                    description='HST paid during booking'
                ),
                Entry(
                    entry_type=EntryType.CREDIT,
                    acct=self.acct_service.get_account('acct-fbank'),
                    cur_incexp=None,
                    amount=25000,
                    amount_base=295,
                    description=None
                ),
                Entry(
                    entry_type=EntryType.CREDIT,
                    acct=self.acct_service.get_account('acct-credit'),
                    cur_incexp=None,
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
                    acct=self.acct_service.get_account('acct-consul'),
                    cur_incexp=CurType.USD,
                    amount=5000,
                    amount_base=6700,
                    description='Invoice client USD5000=CAD6700'
                ),
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=self.acct_service.get_account(SystemAcctNumber.ACCT_RECEIV),
                    cur_incexp=None,
                    amount=6700,
                    amount_base=6700,
                    description='Record as A/R'
                ),
            ],
            jrn_src=JournalSrc.EXPENSE, # this is non-manual entry journal
            note='sample invoice journal'
        )
        self.add_journal(journal1)
        self.add_journal(journal2)
        self.add_journal(journal3)
        
    def clear_sample(self):
        self.delete_journal('jrn-1')
        self.delete_journal('jrn-2')
        self.delete_journal('jrn-3')
        
    def add_journal(self, journal: Journal):
        # add journal and entries
        try:
            self.journal_dao.add(journal)
        except AlreadyExistError as e:
            raise e
        except FKNotExistError as e:
            raise e
        
    def get_journal(self, journal_id: str) -> Journal:
        try:
            journal = self.journal_dao.get(journal_id)
        except NotExistError as e:
            raise NotExistError(
                f"Journal/Entry not found: {journal_id}",
                details=e.details
            )
        return journal
    
    def delete_journal(self, journal_id: str):
        try:
            self.journal_dao.remove(journal_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError()
        except NotExistError as e:
            raise NotExistError(
                message=f'Journal {journal_id} not exist, cannot delete',
                details=e.details
            )
        
    def update_journal(self, journal: Journal):
        self.delete_journal(journal_id = journal.journal_id)
        self.add_journal(journal)
        
    def list_journal(
        self,
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
        return self.journal_dao.list_journal(
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
        
    def stat_journal_by_src(self) -> list[Tuple[JournalSrc, int, float]]:
        return self.journal_dao.stat_journal_by_src()
        
    def list_entry_by_acct(self, acct_id: str) -> list[_EntryBrief]:
        return self.journal_dao.list_entry_by_acct(
            acct_id = acct_id
        )
        
    def get_incexp_flow(self, acct_id: str, start_dt: date, end_dt: date) -> _AcctFlowAGG:
        # get total flow amount for income statement accounts
        try:
            flow = self.journal_dao.sum_acct_flow(
                acct_id = acct_id,
                start_dt = start_dt,
                end_dt = end_dt
            )
        except NotExistError as e:
            raise NotExistError(
                f'Account {acct_id} does not exist'
            )
        return flow
        
    def get_blsh_balance(self, acct_id: str, report_dt: date) -> _AcctFlowAGG:
        # get balance for balance sheet account at report date
        try:
            bal = self.journal_dao.sum_acct_flow(
                acct_id = acct_id,
                start_dt = date(1900, 1, 1),
                end_dt = report_dt
            )
        except NotExistError as e:
            raise NotExistError(
                f'Account {acct_id} does not exist'
            )
        return bal
        
    def get_incexp_flows(self, start_dt: date, end_dt: date) -> dict[str, _AcctFlowAGG]:
        # get total flow amount for ALL income statement accounts
        inc = self.journal_dao.agg_accts_flow(
            start_dt = start_dt,
            end_dt = end_dt,
            acct_type = AcctType.INC
        )
        exp = self.journal_dao.agg_accts_flow(
            start_dt = start_dt,
            end_dt = end_dt,
            acct_type = AcctType.EXP
        )
        return inc | exp
        
        
    def get_blsh_balances(self, report_dt: date) -> dict[str, _AcctFlowAGG]:
        # get balance for ALL balance sheet account at report date
        ast = self.journal_dao.agg_accts_flow(
            start_dt = date(1900, 1, 1),
            end_dt = report_dt,
            acct_type = AcctType.AST
        )
        liab = self.journal_dao.agg_accts_flow(
            start_dt = date(1900, 1, 1),
            end_dt = report_dt,
            acct_type = AcctType.LIB
        )
        equity = self.journal_dao.agg_accts_flow(
            start_dt = date(1900, 1, 1),
            end_dt = report_dt,
            acct_type = AcctType.EQU
        )
        return ast | liab | equity
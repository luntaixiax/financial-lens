

from datetime import date
import math
from typing import Tuple

from src.app.service.journal import JournalService
from src.app.dao.shares import dividendDao, stockIssueDao, stockRepurchaseDao
from src.app.service.fx import FxService
from src.app.model.const import SystemAcctNumber
from src.app.model.journal import Entry, Journal
from src.app.model.enums import AcctType, EntryType, JournalSrc
from src.app.utils.tools import finround, get_base_cur, get_par_share_price
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, FKNotExistError, NotExistError, NotMatchWithSystemError, OpNotPermittedError
from src.app.service.acct import AcctService
from src.app.model.accounts import Account
from src.app.model.shares import Dividend, StockIssue, StockRepurchase


class SharesService:
    
    def __init__(
            self, 
            stock_issue_dao: stockIssueDao, 
            stock_repurchase_dao: stockRepurchaseDao, 
            dividend_dao: dividendDao,
            acct_service: AcctService, 
            journal_service: JournalService,
            fx_service: FxService,
        ):
        self.stock_issue_dao = stock_issue_dao
        self.stock_repurchase_dao = stock_repurchase_dao
        self.dividend_dao = dividend_dao
        self.acct_service = acct_service
        self.journal_service = journal_service
        self.fx_service = fx_service

    def create_sample(self):
        issue = StockIssue(
            issue_id='sample-issue',
            issue_dt=date(2024, 1, 3),
            is_reissue = False,
            num_shares=100,
            issue_price=5.4,
            reissue_repur_id=None,
            debit_acct_id='acct-fbank',
            issue_amt=60000,
            note='Issue of 100 shares priced at 5.4'
        )
        repur = StockRepurchase(
            repur_id='sample-repur',
            repur_dt=date(2024, 1, 10),
            num_shares=20,
            repur_price=12.5,
            credit_acct_id='acct-bank',
            repur_amt=250,
            note='Repurchase of 20 shares priced at 12.5'
        )
        div = Dividend(
            div_id='sample-div',
            div_dt=date(2024, 1, 5),
            credit_acct_id='acct-bank',
            div_amt=1000,
            note='Pay dividend of $1000'
        )
        self.add_issue(issue)
        self.add_repur(repur)
        self.add_div(div)
        
    def clear_sample(self):
        self.delete_issue(issue_id='sample-issue')
        self.delete_repur(repur_id='sample-repur')
        self.delete_div(div_id='sample-div')
        
    def _validate_issue(self, issue: StockIssue) -> StockIssue:
        # TODO: if reissue, need to check if num_shares <= total repurchased shares
        if issue.is_reissue:
            # check if reissue id exist
            try:
                repur, jrn = self.get_repur_journal(issue.reissue_repur_id) # type: ignore
            except NotExistError as e:
                raise NotExistError(
                    message=f'Repurchase id {issue.reissue_repur_id} not found for reissue',
                    details=e.details
                )
            else:
                # verify if reissue is after repurchase
                if issue.issue_dt < repur.repur_dt:
                    raise OpNotPermittedError(
                        message="Cannot reissue stock before that batch of stock being repurchased",
                        details=f"issue date: {issue.issue_dt} while repurchased at {repur.repur_dt}"
                    )
                
                # verify if issue # of stock is less than remaining repurchased shares
                total_reissued_excl_self = self.stock_issue_dao.get_total_reissue_from_repur(
                    repur_id=issue.reissue_repur_id, # type: ignore
                    rep_dt=issue.issue_dt, # reissue on and before this date
                    exclu_issue_id=issue.issue_id  # exclude itself to avoid recursive counting
                ) # already reissued before given date
                # remaining treasury stock available for that batch of repurchase
                remaining_for_reissue = repur.num_shares - total_reissued_excl_self
                
                if issue.num_shares > remaining_for_reissue:
                    raise OpNotPermittedError(
                        message=f"You can only reissue remaining repurchased stock for batch {issue.reissue_repur_id}",
                        details=f"total repurchased={repur.num_shares}, already issued={total_reissued_excl_self}, " \
                        f"remaining={remaining_for_reissue} while you ask for {issue.num_shares}"
                    )
        
        # check if debit_acct_id exists
        try:
            debit_acct: Account = self.acct_service.get_account(
                issue.debit_acct_id
            )
        except NotExistError as e:
            raise FKNotExistError(
                f"Debit Account Id {issue.debit_acct_id} does not exist",
                details=e.details
            )
            
        if not debit_acct.acct_type in (AcctType.AST, AcctType.LIB, AcctType.EXP):
            raise NotMatchWithSystemError(
                message=f"Debit acct type of share issue must be of Balance sheet type or expense, get {debit_acct.acct_type}"
            )
            
        # if the debit account is base currency, it should match the issue amount
        if debit_acct.currency == get_base_cur():
            if not math.isclose(issue.issue_amt, issue.issue_amt_base): # type: ignore
                raise OpNotPermittedError(
                    message=f'Issue amount should equal to issue price x num_shares, if receiving base currency',
                    details=f'({debit_acct.currency}), Issue: {issue}'
                )
                
        return issue
    
    def _validate_repur(self, repur: StockRepurchase) -> StockRepurchase:
        # check if credit_acct_id exists
        try:
            credit_acct: Account = self.acct_service.get_account(
                repur.credit_acct_id
            )
        except NotExistError as e:
            raise FKNotExistError(
                f"Credit Account Id {repur.credit_acct_id} does not exist",
                details=e.details
            )
            
        if not credit_acct.acct_type in (AcctType.AST, AcctType.LIB):
            raise NotMatchWithSystemError(
                message=f"Credit acct type of share repurchase must be of Balance sheet type, get {credit_acct.acct_type}"
            )
            
        # if the credit account is base currency, it should match the repurchase amount
        if credit_acct.currency == get_base_cur():
            if not math.isclose(repur.repur_amt, repur.repur_amt_base): # type: ignore
                raise OpNotPermittedError(
                    message=f'Repurchase amount should equal to repur price x num_shares, if paying base currency',
                    details=f'({credit_acct.currency}), Repurchase: {repur}'
                )
        
        return repur
    
    def _validate_div(self, div: Dividend) -> Dividend:
        # check if credit_acct_id exists
        try:
            credit_acct: Account = self.acct_service.get_account(
                div.credit_acct_id
            )
        except NotExistError as e:
            raise FKNotExistError(
                f"Credit Account Id {div.credit_acct_id} does not exist",
                details=e.details
            )
            
        if not credit_acct.acct_type in (AcctType.AST, AcctType.LIB):
            raise NotMatchWithSystemError(
                message=f"Credit acct type of dividend must be of Balance sheet type, get {credit_acct.acct_type}"
            )
            
        return div
    
    def create_journal_from_issue(self, issue: StockIssue) -> Journal:
        self._validate_issue(issue)
        
        entries = []
        debit_acct: Account = self.acct_service.get_account(
            issue.debit_acct_id
        )
        # credit common stock / treasury stock
        if issue.is_reissue:
            repur, _ = self.get_repur_journal(issue.reissue_repur_id) # type: ignore
            cost_price = repur.repur_price # using cost method, cost is repurchase price
            credit_acct = self.acct_service.get_account(SystemAcctNumber.TREASURY_STOCK)
            description=f"Reissue Treasy stock at cost={cost_price}"
        else:
            cost_price = get_par_share_price()
            credit_acct = self.acct_service.get_account(SystemAcctNumber.CONTR_CAP)
            description=f"Common stock at par value={cost_price}"
            
        issue_cost_base = finround(cost_price * issue.num_shares)
        common_entry = Entry(
            entry_type=EntryType.CREDIT, # common stock is credit entry
            acct=credit_acct,
            cur_incexp=None, # balance sheet item should not have currency
            amount=issue_cost_base, # amount in raw currency
            # amount in base currency
            amount_base=issue_cost_base,
            description=description,
        )
        # credit additional paid in capital
        issue_premium_base = issue.issue_amt_base - issue_cost_base # type: ignore
        add_entry = Entry(
            entry_type=EntryType.CREDIT, # additional paid in stock is credit entry
            acct=self.acct_service.get_account(SystemAcctNumber.ADD_PAID_IN),
            cur_incexp=None, # balance sheet item should not have currency
            amount=issue_premium_base, # amount in raw currency
            # amount in base currency
            amount_base=issue_premium_base,
            description=f"Additional paid in premium"
        )
        entries.append(common_entry)
        entries.append(add_entry)
        
        # debit receiving account
        # use base currency to record if using expense to debit
        cur_incexp = get_base_cur() if debit_acct.acct_type == AcctType.EXP else None
        if debit_acct.currency != get_base_cur():
            amount_base=self.fx_service.convert_to_base(
                amount=issue.issue_amt,
                src_currency=debit_acct.currency, # receive currency # type: ignore
                cur_dt=issue.issue_dt, # convert fx at issue date
            )
            
            debit_entry = Entry(
                entry_type=EntryType.DEBIT, # receiving fund is debit entry
                acct=debit_acct,
                cur_incexp=cur_incexp,
                amount=issue.issue_amt,
                # amount in base currency
                amount_base=amount_base,
                description=f"Receiving fund"
            )
            
            # if using different currency, additional received is fx gain
            gain = amount_base - issue.issue_amt_base # type: ignore
            fx_gain = Entry(
                entry_type=EntryType.CREDIT, # fx gain is credit
                acct=self.acct_service.get_account(SystemAcctNumber.FX_GAIN), # goes to gain account
                cur_incexp=get_base_cur(),
                amount=gain, # gain is already expressed in base currency
                amount_base=gain, # gain is already expressed in base currency
                description='fx gain' if gain >=0 else 'fx loss'
            )
            entries.append(fx_gain)
            
        else:
            debit_entry = Entry(
                entry_type=EntryType.DEBIT, # receiving fund is debit entry
                acct=debit_acct,
                cur_incexp=cur_incexp,
                amount=issue.issue_amt,
                # amount in base currency
                amount_base=issue.issue_amt,
                description=f"Receiving fund"
            )
            
        entries.append(debit_entry)
        
        # create journal
        journal = Journal(
            jrn_date=issue.issue_dt,
            entries=entries,
            jrn_src=JournalSrc.SHARE,
            note=f"Issuing new stocks @{get_base_cur()}{issue.issue_price} for {issue.num_shares} shares" \
            if issue.is_reissue == False \
            else f"Reissue repurchased stocks @{get_base_cur()}{issue.issue_price} for {issue.num_shares} shares"
        )
        journal.reduce_entries()
        return journal
    
    def create_journal_from_repur(self, repur: StockRepurchase) -> Journal:
        self._validate_repur(repur)
        
        entries = []
        credit_acct: Account = self.acct_service.get_account(
            repur.credit_acct_id
        )
        
        # debit the treasury stock account
        treasury_entry = Entry(
            entry_type=EntryType.DEBIT, # repurchase is debit entry to treasury stock
            acct=self.acct_service.get_account(SystemAcctNumber.TREASURY_STOCK),
            cur_incexp=None, # balance sheet item should not have currency
            amount=repur.repur_amt_base, # type: ignore # amount in raw currency
            # amount in base currency
            amount_base=repur.repur_amt_base, # type: ignore
            description=f"Treasury stock at price={repur.repur_price}"
        )
        entries.append(treasury_entry)
        
        # credit the account paying the repurchase
        if credit_acct.currency != get_base_cur():
            amount_base=self.fx_service.convert_to_base(
                amount=repur.repur_amt,
                src_currency=credit_acct.currency, # receive currency # type: ignore
                cur_dt=repur.repur_dt, # convert fx at repurchase date
            )
            credit_entry = Entry(
                entry_type=EntryType.CREDIT, # paying fund is credit entry
                acct=credit_acct,
                cur_incexp=None, # balance sheet item should not have currency
                amount=repur.repur_amt,
                # amount in base currency
                amount_base=amount_base,
                description=f"Paying fund"
            )
            
            # if using different currency, less paid is fx gain
            gain = repur.repur_amt_base - amount_base # type: ignore
            fx_gain = Entry(
                entry_type=EntryType.CREDIT, # fx gain is credit
                acct=self.acct_service.get_account(SystemAcctNumber.FX_GAIN), # goes to gain account
                cur_incexp=get_base_cur(),
                amount=gain, # gain is already expressed in base currency
                amount_base=gain, # gain is already expressed in base currency
                description='fx gain' if gain >=0 else 'fx loss'
            )
            entries.append(fx_gain)
            
        else:
            credit_entry = Entry(
                entry_type=EntryType.CREDIT, # paying fund is credit entry
                acct=credit_acct,
                cur_incexp=None, # balance sheet item should not have currency
                amount=repur.repur_amt,
                # amount in base currency
                amount_base=repur.repur_amt,
                description=f"Paying fund"
            )
            
        entries.append(credit_entry)
        
        # create journal
        journal = Journal(
            jrn_date=repur.repur_dt,
            entries=entries,
            jrn_src=JournalSrc.SHARE,
            note=f"Repurchasing stock @{get_base_cur()}{repur.repur_price} for {repur.num_shares} shares"
        )
        journal.reduce_entries()
        return journal
    
    def create_journal_from_div(self, div: Dividend) -> Journal:
        self._validate_div(div)
        
        entries = []
        credit_acct: Account = self.acct_service.get_account(
            div.credit_acct_id
        )
        
        # debit the accum. dividend account
        amount_base=self.fx_service.convert_to_base(
            amount=div.div_amt,
            src_currency=credit_acct.currency, # paying currency # type: ignore
            cur_dt=div.div_dt, # convert fx at dividend date
        )
        div_entry = Entry(
            entry_type=EntryType.DEBIT, # dividend is debit entry
            acct=self.acct_service.get_account(SystemAcctNumber.TREASURY_STOCK),
            cur_incexp=None, # balance sheet item should not have currency
            amount=amount_base, # amount in base currency
            # amount in base currency
            amount_base=amount_base,
            description=f"announced dividend"
        )
        entries.append(div_entry)
        
        # credit the paying account
        credit_entry = Entry(
            entry_type=EntryType.CREDIT, # paying fund is credit entry
            acct=credit_acct,
            cur_incexp=None, # balance sheet item should not have currency
            amount=div.div_amt,
            # amount in base currency
            amount_base=amount_base,
            description=f"paying dividend"
        )
        entries.append(credit_entry)
        
        # create journal
        journal = Journal(
            jrn_date=div.div_dt,
            entries=entries,
            jrn_src=JournalSrc.SHARE,
            note=f"Paying dividend"
        )
        journal.reduce_entries()
        return journal
    
    def add_issue(self, issue: StockIssue):
        # see if issue already exist
        try:
            _issue, _jrn_id  = self.stock_issue_dao.get(issue.issue_id)
        except NotExistError as e:
            # if not exist, can safely create it
            # validate it first
            self._validate_issue(issue)
            
            # add journal first
            journal = self.create_journal_from_issue(issue)
            try:
                self.journal_service.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of journal does not exist: {journal}',
                    details=e.details
                )
                
            # add issue
            try:
                self.stock_issue_dao.add(journal_id = journal.journal_id, stock_issue = issue)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of issue does not exist: {issue}',
                    details=e.details
                )
            except AlreadyExistError as e:
                raise AlreadyExistError(
                    f'StockIssue already exist, change one please',
                    details=f"{issue}"
                )
            
        else:
            raise AlreadyExistError(
                f"StockIssue id {issue.issue_id} already exist",
                details=f"StockIssue: {_issue}, journal_id: {_jrn_id}"
            )
            
    def add_repur(self, repur: StockRepurchase):
        # see if repur already exist
        try:
            _repur, _jrn_id  = self.stock_repurchase_dao.get(repur.repur_id)
        except NotExistError as e:
            # if not exist, can safely create it
            # validate it first
            self._validate_repur(repur)
            
            # add journal first
            journal = self.create_journal_from_repur(repur)
            try:
                self.journal_service.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of journal does not exist: {journal}',
                    details=e.details
                )
                
            # add repur
            try:
                self.stock_repurchase_dao.add(journal_id = journal.journal_id, stock_repur = repur)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of repur does not exist: {repur}',
                    details=e.details
                )
            except AlreadyExistError as e:
                raise AlreadyExistError(
                    f'StockRepurchase already exist, change one please',
                    details=f"{repur}"
                )
            
        else:
            raise AlreadyExistError(
                f"StockRepurchase id {repur.repur_id} already exist",
                details=f"StockRepurchase: {_repur}, journal_id: {_jrn_id}"
            )
            
    def add_div(self, div: Dividend):
        # see if div already exist
        try:
            _div, _jrn_id  = self.dividend_dao.get(div.div_id)
        except NotExistError as e:
            # if not exist, can safely create it
            # validate it first
            self._validate_div(div)
            
            # add journal first
            journal = self.create_journal_from_div(div)
            try:
                self.journal_service.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of journal does not exist: {journal}',
                    details=e.details
                )
                
            # add div
            try:
                self.dividend_dao.add(journal_id = journal.journal_id, dividend = div)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of div does not exist: {div}',
                    details=e.details
                )
            except AlreadyExistError as e:
                raise AlreadyExistError(
                    f'Dividend already exist, change one please',
                    details=f"{div}"
                )
            
        else:
            raise AlreadyExistError(
                f"Dividend id {div.div_id} already exist",
                details=f"Dividend: {_div}, journal_id: {_jrn_id}"
            )
            
    def get_issue_journal(self, issue_id: str) -> Tuple[StockIssue, Journal]:
        try:
            stock_issue, jrn_id = self.stock_issue_dao.get(issue_id)
        except NotExistError as e:
            raise NotExistError(
                f'StockIssue id {issue_id} does not exist',
                details=e.details
            )
        
        # get journal
        try:
            journal = self.journal_service.get_journal(jrn_id)
        except NotExistError as e:
            # TODO: raise error or add missing journal?
            # if not exist, add journal
            journal = self.create_journal_from_issue(stock_issue)
            try:
                self.journal_service.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Trying to add journal but failed, some component of journal does not exist: {journal}',
                    details=e.details
                )
        
        return stock_issue, journal
    
    def get_repur_journal(self, repur_id: str) -> Tuple[StockRepurchase, Journal]:
        try:
            stock_repur, jrn_id = self.stock_repurchase_dao.get(repur_id)
        except NotExistError as e:
            raise NotExistError(
                f'StockRepurchase id {repur_id} does not exist',
                details=e.details
            )
        
        # get journal
        try:
            journal = self.journal_service.get_journal(jrn_id)
        except NotExistError as e:
            # TODO: raise error or add missing journal?
            # if not exist, add journal
            journal = self.create_journal_from_repur(stock_repur)
            try:
                self.journal_service.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Trying to add journal but failed, some component of journal does not exist: {journal}',
                    details=e.details
                )
        
        return stock_repur, journal
    
    def get_div_journal(self, div_id: str) -> Tuple[Dividend, Journal]:
        try:
            dividend, jrn_id = self.dividend_dao.get(div_id)
        except NotExistError as e:
            raise NotExistError(
                f'Dividend id {div_id} does not exist',
                details=e.details
            )
        
        # get journal
        try:
            journal = self.journal_service.get_journal(jrn_id)
        except NotExistError as e:
            # TODO: raise error or add missing journal?
            # if not exist, add journal
            journal = self.create_journal_from_div(dividend)
            try:
                self.journal_service.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Trying to add journal but failed, some component of journal does not exist: {journal}',
                    details=e.details
                )
        
        return dividend, journal
    
    def delete_issue(self, issue_id: str):
        # remove journal first
        # get journal
        try:
            issue, jrn_id  = self.stock_issue_dao.get(issue_id)
        except NotExistError as e:
            raise NotExistError(
                f'Issue id {issue_id} does not exist',
                details=e.details
            )
            
        # remove issue first
        try:
            self.stock_issue_dao.remove(issue_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Issue {issue_id} have dependency cannot be deleted",
                details=e.details
            )
        
        # then remove journal
        try:
            self.journal_service.delete_journal(jrn_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Delete journal failed, some component depends on the journal id {jrn_id}",
                details=e.details
            )
            
    def delete_repur(self, repur_id: str):
        # remove journal first
        # get journal
        try:
            repur, jrn_id  = self.stock_repurchase_dao.get(repur_id)
        except NotExistError as e:
            raise NotExistError(
                f'Repurchase id {repur_id} does not exist',
                details=e.details
            )
            
        # remove repur first
        try:
            self.stock_repurchase_dao.remove(repur_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Repurchase {repur_id} have dependency cannot be deleted",
                details=e.details
            )
        
        # then remove journal
        try:
            self.journal_service.delete_journal(jrn_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Delete journal failed, some component depends on the journal id {jrn_id}",
                details=e.details
            )
            
    def delete_div(self, div_id: str):
        # remove journal first
        # get journal
        try:
            div, jrn_id  = self.dividend_dao.get(div_id)
        except NotExistError as e:
            raise NotExistError(
                f'Dividend id {div_id} does not exist',
                details=e.details
            )
            
        # remove div first
        try:
            self.dividend_dao.remove(div_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Dividend {div_id} have dependency cannot be deleted",
                details=e.details
            )
        
        # then remove journal
        try:
            self.journal_service.delete_journal(jrn_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Delete journal failed, some component depends on the journal id {jrn_id}",
                details=e.details
            )
            
    def update_issue(self, issue: StockIssue):
        self._validate_issue(issue)
        # only delete if validation passed
        
        # get existing journal id
        try:
            _issue, jrn_id  = self.stock_issue_dao.get(issue.issue_id)
        except NotExistError as e:
            raise NotExistError(
                f'StockIssue id {issue.issue_id} does not exist',
                details=e.details
            )
        
        # add new journal first
        journal = self.create_journal_from_issue(issue)
        try:
            self.journal_service.add_journal(journal)
        except FKNotExistError as e:
            raise FKNotExistError(
                f'Some component of journal does not exist: {journal}',
                details=e.details
            )
        
        # update issue
        try:
            self.stock_issue_dao.update(
                journal_id=journal.journal_id, # use new journal id
                stock_issue=issue
            )
        except FKNotExistError as e:
            # need to remove the new journal
            self.journal_service.delete_journal(journal.journal_id)
            raise FKNotExistError(
                f"StockIssue element does not exist",
                details=e.details
            )
        
        # remove old journal
        self.journal_service.delete_journal(jrn_id)
        
    def update_repur(self, repur: StockRepurchase):
        self._validate_repur(repur)
        # only delete if validation passed
        
        # get existing journal id
        try:
            _repur, jrn_id  = self.stock_repurchase_dao.get(repur.repur_id)
        except NotExistError as e:
            raise NotExistError(
                f'StockRepurchase id {repur.repur_id} does not exist',
                details=e.details
            )
        
        # add new journal first
        journal = self.create_journal_from_repur(repur)
        try:
            self.journal_service.add_journal(journal)
        except FKNotExistError as e:
            raise FKNotExistError(
                f'Some component of journal does not exist: {journal}',
                details=e.details
            )
        
        # update repur
        try:
            self.stock_repurchase_dao.update(
                journal_id=journal.journal_id, # use new journal id
                stock_repur=repur
            )
        except FKNotExistError as e:
            # need to remove the new journal
            self.journal_service.delete_journal(journal.journal_id)
            raise FKNotExistError(
                f"StockRepurchase element does not exist",
                details=e.details
            )
        
        # remove old journal
        self.journal_service.delete_journal(jrn_id)
        
    def update_div(self, div: Dividend):
        self._validate_div(div)
        # only delete if validation passed
        
        # get existing journal id
        try:
            _div, jrn_id  = self.dividend_dao.get(div.div_id)
        except NotExistError as e:
            raise NotExistError(
                f'Dividend id {div.div_id} does not exist',
                details=e.details
            )
        
        # add new journal first
        journal = self.create_journal_from_div(div)
        try:
            self.journal_service.add_journal(journal)
        except FKNotExistError as e:
            raise FKNotExistError(
                f'Some component of journal does not exist: {journal}',
                details=e.details
            )
        
        # update div
        try:
            self.dividend_dao.update(
                journal_id=journal.journal_id, # use new journal id
                dividend=div
            )
        except FKNotExistError as e:
            # need to remove the new journal
            self.journal_service.delete_journal(journal.journal_id)
            raise FKNotExistError(
                f"Dividend element does not exist",
                details=e.details
            )
        
        # remove old journal
        self.journal_service.delete_journal(jrn_id)
    
        
    def list_issues(self, is_reissue: bool = False) -> list[StockIssue]:
        return self.stock_issue_dao.list_issues(is_reissue=is_reissue)
    
    def list_reissue_from_repur(self, repur_id: str) -> list[StockIssue]:
        return self.stock_issue_dao.list_reissue_from_repur(repur_id)
    
    def get_total_reissue_from_repur(self, repur_id: str, rep_dt: date, exclu_issue_id: str | None = None) -> float:
        return self.stock_issue_dao.get_total_reissue_from_repur(
            repur_id=repur_id,
            rep_dt=rep_dt,
            exclu_issue_id=exclu_issue_id
        )
    
    def list_repurs(self) -> list[StockRepurchase]:
        return self.stock_repurchase_dao.list_repurs()
    
    def list_divs(self) -> list[Dividend]:
        return self.dividend_dao.list_divs()


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
    
    @classmethod
    def create_sample(cls):
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
        cls.add_issue(issue)
        cls.add_repur(repur)
        cls.add_div(div)
        
    @classmethod
    def clear_sample(cls):
        cls.delete_issue(issue_id='sample-issue')
        cls.delete_repur(repur_id='sample-repur')
        cls.delete_div(div_id='sample-div')
        
    @classmethod
    def _validate_issue(cls, issue: StockIssue) -> StockIssue:
        # TODO: if reissue, need to check if num_shares <= total repurchased shares
        if issue.is_reissue:
            # check if reissue id exist
            try:
                repur, jrn = cls.get_repur_journal(issue.reissue_repur_id)
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
                total_reissued_excl_self = stockIssueDao.get_total_reissue_from_repur(
                    repur_id=issue.reissue_repur_id,
                    rep_dt=issue.issue_dt, # reissue on and before this date
                    exclu_issue_id=issue.issue_id  # exclude itself to avoid recursive counting
                ) # already reissued before given date
                # remaining treasury stock available for that batch of repurchase
                remaining_for_reissue = repur.num_shares - total_reissued_excl_self
                
                if issue.num_shares > remaining_for_reissue:
                    raise OpNotPermittedError(
                        message=f"You can only reissue remaining repurchased stock for batch {issue.reissue_repur_id}",
                        details=f"total repurchased={repur.num_shares}, already issued={total_reissued_excl_self}, remaining={remaining_for_reissue} while you ask for {issue.num_shares}"
                    )
        
        # check if debit_acct_id exists
        try:
            debit_acct: Account = AcctService.get_account(
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
            if not math.isclose(issue.issue_amt, issue.issue_amt_base):
                raise OpNotPermittedError(
                    message=f'Issue amount should equal to issue price x num_shares, if receiving base currency',
                    details=f'({debit_acct.currency}), Issue: {issue}'
                )
                
        return issue
    
    @classmethod
    def _validate_repur(cls, repur: StockRepurchase) -> StockRepurchase:
        # check if credit_acct_id exists
        try:
            credit_acct: Account = AcctService.get_account(
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
            if not math.isclose(repur.repur_amt, repur.repur_amt_base):
                raise OpNotPermittedError(
                    message=f'Repurchase amount should equal to repur price x num_shares, if paying base currency',
                    details=f'({credit_acct.currency}), Repurchase: {repur}'
                )
        
        return repur
    
    @classmethod
    def _validate_div(cls, div: Dividend) -> Dividend:
        # check if credit_acct_id exists
        try:
            credit_acct: Account = AcctService.get_account(
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
    
    @classmethod
    def create_journal_from_issue(cls, issue: StockIssue) -> Journal:
        cls._validate_issue(issue)
        
        entries = []
        debit_acct: Account = AcctService.get_account(
            issue.debit_acct_id
        )
        # credit common stock / treasury stock
        if issue.is_reissue:
            repur, _ = cls.get_repur_journal(issue.reissue_repur_id)
            cost_price = repur.repur_price # using cost method, cost is repurchase price
            credit_acct = AcctService.get_account(SystemAcctNumber.TREASURY_STOCK)
            description=f"Reissue Treasy stock at cost={cost_price}"
        else:
            cost_price = get_par_share_price()
            credit_acct = AcctService.get_account(SystemAcctNumber.CONTR_CAP)
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
        issue_premium_base = issue.issue_amt_base - issue_cost_base
        add_entry = Entry(
            entry_type=EntryType.CREDIT, # additional paid in stock is credit entry
            acct=AcctService.get_account(SystemAcctNumber.ADD_PAID_IN),
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
            amount_base=FxService.convert_to_base(
                amount=issue.issue_amt,
                src_currency=debit_acct.currency, # receive currency
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
            gain = amount_base - issue.issue_amt_base
            fx_gain = Entry(
                entry_type=EntryType.CREDIT, # fx gain is credit
                acct=AcctService.get_account(SystemAcctNumber.FX_GAIN), # goes to gain account
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
    
    @classmethod
    def create_journal_from_repur(cls, repur: StockRepurchase) -> Journal:
        cls._validate_repur(repur)
        
        entries = []
        credit_acct: Account = AcctService.get_account(
            repur.credit_acct_id
        )
        
        # debit the treasury stock account
        treasury_entry = Entry(
            entry_type=EntryType.DEBIT, # repurchase is debit entry to treasury stock
            acct=AcctService.get_account(SystemAcctNumber.TREASURY_STOCK),
            cur_incexp=None, # balance sheet item should not have currency
            amount=repur.repur_amt_base, # amount in raw currency
            # amount in base currency
            amount_base=repur.repur_amt_base,
            description=f"Treasury stock at price={repur.repur_price}"
        )
        entries.append(treasury_entry)
        
        # credit the account paying the repurchase
        if credit_acct.currency != get_base_cur():
            amount_base=FxService.convert_to_base(
                amount=repur.repur_amt,
                src_currency=credit_acct.currency, # receive currency
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
            gain = repur.repur_amt_base - amount_base
            fx_gain = Entry(
                entry_type=EntryType.CREDIT, # fx gain is credit
                acct=AcctService.get_account(SystemAcctNumber.FX_GAIN), # goes to gain account
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
    
    @classmethod
    def create_journal_from_div(cls, div: Dividend) -> Journal:
        cls._validate_div(div)
        
        entries = []
        credit_acct: Account = AcctService.get_account(
            div.credit_acct_id
        )
        
        # debit the accum. dividend account
        amount_base=FxService.convert_to_base(
            amount=div.div_amt,
            src_currency=credit_acct.currency, # paying currency
            cur_dt=div.div_dt, # convert fx at dividend date
        )
        div_entry = Entry(
            entry_type=EntryType.DEBIT, # dividend is debit entry
            acct=AcctService.get_account(SystemAcctNumber.TREASURY_STOCK),
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
    
    @classmethod
    def add_issue(cls, issue: StockIssue):
        # see if issue already exist
        try:
            _issue, _jrn_id  = stockIssueDao.get(issue.issue_id)
        except NotExistError as e:
            # if not exist, can safely create it
            # validate it first
            cls._validate_issue(issue)
            
            # add journal first
            journal = cls.create_journal_from_issue(issue)
            try:
                JournalService.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of journal does not exist: {journal}',
                    details=e.details
                )
                
            # add issue
            try:
                stockIssueDao.add(journal_id = journal.journal_id, stock_issue = issue)
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
            
    @classmethod
    def add_repur(cls, repur: StockRepurchase):
        # see if repur already exist
        try:
            _repur, _jrn_id  = stockRepurchaseDao.get(repur.repur_id)
        except NotExistError as e:
            # if not exist, can safely create it
            # validate it first
            cls._validate_repur(repur)
            
            # add journal first
            journal = cls.create_journal_from_repur(repur)
            try:
                JournalService.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of journal does not exist: {journal}',
                    details=e.details
                )
                
            # add repur
            try:
                stockRepurchaseDao.add(journal_id = journal.journal_id, stock_repur = repur)
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
            
    @classmethod
    def add_div(cls, div: Dividend):
        # see if div already exist
        try:
            _div, _jrn_id  = dividendDao.get(div.div_id)
        except NotExistError as e:
            # if not exist, can safely create it
            # validate it first
            cls._validate_div(div)
            
            # add journal first
            journal = cls.create_journal_from_div(div)
            try:
                JournalService.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Some component of journal does not exist: {journal}',
                    details=e.details
                )
                
            # add div
            try:
                dividendDao.add(journal_id = journal.journal_id, dividend = div)
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
            
    @classmethod
    def get_issue_journal(cls, issue_id: str) -> Tuple[StockIssue, Journal]:
        try:
            stock_issue, jrn_id = stockIssueDao.get(issue_id)
        except NotExistError as e:
            raise NotExistError(
                f'StockIssue id {issue_id} does not exist',
                details=e.details
            )
        
        # get journal
        try:
            journal = JournalService.get_journal(jrn_id)
        except NotExistError as e:
            # TODO: raise error or add missing journal?
            # if not exist, add journal
            journal = cls.create_journal_from_issue(stock_issue)
            try:
                JournalService.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Trying to add journal but failed, some component of journal does not exist: {journal}',
                    details=e.details
                )
        
        return stock_issue, journal
    
    @classmethod
    def get_repur_journal(cls, repur_id: str) -> Tuple[StockRepurchase, Journal]:
        try:
            stock_repur, jrn_id = stockRepurchaseDao.get(repur_id)
        except NotExistError as e:
            raise NotExistError(
                f'StockRepurchase id {repur_id} does not exist',
                details=e.details
            )
        
        # get journal
        try:
            journal = JournalService.get_journal(jrn_id)
        except NotExistError as e:
            # TODO: raise error or add missing journal?
            # if not exist, add journal
            journal = cls.create_journal_from_repur(stock_repur)
            try:
                JournalService.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Trying to add journal but failed, some component of journal does not exist: {journal}',
                    details=e.details
                )
        
        return stock_repur, journal
    
    @classmethod
    def get_div_journal(cls, div_id: str) -> Tuple[Dividend, Journal]:
        try:
            dividend, jrn_id = dividendDao.get(div_id)
        except NotExistError as e:
            raise NotExistError(
                f'Dividend id {div_id} does not exist',
                details=e.details
            )
        
        # get journal
        try:
            journal = JournalService.get_journal(jrn_id)
        except NotExistError as e:
            # TODO: raise error or add missing journal?
            # if not exist, add journal
            journal = cls.create_journal_from_div(dividend)
            try:
                JournalService.add_journal(journal)
            except FKNotExistError as e:
                raise FKNotExistError(
                    f'Trying to add journal but failed, some component of journal does not exist: {journal}',
                    details=e.details
                )
        
        return dividend, journal
    
    @classmethod
    def delete_issue(cls, issue_id: str):
        # remove journal first
        # get journal
        try:
            issue, jrn_id  = stockIssueDao.get(issue_id)
        except NotExistError as e:
            raise NotExistError(
                f'Issue id {issue_id} does not exist',
                details=e.details
            )
            
        # remove issue first
        try:
            stockIssueDao.remove(issue_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Issue {issue_id} have dependency cannot be deleted",
                details=e.details
            )
        
        # then remove journal
        try:
            JournalService.delete_journal(jrn_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Delete journal failed, some component depends on the journal id {jrn_id}",
                details=e.details
            )
            
    @classmethod
    def delete_repur(cls, repur_id: str):
        # remove journal first
        # get journal
        try:
            repur, jrn_id  = stockRepurchaseDao.get(repur_id)
        except NotExistError as e:
            raise NotExistError(
                f'Repurchase id {repur_id} does not exist',
                details=e.details
            )
            
        # remove repur first
        try:
            stockRepurchaseDao.remove(repur_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Repurchase {repur_id} have dependency cannot be deleted",
                details=e.details
            )
        
        # then remove journal
        try:
            JournalService.delete_journal(jrn_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Delete journal failed, some component depends on the journal id {jrn_id}",
                details=e.details
            )
            
    @classmethod
    def delete_div(cls, div_id: str):
        # remove journal first
        # get journal
        try:
            div, jrn_id  = dividendDao.get(div_id)
        except NotExistError as e:
            raise NotExistError(
                f'Dividend id {div_id} does not exist',
                details=e.details
            )
            
        # remove div first
        try:
            dividendDao.remove(div_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Dividend {div_id} have dependency cannot be deleted",
                details=e.details
            )
        
        # then remove journal
        try:
            JournalService.delete_journal(jrn_id)
        except FKNoDeleteUpdateError as e:
            raise FKNoDeleteUpdateError(
                f"Delete journal failed, some component depends on the journal id {jrn_id}",
                details=e.details
            )
            
    @classmethod
    def update_issue(cls, issue: StockIssue):
        cls._validate_issue(issue)
        # only delete if validation passed
        
        # get existing journal id
        try:
            _issue, jrn_id  = stockIssueDao.get(issue.issue_id)
        except NotExistError as e:
            raise NotExistError(
                f'StockIssue id {_issue.issue_id} does not exist',
                details=e.details
            )
        
        # add new journal first
        journal = cls.create_journal_from_issue(issue)
        try:
            JournalService.add_journal(journal)
        except FKNotExistError as e:
            raise FKNotExistError(
                f'Some component of journal does not exist: {journal}',
                details=e.details
            )
        
        # update issue
        try:
            stockIssueDao.update(
                journal_id=journal.journal_id, # use new journal id
                stock_issue=issue
            )
        except FKNotExistError as e:
            # need to remove the new journal
            JournalService.delete_journal(journal.journal_id)
            raise FKNotExistError(
                f"StockIssue element does not exist",
                details=e.details
            )
        
        # remove old journal
        JournalService.delete_journal(jrn_id)
        
    @classmethod
    def update_repur(cls, repur: StockRepurchase):
        cls._validate_repur(repur)
        # only delete if validation passed
        
        # get existing journal id
        try:
            _repur, jrn_id  = stockRepurchaseDao.get(repur.repur_id)
        except NotExistError as e:
            raise NotExistError(
                f'StockRepurchase id {_repur.repur_id} does not exist',
                details=e.details
            )
        
        # add new journal first
        journal = cls.create_journal_from_repur(repur)
        try:
            JournalService.add_journal(journal)
        except FKNotExistError as e:
            raise FKNotExistError(
                f'Some component of journal does not exist: {journal}',
                details=e.details
            )
        
        # update repur
        try:
            stockRepurchaseDao.update(
                journal_id=journal.journal_id, # use new journal id
                stock_repur=repur
            )
        except FKNotExistError as e:
            # need to remove the new journal
            JournalService.delete_journal(journal.journal_id)
            raise FKNotExistError(
                f"StockRepurchase element does not exist",
                details=e.details
            )
        
        # remove old journal
        JournalService.delete_journal(jrn_id)
        
    @classmethod
    def update_div(cls, div: Dividend):
        cls._validate_div(div)
        # only delete if validation passed
        
        # get existing journal id
        try:
            _div, jrn_id  = dividendDao.get(div.div_id)
        except NotExistError as e:
            raise NotExistError(
                f'Dividend id {_div.div_id} does not exist',
                details=e.details
            )
        
        # add new journal first
        journal = cls.create_journal_from_div(div)
        try:
            JournalService.add_journal(journal)
        except FKNotExistError as e:
            raise FKNotExistError(
                f'Some component of journal does not exist: {journal}',
                details=e.details
            )
        
        # update div
        try:
            dividendDao.update(
                journal_id=journal.journal_id, # use new journal id
                dividend=div
            )
        except FKNotExistError as e:
            # need to remove the new journal
            JournalService.delete_journal(journal.journal_id)
            raise FKNotExistError(
                f"Dividend element does not exist",
                details=e.details
            )
        
        # remove old journal
        JournalService.delete_journal(jrn_id)
    
        
    @classmethod
    def list_issues(cls, is_reissue: bool = False) -> list[StockIssue]:
        return stockIssueDao.list_issues(is_reissue=is_reissue)
    
    @classmethod
    def list_reissue_from_repur(cls, repur_id: str) -> list[StockIssue]:
        return stockIssueDao.list_reissue_from_repur(repur_id)
    
    @classmethod
    def get_total_reissue_from_repur(cls, repur_id: str, rep_dt: date, exclu_issue_id: str | None = None) -> float:
        return stockIssueDao.get_total_reissue_from_repur(
            repur_id=repur_id,
            rep_dt=rep_dt,
            exclu_issue_id=exclu_issue_id
        )
    
    @classmethod
    def list_repurs(cls) -> list[StockRepurchase]:
        return stockRepurchaseDao.list_repurs()
    
    @classmethod
    def list_divs(cls) -> list[Dividend]:
        return dividendDao.list_divs()
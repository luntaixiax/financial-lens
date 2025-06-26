

from datetime import date
import math

from src.app.service.fx import FxService
from src.app.model.const import SystemAcctNumber
from src.app.model.journal import Entry, Journal
from src.app.model.enums import AcctType, EntryType, JournalSrc
from src.app.utils.tools import get_base_cur
from src.app.model.exceptions import FKNotExistError, NotExistError, NotMatchWithSystemError, OpNotPermittedError
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
            cost_price=0.01,
            debit_acct_id='acct-fbank',
            issue_amt=60000
        )
        repur = StockRepurchase(
            repur_id='sample-repur',
            repurchase_dt=date(2024, 1, 10),
            num_shares=20,
            repur_price=12.5,
            credit_acct_id='acct-bank',
            repur_amt=250
        )
        div = Dividend(
            div_id='sample-div',
            div_dt=date(2024, 1, 5),
            credit_acct_id='acct-bank',
            div_amt=1000
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
            pass
        
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
        # credit common stock
        cost_descrp = 'par price' if issue.is_reissue == False else 'repurchase priec'
        common_entry = Entry(
            entry_type=EntryType.CREDIT, # common stock is credit entry
            acct=AcctService.get_account(SystemAcctNumber.CONTR_CAP),
            cur_incexp=None, # balance sheet item should not have currency
            amount=issue.issue_cost_base, # amount in raw currency
            # amount in base currency
            amount_base=issue.issue_cost_base,
            description=f"Common stock at {cost_descrp}={issue.cost_price}"
        )
        # credit additional paid in capital
        add_entry = Entry(
            entry_type=EntryType.CREDIT, # additional paid in stock is credit entry
            acct=AcctService.get_account(SystemAcctNumber.ADD_PAID_IN),
            cur_incexp=None, # balance sheet item should not have currency
            amount=issue.issue_premium_base, # amount in raw currency
            # amount in base currency
            amount_base=issue.issue_premium_base,
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
            note="Issuing new stocks" if issue.is_reissue == False else "Reissue repurchased stocks"
        )
        journal.reduce_entries()
        return journal
    
        
        
            
        
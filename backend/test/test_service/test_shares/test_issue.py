from _typeshed import NoneType
from datetime import date
from unittest import mock
from pydantic import ValidationError
import pytest
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, NotMatchWithSystemError, OpNotPermittedError
from src.app.model.enums import JournalSrc
from src.app.model.shares import StockIssue
from src.app.model.const import SystemAcctNumber

def test_create_journal_from_issue(session_with_sample_choa, sample_issue, test_shares_service, test_fx_service, test_acct_service):
    
    journal = test_shares_service.create_journal_from_issue(sample_issue)
    assert journal.jrn_src == JournalSrc.SHARE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    
    # common stock account should be credit
    acct_ids = [e.acct.acct_id for e in journal.entries]
    assert SystemAcctNumber.CONTR_CAP in acct_ids   
    assert SystemAcctNumber.TREASURY_STOCK not in acct_ids
    
    # total amount from issue should be same to total amount from journal (base currency)
    debit_acct = test_acct_service.get_account(
        sample_issue.debit_acct_id
    )
    amount_base = test_fx_service.convert_to_base(
        amount=sample_issue.issue_amt,
        src_currency=debit_acct.currency, # purchase currency
        cur_dt=sample_issue.issue_dt, # convert fx at issue date
    )
    assert amount_base == journal.total_credits

def test_create_journal_from_reissue(session_with_sample_choa, sample_reissue, sample_repur, test_shares_service, test_fx_service, test_acct_service):
    
    # add a repurchase first
    test_shares_service.add_repur(sample_repur)
    
    journal = test_shares_service.create_journal_from_issue(sample_reissue)
    assert journal.jrn_src == JournalSrc.SHARE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    
    # treasury stock account should be credit
    acct_ids = [e.acct.acct_id for e in journal.entries]
    assert SystemAcctNumber.CONTR_CAP not in acct_ids
    assert SystemAcctNumber.TREASURY_STOCK in acct_ids
    
    # total amount from issue should be same to total amount from journal (base currency)
    debit_acct = test_acct_service.get_account(
        sample_reissue.debit_acct_id
    )
    amount_base = test_fx_service.convert_to_base(
        amount=sample_reissue.issue_amt,
        src_currency=debit_acct.currency, # purchase currency
        cur_dt=sample_reissue.issue_dt, # convert fx at issue date
    )
    assert amount_base == journal.total_credits
    
    # test reissue case
    assert journal.jrn_src == JournalSrc.SHARE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    
    test_shares_service.delete_repur(sample_repur.repur_id)
    
def test_validate_issue(session_with_sample_choa, test_shares_service):
    
    issue = StockIssue(
        issue_id='sample-issue',
        issue_dt=date(2024, 1, 3),
        is_reissue = False,
        num_shares=100,
        issue_price=5.4,
        reissue_repur_id=None,
        debit_acct_id='acct-fbank',
        issue_amt=60000,
        note=None
    )
    # successful validation
    test_shares_service._validate_issue(issue)
    
    # validate credit account id
    issue.debit_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        # account not exist
        test_shares_service._validate_issue(issue)
    issue.debit_acct_id = 'acct-fbank'
    # validate purchase account type
    issue.debit_acct_id = 'acct-consul'
    with pytest.raises(NotMatchWithSystemError):
        test_shares_service._validate_issue(issue)
        
    # test same currency
    issue = StockIssue(
        issue_id='sample-issue',
        issue_dt=date(2024, 1, 3),
        is_reissue = False,
        num_shares=100,
        issue_price=5.4,
        reissue_repur_id=None,
        debit_acct_id='acct-bank',
        issue_amt=600,
        note=None
    )
    with pytest.raises(OpNotPermittedError):
        test_shares_service._validate_issue(issue)
        
def test_validate_reissue(session_with_sample_choa, sample_reissue, sample_repur, test_shares_service):
    
    with pytest.raises(ValidationError):
        reissue = StockIssue(
            issue_id='sample-reissue',
            issue_dt=date(2024, 1, 3),
            is_reissue = True,
            num_shares=100,
            issue_price=5.4,
            reissue_repur_id=None,
            debit_acct_id='acct-fbank',
            issue_amt=60000,
            note=None
        )
        
    # add a repurchase first
    test_shares_service.add_repur(sample_repur)

    # successful validation
    test_shares_service._validate_issue(sample_reissue)
    
    # not exist repur error
    sample_reissue.reissue_repur_id = 'random-repur'
    with pytest.raises(NotExistError):
        test_shares_service._validate_issue(sample_reissue)
    sample_reissue.reissue_repur_id = sample_repur.repur_id
    
    # reissue more than repurchased
    # case 1. before 1st repurchase
    sample_reissue.issue_dt = date(2023, 1, 8)
    with pytest.raises(OpNotPermittedError):
        test_shares_service._validate_issue(sample_reissue)
    sample_reissue.issue_dt = date(2024, 1, 15) 
    
    # case 2. reissue more
    sample_reissue.num_shares = 25
    with pytest.raises(OpNotPermittedError):
        test_shares_service._validate_issue(sample_reissue)
    
    test_shares_service.delete_repur(sample_repur.repur_id)
    

def test_issue(session_with_sample_choa, sample_issue, test_shares_service, test_journal_service):
    
    # test add issue
    test_shares_service.add_issue(sample_issue)
    with pytest.raises(AlreadyExistError):
        test_shares_service.add_issue(sample_issue)
    
    # assert journal is correctly added
    _issue, _journal = test_shares_service.get_issue_journal(sample_issue.issue_id)
    assert _issue == sample_issue
    
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    # validate should still work after added
    test_shares_service._validate_issue(_issue)
    
    with pytest.raises(NotExistError):
        test_shares_service.get_issue_journal('random-issue')
        
    # test update issue
    _issue, _journal = test_shares_service.get_issue_journal(sample_issue.issue_id)
    _jrn_id = _journal.journal_id # original journal id before updating
    # update 1 --  valid issue update
    sample_issue.issue_price = 6
    sample_issue.issue_dt = date(2024, 1, 10)
    test_shares_service.update_issue(sample_issue)
    _issue, _journal = test_shares_service.get_issue_journal(sample_issue.issue_id)
    assert _issue == sample_issue
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    with pytest.raises(NotExistError):
        # original journal should be deleted
        test_journal_service.get_journal(_jrn_id)
    
    # test delete issue
    with pytest.raises(NotExistError):
        test_shares_service.delete_issue('random-issue')
    test_shares_service.delete_issue(sample_issue.issue_id)
    with pytest.raises(NotExistError):
        test_shares_service.get_issue_journal(sample_issue.issue_id)
from datetime import date
from unittest import mock
import pytest
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, NotMatchWithSystemError, OpNotPermittedError
from src.app.model.enums import JournalSrc
from src.app.model.shares import StockIssue

@mock.patch("src.app.dao.connection.get_engine")
def test_create_journal_from_issue(mock_engine, engine_with_sample_choa, sample_issue):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.shares import SharesService
    from src.app.service.fx import FxService
    from src.app.service.acct import AcctService
    
    journal = SharesService.create_journal_from_issue(sample_issue)
    assert journal.jrn_src == JournalSrc.SHARE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    
    # total amount from issue should be same to total amount from journal (base currency)
    debit_acct = AcctService.get_account(
        sample_issue.debit_acct_id
    )
    amount_base = FxService.convert_to_base(
        amount=sample_issue.issue_amt,
        src_currency=debit_acct.currency, # purchase currency
        cur_dt=sample_issue.issue_dt, # convert fx at issue date
    )
    assert amount_base == journal.total_credits
    
@mock.patch("src.app.dao.connection.get_engine")
def test_validate_issue(mock_engine, engine_with_sample_choa):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.shares import SharesService
    
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
    # successful validation
    SharesService._validate_issue(issue)
    
    # validate credit account id
    issue.debit_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        # account not exist
        SharesService._validate_issue(issue)
    issue.debit_acct_id = 'acct-fbank'
    # validate purchase account type
    issue.debit_acct_id = 'acct-consul'
    with pytest.raises(NotMatchWithSystemError):
        SharesService._validate_issue(issue)
        
    # test same currency
    issue = StockIssue(
        issue_id='sample-issue',
        issue_dt=date(2024, 1, 3),
        is_reissue = False,
        num_shares=100,
        issue_price=5.4,
        cost_price=0.01,
        debit_acct_id='acct-bank',
        issue_amt=600
    )
    with pytest.raises(OpNotPermittedError):
        SharesService._validate_issue(issue)

@mock.patch("src.app.dao.connection.get_engine")
def test_issue(mock_engine, engine_with_sample_choa, sample_issue):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.shares import SharesService
    from src.app.service.journal import JournalService
    
    # test add issue
    SharesService.add_issue(sample_issue)
    with pytest.raises(AlreadyExistError):
        SharesService.add_issue(sample_issue)
    
    # assert journal is correctly added
    _issue, _journal = SharesService.get_issue_journal(sample_issue.issue_id)
    assert _issue == sample_issue
    
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    with pytest.raises(NotExistError):
        SharesService.get_issue_journal('random-issue')
        
    # test update issue
    _issue, _journal = SharesService.get_issue_journal(sample_issue.issue_id)
    _jrn_id = _journal.journal_id # original journal id before updating
    # update 1 --  valid issue update
    sample_issue.issue_price = 6
    sample_issue.issue_dt = date(2024, 1, 10)
    SharesService.update_issue(sample_issue)
    _issue, _journal = SharesService.get_issue_journal(sample_issue.issue_id)
    assert _issue == sample_issue
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    with pytest.raises(NotExistError):
        # original journal should be deleted
        JournalService.get_journal(_jrn_id)
    
    # test delete issue
    with pytest.raises(NotExistError):
        SharesService.delete_issue('random-issue')
    SharesService.delete_issue(sample_issue.issue_id)
    with pytest.raises(NotExistError):
        SharesService.get_issue_journal(sample_issue.issue_id)
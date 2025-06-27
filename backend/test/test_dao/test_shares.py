from datetime import date
from typing import Generator
from unittest import mock
import pytest

from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError
from src.app.model.shares import StockIssue, StockRepurchase, Dividend

@pytest.fixture
def sample_issue() -> StockIssue:
    issue = StockIssue(
        issue_id='test-issue',
        issue_dt=date(2024, 1, 3),
        is_reissue = False,
        num_shares=100,
        issue_price=5.4,
        reissue_repur_id=None,
        debit_acct_id='acct-fbank',
        issue_amt=60000
    )
    return issue

@pytest.fixture
def sample_repur() -> StockRepurchase:
    repur = StockRepurchase(
        repur_id='test-repur',
        repurchase_dt=date(2024, 1, 3),
        num_shares=20,
        repur_price=12.5,
        credit_acct_id='acct-bank',
        repur_amt=250
    )
    return repur

@pytest.fixture
def sample_div() -> Dividend:
    div = Dividend(
        div_id='test-div',
        div_dt=date(2024, 1, 3),
        credit_acct_id='acct-bank',
        div_amt=1000
    )
    return div

@mock.patch("src.app.dao.connection.get_engine")
def test_issue(mock_engine, engine_with_sample_choa, sample_issue, sample_journal_meal):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.dao.shares import stockIssueDao
    from src.app.dao.journal import journalDao
    
    # assert issue not found, and have correct error type
    with pytest.raises(NotExistError):
        stockIssueDao.get(sample_issue.issue_id)

    # add without journal will fail
    with pytest.raises(FKNotExistError):
        stockIssueDao.add(journal_id = 'test-jrn', stock_issue = sample_issue)
        
    # add sample journal (does not matter which journal to link to, as long as there is one)
    journalDao.add(sample_journal_meal) # add journal
    
    # then can add issue
    stockIssueDao.add(journal_id = sample_journal_meal.journal_id, stock_issue = sample_issue)
    
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        stockIssueDao.add(journal_id = sample_journal_meal.journal_id, stock_issue = sample_issue)
    
    # test get issue
    _issue, _jrn_id = stockIssueDao.get(sample_issue.issue_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _issue == sample_issue
    
    # test update issue
    sample_issue.issue_dt = date(2024, 5, 1)
    sample_issue.issue_price = 6.5
    stockIssueDao.update(sample_journal_meal.journal_id, sample_issue)
    _issue, _jrn_id = stockIssueDao.get(sample_issue.issue_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _issue == sample_issue
    
    # delete issue
    stockIssueDao.remove(sample_issue.issue_id)
    with pytest.raises(NotExistError):
        stockIssueDao.get(sample_issue.issue_id)
        
    # delete journal
    journalDao.remove(sample_journal_meal.journal_id)
    
    
@mock.patch("src.app.dao.connection.get_engine")
def test_repurchase(mock_engine, engine_with_sample_choa, sample_repur, sample_journal_meal):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.dao.shares import stockRepurchaseDao
    from src.app.dao.journal import journalDao
    
    # assert issue not found, and have correct error type
    with pytest.raises(NotExistError):
        stockRepurchaseDao.get(sample_repur.repur_id)

    # add without journal will fail
    with pytest.raises(FKNotExistError):
        stockRepurchaseDao.add(journal_id = 'test-jrn', stock_repur = sample_repur)
        
    # add sample journal (does not matter which journal to link to, as long as there is one)
    journalDao.add(sample_journal_meal) # add journal
    
    # then can add issue
    stockRepurchaseDao.add(journal_id = sample_journal_meal.journal_id, stock_repur = sample_repur)
    
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        stockRepurchaseDao.add(journal_id = sample_journal_meal.journal_id, stock_repur = sample_repur)
    
    # test get issue
    _repur, _jrn_id = stockRepurchaseDao.get(sample_repur.repur_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _repur == sample_repur
    
    # test update issue
    sample_repur.repurchase_dt = date(2024, 5, 1)
    sample_repur.repur_price = 6.5
    stockRepurchaseDao.update(sample_journal_meal.journal_id, sample_repur)
    _repur, _jrn_id = stockRepurchaseDao.get(sample_repur.repur_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _repur == sample_repur
    
    # delete issue
    stockRepurchaseDao.remove(sample_repur.repur_id)
    with pytest.raises(NotExistError):
        stockRepurchaseDao.get(sample_repur.repur_id)
        
    # delete journal
    journalDao.remove(sample_journal_meal.journal_id)
    
    
@mock.patch("src.app.dao.connection.get_engine")
def test_div(mock_engine, engine_with_sample_choa, sample_div, sample_journal_meal):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.dao.shares import dividendDao
    from src.app.dao.journal import journalDao
    
    # assert issue not found, and have correct error type
    with pytest.raises(NotExistError):
        dividendDao.get(sample_div.div_id)

    # add without journal will fail
    with pytest.raises(FKNotExistError):
        dividendDao.add(journal_id = 'test-jrn', dividend = sample_div)
        
    # add sample journal (does not matter which journal to link to, as long as there is one)
    journalDao.add(sample_journal_meal) # add journal
    
    # then can add issue
    dividendDao.add(journal_id = sample_journal_meal.journal_id, dividend = sample_div)
    
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        dividendDao.add(journal_id = sample_journal_meal.journal_id, dividend = sample_div)
    
    # test get issue
    _div, _jrn_id = dividendDao.get(sample_div.div_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _div == sample_div
    
    # test update issue
    sample_div.div_dt = date(2024, 5, 1)
    sample_div.div_amt = 800
    dividendDao.update(sample_journal_meal.journal_id, sample_div)
    _div, _jrn_id = dividendDao.get(sample_div.div_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _div == sample_div
    
    # delete issue
    dividendDao.remove(sample_div.div_id)
    with pytest.raises(NotExistError):
        dividendDao.get(sample_div.div_id)
        
    # delete journal
    journalDao.remove(sample_journal_meal.journal_id)
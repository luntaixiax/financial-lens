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
        issue_amt=60000,
        note='Issue of 100 shares priced at 5.4'
    )
    return issue

@pytest.fixture
def sample_repur() -> StockRepurchase:
    repur = StockRepurchase(
        repur_id='test-repur',
        repur_dt=date(2024, 1, 3),
        num_shares=20,
        repur_price=12.5,
        credit_acct_id='acct-bank',
        repur_amt=250,
        note='Repurchase of 20 shares priced at 12.5'
    )
    return repur

@pytest.fixture
def sample_div() -> Dividend:
    div = Dividend(
        div_id='test-div',
        div_dt=date(2024, 1, 3),
        credit_acct_id='acct-bank',
        div_amt=1000,
        note='Pay dividend of $1000'
    )
    return div

def test_issue(session_with_sample_choa, test_stock_issue_dao, test_journal_dao, 
               sample_issue, sample_journal_meal):
    
    # assert issue not found, and have correct error type
    with pytest.raises(NotExistError):
        test_stock_issue_dao.get(sample_issue.issue_id)

    # add without journal will fail
    with pytest.raises(FKNotExistError):
        test_stock_issue_dao.add(journal_id = 'test-jrn', stock_issue = sample_issue)
        
    # add sample journal (does not matter which journal to link to, as long as there is one)
    test_journal_dao.add(sample_journal_meal) # add journal
    
    # then can add issue
    test_stock_issue_dao.add(journal_id = sample_journal_meal.journal_id, stock_issue = sample_issue)
    
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        test_stock_issue_dao.add(journal_id = sample_journal_meal.journal_id, stock_issue = sample_issue)
    
    # test get issue
    _issue, _jrn_id = test_stock_issue_dao.get(sample_issue.issue_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _issue == sample_issue
    
    # test update issue
    sample_issue.issue_dt = date(2024, 5, 1)
    sample_issue.issue_price = 6.5
    test_stock_issue_dao.update(sample_journal_meal.journal_id, sample_issue)
    _issue, _jrn_id = test_stock_issue_dao.get(sample_issue.issue_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _issue == sample_issue
    
    # delete issue
    test_stock_issue_dao.remove(sample_issue.issue_id)
    with pytest.raises(NotExistError):
        test_stock_issue_dao.get(sample_issue.issue_id)
        
    # delete journal
    test_journal_dao.remove(sample_journal_meal.journal_id)
    
    
def test_repurchase(session_with_sample_choa, test_stock_repurchase_dao, test_journal_dao, 
                    sample_repur, sample_journal_meal):
    
    # assert issue not found, and have correct error type
    with pytest.raises(NotExistError):
        test_stock_repurchase_dao.get(sample_repur.repur_id)

    # add without journal will fail
    with pytest.raises(FKNotExistError):
        test_stock_repurchase_dao.add(journal_id = 'test-jrn', stock_repur = sample_repur)
        
    # add sample journal (does not matter which journal to link to, as long as there is one)
    test_journal_dao.add(sample_journal_meal) # add journal
    
    # then can add issue
    test_stock_repurchase_dao.add(journal_id = sample_journal_meal.journal_id, stock_repur = sample_repur)
    
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        test_stock_repurchase_dao.add(journal_id = sample_journal_meal.journal_id, stock_repur = sample_repur)
    
    # test get issue
    _repur, _jrn_id = test_stock_repurchase_dao.get(sample_repur.repur_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _repur == sample_repur
    
    # test update issue
    sample_repur.repur_dt = date(2024, 5, 1)
    sample_repur.repur_price = 6.5
    test_stock_repurchase_dao.update(sample_journal_meal.journal_id, sample_repur)
    _repur, _jrn_id = test_stock_repurchase_dao.get(sample_repur.repur_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _repur == sample_repur
    
    # delete issue
    test_stock_repurchase_dao.remove(sample_repur.repur_id)
    with pytest.raises(NotExistError):
        test_stock_repurchase_dao.get(sample_repur.repur_id)
        
    # delete journal
    test_journal_dao.remove(sample_journal_meal.journal_id)
    
    
def test_div(session_with_sample_choa, test_stock_dividend_dao, test_journal_dao, 
             sample_div, sample_journal_meal):
    
    # assert issue not found, and have correct error type
    with pytest.raises(NotExistError):
        test_stock_dividend_dao.get(sample_div.div_id)

    # add without journal will fail
    with pytest.raises(FKNotExistError):
        test_stock_dividend_dao.add(journal_id = 'test-jrn', dividend = sample_div)
        
    # add sample journal (does not matter which journal to link to, as long as there is one)
    test_journal_dao.add(sample_journal_meal) # add journal
    
    # then can add issue
    test_stock_dividend_dao.add(journal_id = sample_journal_meal.journal_id, dividend = sample_div)
    
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        test_stock_dividend_dao.add(journal_id = sample_journal_meal.journal_id, dividend = sample_div)
    
    # test get issue
    _div, _jrn_id = test_stock_dividend_dao.get(sample_div.div_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _div == sample_div
    
    # test update issue
    sample_div.div_dt = date(2024, 5, 1)
    sample_div.div_amt = 800
    test_stock_dividend_dao.update(sample_journal_meal.journal_id, sample_div)
    _div, _jrn_id = test_stock_dividend_dao.get(sample_div.div_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _div == sample_div
    
    # delete issue
    test_stock_dividend_dao.remove(sample_div.div_id)
    with pytest.raises(NotExistError):
        test_stock_dividend_dao.get(sample_div.div_id)
        
    # delete journal
    test_journal_dao.remove(sample_journal_meal.journal_id)
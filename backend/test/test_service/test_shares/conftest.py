from datetime import date
import pytest
from src.app.model.shares import StockIssue, StockRepurchase, Dividend

@pytest.fixture
def sample_issue() -> StockIssue:
    issue = StockIssue(
        issue_id='sample-issue',
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
def sample_reissue(sample_repur) -> StockIssue:
    reissue = StockIssue(
        issue_id='sample-reissue',
        issue_dt=date(2024, 1, 15),
        is_reissue = True,
        num_shares=10,
        issue_price=5.4,
        reissue_repur_id=sample_repur.repur_id,
        debit_acct_id='acct-fbank',
        issue_amt=60000
    )
    return reissue

@pytest.fixture
def sample_repur() -> StockRepurchase:
    repur = StockRepurchase(
        repur_id='sample-repur',
        repurchase_dt=date(2024, 1, 10),
        num_shares=20,
        repur_price=12.5,
        credit_acct_id='acct-bank',
        repur_amt=250
    )
    return repur
    
@pytest.fixture
def sample_div() -> Dividend:
    div = Dividend(
        div_id='sample-div',
        div_dt=date(2024, 1, 5),
        credit_acct_id='acct-bank',
        div_amt=1000
    )
    return div
import pytest
from unittest import mock
from anytree import PreOrderIter
from src.app.model.exceptions import NotExistError, FKNotExistError
from src.app.model.enums import AcctType
from src.app.model.accounts import Chart, ChartNode

@pytest.fixture
def engine_with_acct(engine, asset_node: ChartNode):
    with mock.patch("src.app.dao.connection.get_engine") as mock_engine:
        mock_engine.return_value = engine
        
        from src.app.dao.accounts import chartOfAcctDao
        # create chart of account
        chartOfAcctDao.save(asset_node)
        
        yield engine
        
        # remove chart of account
        chartOfAcctDao.remove(asset_node.chart.acct_type)
    

@mock.patch("src.app.dao.connection.get_engine")
def test_account(mock_engine, engine_with_acct, sample_accounts):
    mock_engine.return_value = engine_with_acct
    
    from src.app.dao.accounts import acctDao
    
    # should not have any account
    with pytest.raises(NotExistError):
        acctDao.get(sample_accounts[0].acct_id, sample_accounts[0].chart)
    
    for acct in sample_accounts:
        acctDao.add(acct)
        
        # test get_chart_id_by_acct
        assert acctDao.get_chart_id_by_acct(acct.acct_id) == acct.chart.chart_id
        
        # test get
        _acct = acctDao.get(acct.acct_id, acct.chart)
        assert _acct == acct
        
    # test update
    _acct.acct_name = 'random name'
    acctDao.update(_acct)
    _acct2 = acctDao.get(acct.acct_id, acct.chart)
    assert _acct == _acct2
    
    # test remove 1 of the 3 accounts
    with pytest.raises(NotExistError):
        acctDao.remove('random_acct_id')
        
    acctDao.remove(_acct.acct_id) # remove the last account
    with pytest.raises(NotExistError):
        acctDao.get(_acct.acct_id, _acct.chart)
    
    # test no update on non-exist acct (removed from last step)
    with pytest.raises(NotExistError):
        acctDao.update(_acct)
        
    # test update the chart to a non-existing chart
    acct = sample_accounts[0]
    acct.chart = Chart(
        chart_id='random_chart_id', 
        name='random chart', 
        acct_type = AcctType.AST
    )
    with pytest.raises(FKNotExistError):
        acctDao.update(acct)
    
    # remove the first 2 accounts to clean up
    acctDao.remove(sample_accounts[0].acct_id)
    acctDao.remove(sample_accounts[1].acct_id)
    
    
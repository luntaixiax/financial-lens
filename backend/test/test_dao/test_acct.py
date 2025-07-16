import pytest
from unittest import mock
from anytree import PreOrderIter
from src.app.model.exceptions import NotExistError, FKNotExistError
from src.app.model.enums import AcctType
from src.app.model.accounts import Chart, ChartNode

@pytest.fixture
def session_with_acct(test_session, settings, test_chart_of_acct_dao, asset_node: ChartNode):
    with mock.patch("src.app.utils.tools.get_settings") as mock_settings:
        mock_settings.return_value = settings
        # create chart of account
        test_chart_of_acct_dao.save(asset_node)
        
        yield test_session
        
        # remove chart of account
        test_chart_of_acct_dao.remove(asset_node.chart.acct_type)
    
def test_account(test_acct_dao, session_with_acct, sample_accounts):
    
    # should not have any account
    with pytest.raises(NotExistError):
        test_acct_dao.get(sample_accounts[0].acct_id, sample_accounts[0].chart)
    
    for acct in sample_accounts:
        test_acct_dao.add(acct)
        
        # test get_chart_id_by_acct
        assert test_acct_dao.get_chart_id_by_acct(acct.acct_id) == acct.chart.chart_id
        
        # test get
        _acct = test_acct_dao.get(acct.acct_id, acct.chart)
        assert _acct == acct
        
    # test update
    _acct.acct_name = 'random name'
    test_acct_dao.update(_acct)
    _acct2 = test_acct_dao.get(acct.acct_id, acct.chart)
    assert _acct == _acct2
    
    # test remove 1 of the 3 accounts
    with pytest.raises(NotExistError):
        test_acct_dao.remove('random_acct_id')
        
    test_acct_dao.remove(_acct.acct_id) # remove the last account
    with pytest.raises(NotExistError):
        test_acct_dao.get(_acct.acct_id, _acct.chart)
    
    # test no update on non-exist acct (removed from last step)
    with pytest.raises(NotExistError):
        test_acct_dao.update(_acct)
        
    # test update the chart to a non-existing chart
    acct = sample_accounts[0]
    acct.chart = Chart(
        chart_id='random_chart_id', 
        name='random chart', 
        acct_type = AcctType.AST
    )
    with pytest.raises(FKNotExistError):
        test_acct_dao.update(acct)
    
    # remove the first 2 accounts to clean up
    test_acct_dao.remove(sample_accounts[0].acct_id)
    test_acct_dao.remove(sample_accounts[1].acct_id)
    
    
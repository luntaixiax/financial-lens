from unittest import mock

import pytest
from src.app.model.accounts import Account, Chart
from src.app.model.exceptions import FKNotExistError, NotExistError, FKNoDeleteUpdateError, OpNotPermittedError
from src.app.model.const import SystemAcctNumber, SystemChartOfAcctNumber
from src.app.model.enums import AcctType


@mock.patch("src.app.dao.connection.get_engine")
def test_coa(mock_engine, engine_with_test_choa):
    mock_engine.return_value = engine_with_test_choa
    
    from src.app.service.acct import AcctService
    
    # load the asset node
    _node = AcctService.get_coa(AcctType.AST)
    # try remove the bank asset node
    _bnk_node = _node.find_node_by_id(
        chart_id=SystemChartOfAcctNumber.BANK_ASSET
    )
    _bnk_node.parent = None # delete it from the tree
    # try to save back, should be fine because no acct hangs on it
    AcctService.save_coa(_node)
    # try to load back bank chart, should not be able to do so
    with pytest.raises(NotExistError):
        AcctService.get_chart(_bnk_node.chart_id)
        
    # try to remove current asset node
    _ca_node = _node.find_node_by_id(
        chart_id=SystemChartOfAcctNumber.CUR_ASSET
    )
    _ca_node.parent = None # delete it from the tree
    # try to save back, should raise FK error because there is account
    with pytest.raises(FKNoDeleteUpdateError):
        AcctService.save_coa(_node)
    
    # try to remove chart of account
    with pytest.raises(FKNoDeleteUpdateError):
        AcctService.delete_coa(AcctType.AST)
    
@mock.patch("src.app.dao.connection.get_engine")
def test_account(mock_engine, engine_with_test_choa):
    mock_engine.return_value = engine_with_test_choa
    
    from src.app.service.acct import AcctService
    
    # test get_account and get_chart
    _acct = AcctService.get_account(acct_id=SystemAcctNumber.ACCT_PAYAB)
    _chart = AcctService.get_chart(_acct.chart.chart_id)
    assert _acct.chart == _chart
    
    # test add account
    # fail if chart not exist
    random = Account(
        acct_name="Rental Expense",
        acct_type=AcctType.EXP,
        chart=Chart(name='random chart', acct_type=AcctType.EXP)
    )
    with pytest.raises(FKNotExistError):
        AcctService.add_account(random)
    
    _coa = AcctService.get_coa(acct_type=AcctType.EXP)
    exp_chart = _coa.find_node_by_id(SystemChartOfAcctNumber.TOTAL_EXP).chart
    rental = Account(
        acct_name="Rental Expense",
        acct_type=AcctType.EXP,
        chart=exp_chart
    )
    AcctService.add_account(rental)
    meal = Account(
        acct_name="Meal Expense",
        acct_type=AcctType.EXP,
        chart=exp_chart
    )
    AcctService.add_account(meal)
    _meal = AcctService.get_account(acct_id=meal.acct_id)
    assert _meal == meal
    # test get accounts by chart
    _exps = AcctService.get_accounts_by_chart(exp_chart)
    assert len(_exps) == 2
    assert rental in _exps
    assert meal in _exps
    
    # test update account
    meal.acct_name='Meal and Entertainment'
    AcctService.update_account(meal)
    # test update non-exist account
    random = Account(
        acct_name="Random Expense",
        acct_type=AcctType.EXP,
        chart=exp_chart
    )
    with pytest.raises(NotExistError):
        AcctService.update_account(random)
    # test upsert
    AcctService.upsert_account(random)
    _random = AcctService.get_account(acct_id=random.acct_id)
    assert _random == random
    # test update account to a chart not exist
    random.chart = Chart(
        name='random_chart',
        acct_type=AcctType.EXP
    )
    with pytest.raises(FKNotExistError):
        AcctService.update_account(random)
    with pytest.raises(FKNotExistError):
        AcctService.upsert_account(random)
    
    # test delete account
    # test delete system account
    with pytest.raises(OpNotPermittedError):
        AcctService.delete_account(acct_id=SystemAcctNumber.ACCT_PAYAB)
    with pytest.raises(NotExistError):
        AcctService.delete_account(acct_id='random_acct')
    AcctService.delete_account(acct_id='random_acct', ignore_nonexist=True)
    
    for acct in AcctService.get_accounts_by_chart(exp_chart):
        AcctService.delete_account(acct.acct_id)
    
    assert len(AcctService.get_accounts_by_chart(exp_chart)) == 0
from unittest import mock
from pprint import pprint
import pytest
from src.app.model.accounts import Account, Chart, ChartNode
from src.app.model.exceptions import FKNotExistError, NotExistError, FKNoDeleteUpdateError, OpNotPermittedError
from src.app.model.const import SystemAcctNumber, SystemChartOfAcctNumber
from src.app.model.enums import AcctType


@mock.patch("src.app.dao.connection.get_engine")
def test_coa(mock_engine, engine_with_basic_choa):
    mock_engine.return_value = engine_with_basic_choa
    
    from src.app.service.acct import AcctService
    
    # load the asset node
    _node = AcctService.get_coa(AcctType.AST)
    _node.print()
    
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
        
    # test add chart directly
    _node = AcctService.get_coa(AcctType.AST)
    test_bank = Chart(
        name='test-bank',
        acct_type=AcctType.AST
    )
    AcctService.add_chart(
        child_chart=test_bank,
        parent_chart_id=_node.chart_id
    )
    test_wise = Chart(
        name='test-wise',
        acct_type=AcctType.AST
    )
    AcctService.add_chart(
        child_chart=test_wise,
        parent_chart_id=test_bank.chart_id
    )
    _test_bank = AcctService.get_chart(test_bank.chart_id)
    assert _test_bank == test_bank
    _test_wise = AcctService.get_chart(test_wise.chart_id)
    assert _test_wise == test_wise
    
    # test update chart
    test_bank.name = 'test-bank-2'
    AcctService.update_chart(test_bank)
    _test_bank = AcctService.get_chart(test_bank.chart_id)
    assert _test_bank == test_bank
    
    # test move chart
    AcctService.move_chart(
        chart_id=test_wise.chart_id, 
        new_parent_chart_id=SystemChartOfAcctNumber.CUR_ASSET
    )
    _test_wise = AcctService.get_chart(test_wise.chart_id)
    _node = AcctService.get_coa(AcctType.AST)
    assert _test_wise == test_wise
    _cur_asset = _node.find_node_by_id(SystemChartOfAcctNumber.CUR_ASSET)
    _wise_node = _node.find_node_by_id(test_wise.chart_id)
    assert _wise_node.parent == _cur_asset
    assert len(_cur_asset.descendants) == 1
    assert len(_node.children) == 3
    assert len(_node.descendants) == 5
    AcctService.move_chart(
        chart_id=test_bank.chart_id, 
        new_parent_chart_id=SystemChartOfAcctNumber.NONCUR_ASSET
    )
    _node = AcctService.get_coa(AcctType.AST)
    _noncur_asset = _node.find_node_by_id(SystemChartOfAcctNumber.NONCUR_ASSET)
    _bank_node = _node.find_node_by_id(test_bank.chart_id)
    assert _bank_node.parent == _noncur_asset
    assert len(_cur_asset.descendants) == 1
    assert len(_noncur_asset.descendants) == 2
    assert len(_node.children) == 2
    assert len(_node.descendants) == 5
    
    # test delete account
    AcctService.delete_chart(chart_id=test_bank.chart_id)
    AcctService.delete_chart(chart_id=test_wise.chart_id)
    _node = AcctService.get_coa(AcctType.AST)
    _noncur_asset = _node.find_node_by_id(SystemChartOfAcctNumber.NONCUR_ASSET)
    _cur_asset = _node.find_node_by_id(SystemChartOfAcctNumber.CUR_ASSET)
    assert len(_cur_asset.descendants) == 0
    assert len(_noncur_asset.descendants) == 1
    
@mock.patch("src.app.dao.connection.get_engine")
def test_account(mock_engine, engine_with_basic_choa):
    mock_engine.return_value = engine_with_basic_choa
    
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
    assert len(_exps) == 6
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
        try:
            AcctService.delete_account(acct.acct_id)
        except OpNotPermittedError:
            pass
    
    assert len(AcctService.get_accounts_by_chart(exp_chart)) == 4 # leave 4 system account
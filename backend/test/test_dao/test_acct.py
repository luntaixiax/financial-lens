import pytest
from unittest import mock
from anytree import PreOrderIter
from src.app.model.exceptions import NotExistError
from src.app.model.const import SystemChartOfAcctNumber
from src.app.model.enums import AcctType
from src.app.model.accounts import Chart, ChartNode

@pytest.fixture
def asset_node() -> ChartNode:
    total_asset = ChartNode(
        Chart(
            chart_id=SystemChartOfAcctNumber.TOTAL_ASSET, 
            name='1000 - Total Asset',
            acct_type=AcctType.AST
        )
    )
    current_asset = ChartNode(
        Chart(
            chart_id=SystemChartOfAcctNumber.CUR_ASSET,
            name='1100 - Current Asset',
            acct_type=AcctType.AST
        ), 
        parent = total_asset
    )
    bank_asset = ChartNode(
        Chart(
            chart_id=SystemChartOfAcctNumber.BANK_ASSET,
            name='1110 - Bank Asset',
            acct_type=AcctType.AST
        ), 
        parent = current_asset
    )
    noncurrent_asset = ChartNode(
        Chart(
            chart_id=SystemChartOfAcctNumber.NONCUR_ASSET,
            name='1200 - Non-Current Asset',
            acct_type=AcctType.AST
        ), 
        parent = total_asset
    )
    return total_asset

@mock.patch("src.app.dao.connection.get_engine")
def test_tree_save_load_delete(mock_engine, engine, asset_node):
    mock_engine.return_value = engine
    
    from src.app.dao.accounts import chartOfAcctDao
    
    with pytest.raises(NotExistError):
        _node = chartOfAcctDao.load(AcctType.AST)
        
    # should not raise error if not exist
    chartOfAcctDao.remove(AcctType.AST) # should not exist
    
    # write a tree
    chartOfAcctDao.save(asset_node)
    
    # load back the tree
    _asset_node = chartOfAcctDao.load(AcctType.AST)
    
    # compare the new node
    assert _asset_node.is_root
    # iterate through the tree
    for node in PreOrderIter(asset_node):
        _node = _asset_node.find_node_by_id(chart_id=node.chart_id)
        assert _node.chart == node.chart
        
    # remove the charts
    chartOfAcctDao.remove(AcctType.AST)
    
    # chart should not exist
    with pytest.raises(NotExistError):
        _node = chartOfAcctDao.load(AcctType.AST)


@mock.patch("src.app.dao.connection.get_engine")
def test_tree_update_no_delete(mock_engine, engine, asset_node):
    mock_engine.return_value = engine
    
    from src.app.dao.accounts import chartOfAcctDao
    
    # write a tree
    chartOfAcctDao.save(asset_node)
    
    # update the tree (no deletion of existing node)
    _asset_node = chartOfAcctDao.load(AcctType.AST)
    # move bank asset to be under non-current asset
    _bank = _asset_node.find_node_by_name('1110 - Bank Asset')
    _noncur = _asset_node.find_node_by_name('1200 - Non-Current Asset')
    _bank.parent = _noncur
    _bank.chart.name = '1210 - Bank Asset' # change node chart name
    
    # add new node (bank check) under bank account
    bank_check = ChartNode(
        Chart(
            name='1211 - Checking Accounts',
            acct_type=AcctType.AST
        ), 
        parent = _bank
    )
    
    # add new node (fixed asset) under non-current account
    fixed_asset = ChartNode(
        Chart(
            name='1220 - Fixed Asset',
            acct_type=AcctType.AST
        ), 
        parent = _noncur
    )
    
    # save the updated node
    chartOfAcctDao.save(_asset_node)
    
    # see if same
    _asset_node_reload = chartOfAcctDao.load(AcctType.AST)
    assert _asset_node_reload.is_root
    # iterate through the tree
    for node in PreOrderIter(_asset_node):
        _node = _asset_node_reload.find_node_by_id(chart_id=node.chart_id)
        assert _node.chart == node.chart
        
    # remove the charts
    chartOfAcctDao.remove(AcctType.AST)
    
    # chart should not exist
    with pytest.raises(NotExistError):
        _node = chartOfAcctDao.load(AcctType.AST)
        

@mock.patch("src.app.dao.connection.get_engine")
def test_tree_update_with_delete(mock_engine, engine, asset_node):
    mock_engine.return_value = engine
    
    from src.app.dao.accounts import chartOfAcctDao
    
    # write a tree
    chartOfAcctDao.save(asset_node)
    
    # update the tree (with deletion of existing node)
    _asset_node = chartOfAcctDao.load(AcctType.AST)
    
    # which can be replace as a subset of the original tree
    _curasset = _asset_node.find_node_by_name('1100 - Current Asset')
    _curasset.parent = None # set it to root
    
    # save the updated tree
    chartOfAcctDao.save(_curasset)
    
    # see if same
    _asset_node_reload = chartOfAcctDao.load(AcctType.AST)
    assert _asset_node_reload.is_root
    # iterate through the tree
    for node in PreOrderIter(_curasset):
        _node = _asset_node_reload.find_node_by_id(chart_id=node.chart_id)
        assert _node.chart == node.chart
        
    # remove the charts
    chartOfAcctDao.remove(AcctType.AST)
        
    # chart should not exist
    with pytest.raises(NotExistError):
        _node = chartOfAcctDao.load(AcctType.AST)
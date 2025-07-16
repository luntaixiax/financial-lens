import pytest
from unittest import mock
from anytree import PreOrderIter
from src.app.model.exceptions import NotExistError
from src.app.model.enums import AcctType
from src.app.model.accounts import Chart, ChartNode

def test_tree_save_load_delete(test_chart_of_acct_dao, asset_node):
    
    with pytest.raises(NotExistError):
        _node = test_chart_of_acct_dao.load(AcctType.AST)
        
    # should not raise error if not exist
    test_chart_of_acct_dao.remove(AcctType.AST) # should not exist
    
    # write a tree
    test_chart_of_acct_dao.save(asset_node)
    
    # load back the tree
    _asset_node = test_chart_of_acct_dao.load(AcctType.AST)
    
    # compare the new node
    assert _asset_node.is_root
    # iterate through the tree
    for node in PreOrderIter(asset_node):
        _node = _asset_node.find_node_by_id(chart_id=node.chart_id)
        assert _node.chart == node.chart
        
    # test get_chart
    _chart = test_chart_of_acct_dao.get_chart(chart_id = _node.chart_id)
    assert _chart == _node.chart
    
    # test get charts
    _charts = sorted(
        test_chart_of_acct_dao.get_charts(AcctType.AST), 
        key=lambda c: c.chart_id
    )
    # get charts from node
    charts = sorted(
        (n.chart for n in PreOrderIter(asset_node)), 
        key=lambda c: c.chart_id
    )
    for _c, c in zip(_charts, charts):
        assert _c == c
        
    # remove the charts
    test_chart_of_acct_dao.remove(AcctType.AST)
    
    # chart should not exist
    with pytest.raises(NotExistError):
        _node = test_chart_of_acct_dao.load(AcctType.AST)


def test_tree_update_no_delete(test_chart_of_acct_dao, asset_node):
    
    # write a tree
    test_chart_of_acct_dao.save(asset_node)
    
    # update the tree (no deletion of existing node)
    _asset_node = test_chart_of_acct_dao.load(AcctType.AST)
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
    test_chart_of_acct_dao.save(_asset_node)
    
    # see if same between the 2 list
    _asset_node_reload = test_chart_of_acct_dao.load(AcctType.AST)
    assert _asset_node_reload.is_root
    # iterate through the tree
    for node in PreOrderIter(_asset_node):
        _node = _asset_node_reload.find_node_by_id(chart_id=node.chart_id)
        assert _node.chart == node.chart
        
    # remove the charts
    test_chart_of_acct_dao.remove(AcctType.AST)
    
    # chart should not exist
    with pytest.raises(NotExistError):
        _node = test_chart_of_acct_dao.load(AcctType.AST)
        

def test_tree_update_with_delete(test_chart_of_acct_dao, asset_node):
    
    # write a tree
    test_chart_of_acct_dao.save(asset_node)
    
    # update the tree (with deletion of existing node)
    _asset_node = test_chart_of_acct_dao.load(AcctType.AST)
    
    # which can be replace as a subset of the original tree
    _curasset = _asset_node.find_node_by_name('1100 - Current Asset')
    _curasset.parent = None # set it to root
    
    # save the updated tree
    test_chart_of_acct_dao.save(_curasset)
    
    # see if same
    _asset_node_reload = test_chart_of_acct_dao.load(AcctType.AST)
    assert _asset_node_reload.is_root
    # iterate through the tree
    for node in PreOrderIter(_curasset):
        _node = _asset_node_reload.find_node_by_id(chart_id=node.chart_id)
        assert _node.chart == node.chart
        
    # remove the charts
    test_chart_of_acct_dao.remove(AcctType.AST)
        
    # chart should not exist
    with pytest.raises(NotExistError):
        _node = test_chart_of_acct_dao.load(AcctType.AST)
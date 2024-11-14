from unittest import mock

import pytest
from src.app.model.exceptions import NotExistError, FKNoDeleteUpdateError
from src.app.model.const import SystemChartOfAcctNumber
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
    
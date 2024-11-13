import pytest
from unittest import mock
from anytree import PreOrderIter
from src.app.model.exceptions import NotExistError
from src.app.model.enums import AcctType
from src.app.model.accounts import Chart, ChartNode

@mock.patch("src.app.dao.connection.get_engine")
def test_add_account(mock_engine, engine, asset_node, sample_accounts):
    mock_engine.return_value = engine
    
    from src.app.dao.accounts import chartOfAcctDao, acctDao
    
    
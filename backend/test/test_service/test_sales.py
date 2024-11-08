import pytest
from unittest import mock
from src.app.model.const import SystemAcctNumber
from src.app.service.chart_of_accounts import AcctService

def test_create_journal_from_invoice(engine, sample_invoice):
    print("Using Engine: ", engine)
    with mock.patch('src.app.dao.connection.get_engine') as mock_engine:
        mock_engine.return_value = engine
        
        AcctService.init()
        
        print("OUTPUT TAX ACCOUNT: ", AcctService.get_account(acct_id = SystemAcctNumber.OUTPUT_TAX))
    
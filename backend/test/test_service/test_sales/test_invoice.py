import logging
import pytest
from unittest import mock
from src.app.model.const import SystemAcctNumber

@mock.patch("src.app.dao.connection.get_engine")
def test_create_journal_from_invoice(mock_engine, engine_with_test_choa, sample_invoice):
    mock_engine.return_value = engine_with_test_choa
    
    from src.app.service.sales import SalesService
    
    print(sample_invoice)
    jorunal = SalesService.create_journal_from_invoice(sample_invoice)
    print(jorunal)
    
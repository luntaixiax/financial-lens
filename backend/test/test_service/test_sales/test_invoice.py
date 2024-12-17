import logging
import pytest
from unittest import mock
from src.app.model.const import SystemAcctNumber

@mock.patch("src.app.dao.connection.get_engine")
def test_create_journal_from_invoice(mock_engine, engine_with_basic_choa, sample_invoice):
    mock_engine.return_value = engine_with_basic_choa
    
    from src.app.service.sales import SalesService
    from src.app.service.fx import FxService
    
    journal = SalesService.create_journal_from_invoice(sample_invoice)
    
    # should not be manual journal
    assert not journal.is_manual
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    # total amount from invoice should be same to total amount from journal (base currency)
    total_invoice = FxService.convert(
        amount=sample_invoice.total, # total billable
        src_currency=sample_invoice.currency, # invoice currency
        cur_dt=sample_invoice.invoice_dt, # convert fx at invoice date
    )
    total_journal = journal.total_debits # total billable = total receivable
    assert total_invoice == total_journal
    
    
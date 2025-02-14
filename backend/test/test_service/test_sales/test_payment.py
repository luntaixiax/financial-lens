from datetime import date
import math
import pytest
from unittest import mock
from src.app.model.const import SystemAcctNumber
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, OpNotPermittedError
from src.app.model.enums import EntityType, JournalSrc
from src.app.model.payment import Payment, PaymentItem

@mock.patch("src.app.dao.connection.get_engine")
def test_validate_payment(mock_engine, engine, sample_payment):
    mock_engine.return_value = engine
    
    from src.app.service.sales import SalesService
    
    # this should pass
    SalesService._validate_payment(sample_payment)
    
    # test invalid entity type
    sample_payment.entity_type = EntityType.SUPPLIER
    with pytest.raises(OpNotPermittedError):
        SalesService._validate_payment(sample_payment)
    sample_payment.entity_type = EntityType.CUSTOMER
    
    # test payment account id not exist
    sample_payment.payment_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        SalesService._validate_payment(sample_payment)
    sample_payment.payment_acct_id = 'acct-bank'
    
    # test invalid payment items
    ## 1. invoice id not exist
    sample_payment.payment_items[0].invoice_id = 'inv-random'
    with pytest.raises(FKNotExistError):
        SalesService._validate_payment(sample_payment)
    sample_payment.payment_items[0].invoice_id = 'inv-sample'
    
    ## 2. when invoice currency equals payment currency, amount not match
    sample_payment.payment_acct_id = 'acct-fbank2' # USD, same as invoice currency
    sample_payment.payment_items[0].payment_amount = 500
    sample_payment.payment_items[0].payment_amount_raw = 450
    with pytest.raises(OpNotPermittedError):
        SalesService._validate_payment(sample_payment)
    sample_payment.payment_items[0].payment_amount_raw = 500
    SalesService._validate_payment(sample_payment)


@mock.patch("src.app.dao.connection.get_engine")
def test_create_journal_from_payment(mock_engine, engine, sample_payment):
    mock_engine.return_value = engine
    
    from src.app.service.sales import SalesService
    from src.app.service.fx import FxService
    
    journal = SalesService.create_journal_from_payment(sample_payment)
    
    # should not be manual journal
    assert journal.jrn_src == JournalSrc.PAYMENT
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    # assert there is fx gain account created
    gain_entries = [
        entry for entry in journal.entries 
        if entry.acct.acct_id == SystemAcctNumber.FX_GAIN
    ]
    assert len(gain_entries) == 1
    gain_entry = gain_entries[0]
    assert math.isclose(gain_entry.amount_base, gain_entry.amount, rel_tol=1e-6)
    # assert there is fee account created
    fee_entries = [
        entry for entry in journal.entries 
        if entry.acct.acct_id == SystemAcctNumber.BANK_FEE
    ]
    assert len(fee_entries) == 1
    
    
@mock.patch("src.app.dao.connection.get_engine")
def test_payment(mock_engine, engine, sample_payment):
    mock_engine.return_value = engine
    
    from src.app.service.sales import SalesService
    from src.app.service.journal import JournalService
    
    # test add payment
    SalesService.add_payment(sample_payment)
    with pytest.raises(AlreadyExistError):
        SalesService.add_payment(sample_payment)
    
    _payment, _journal = SalesService.get_payment_journal(sample_payment.payment_id)
    assert _payment == sample_payment
    
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    with pytest.raises(NotExistError):
        SalesService.get_payment_journal('random-payment')
        
    # test invoice balance
    balance = SalesService.get_invoice_balance(
        invoice_id='inv-sample',
        bal_dt=date(2024, 1, 2)
    )
    
    
    # test update payment
    _payment, _journal = SalesService.get_payment_journal(sample_payment.payment_id)
    _jrn_id = _journal.journal_id # original journal id before updating
    ## update1 -- valid payment level update
    sample_payment.payment_dt = date(2024, 1, 4)
    sample_payment.payment_items[0].payment_amount = 1000
    SalesService.update_payment(sample_payment)
    _payment, _journal = SalesService.get_payment_journal(sample_payment.payment_id)
    assert _payment == sample_payment
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    with pytest.raises(NotExistError):
        # original journal should be deleted
        JournalService.get_journal(_jrn_id)
    
    # test delete payment
    with pytest.raises(NotExistError):
        SalesService.delete_payment('random-payment')
    SalesService.delete_payment(sample_payment.payment_id)
    with pytest.raises(NotExistError):
        SalesService.get_payment_journal(sample_payment.payment_id)
        
    
    
    
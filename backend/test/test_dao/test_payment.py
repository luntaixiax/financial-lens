from datetime import date
import pytest
from unittest import mock

from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError
from src.app.model.enums import CurType, EntityType
from src.app.model.payment import PaymentItem, Payment


@pytest.fixture
def sample_payment(session_with_sample_choa, test_invoice_dao, test_journal_dao, 
                   sample_invoice, sample_journal_meal):
    
        # add sample journal (does not matter which journal to link to, as long as there is one)
        test_journal_dao.add(sample_journal_meal) # add journal
        
        # finally you can add invoice
        test_invoice_dao.add(
            journal_id = sample_journal_meal.journal_id, 
            invoice = sample_invoice
        )
        
        # create payment
        payment = Payment(
            payment_id='pmt-sample',
            payment_num='PMT-001',
            payment_dt=date(2024, 1, 2),
            entity_type=EntityType.CUSTOMER,
            payment_items=[
                PaymentItem(
                    payment_item_id='pmtitem-1',
                    invoice_id='inv-sample',
                    payment_amount=1100,
                    payment_amount_raw=800
                )
            ],
            payment_acct_id='acct-bank',
            payment_fee=12,
            ref_num='#12345',
            note='payment from client'
        )
        
        yield payment
        
        test_invoice_dao.remove(sample_invoice.invoice_id)
        test_journal_dao.remove(sample_journal_meal.journal_id)
        
def test_payment(session_with_sample_choa, sample_payment, test_payment_dao, test_journal_dao):
    
    # assert payment not found, and have correct error type
    with pytest.raises(NotExistError):
        test_payment_dao.get(payment_id=sample_payment.payment_id)
        
    # add sample journal (does not matter which journal to link to, as long as there is one)
    sample_journal_meal = test_journal_dao.get('jrn-sample')
    #journalDao.add(sample_journal_meal) # add journal
        
    # test add payment
    test_payment_dao.add(journal_id=sample_journal_meal.journal_id, payment=sample_payment)
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        test_payment_dao.add(journal_id=sample_journal_meal.journal_id, payment=sample_payment)
    _payment, _ = test_payment_dao.get(payment_id=sample_payment.payment_id)
    assert _payment == sample_payment
    
    # test list
    payments = test_payment_dao.list_payment()
    assert len(payments) == 1
    payments = test_payment_dao.list_payment(entity_type=EntityType.SUPPLIER)
    assert len(payments) == 0
    payments = test_payment_dao.list_payment(payment_nums=['PMT-001'])
    assert len(payments) == 1
    payments = test_payment_dao.list_payment(currency=CurType.EUR)
    assert len(payments) == 0
    payments = test_payment_dao.list_payment(num_invoices=1)
    assert len(payments) == 1
    payments = test_payment_dao.list_payment(invoice_nums=['INV-001'])
    assert len(payments) == 1
    payments = test_payment_dao.list_payment(payment_acct_id='acct-random')
    assert len(payments) == 0
    
    # test update (only update payment body)
    sample_payment.payment_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        test_payment_dao.update(journal_id=sample_journal_meal.journal_id, payment=sample_payment)
    # should be no change
    sample_payment.payment_acct_id = 'acct-bank'
    _payment, _ = test_payment_dao.get(payment_id=sample_payment.payment_id)
    assert _payment == sample_payment
    # test update (success case)
    sample_payment.payment_dt = date(2024, 1, 3)
    test_payment_dao.update(journal_id=sample_journal_meal.journal_id, payment=sample_payment)
    _payment, _ = test_payment_dao.get(payment_id=sample_payment.payment_id)
    assert _payment == sample_payment
    
    # test update with changed payment items
    sample_payment.payment_items[0].invoice_id = 'inv-random'
    with pytest.raises(FKNotExistError):
        test_payment_dao.update(journal_id=sample_journal_meal.journal_id, payment=sample_payment)    
    # should be no change
    sample_payment.payment_items[0].invoice_id = 'inv-sample'
    _payment, _ = test_payment_dao.get(payment_id=sample_payment.payment_id)
    assert _payment == sample_payment
    # test update payment item success case
    sample_payment.payment_items[0].payment_amount_raw = 900
    test_payment_dao.update(journal_id=sample_journal_meal.journal_id, payment=sample_payment)
    _payment, _ = test_payment_dao.get(payment_id=sample_payment.payment_id)
    assert _payment == sample_payment
    
    # test remove payment
    test_payment_dao.remove(payment_id=sample_payment.payment_id)
    with pytest.raises(NotExistError):
        test_payment_dao.get(payment_id=sample_payment.payment_id)
    
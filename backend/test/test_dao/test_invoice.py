from datetime import date
from typing import Generator
from unittest import mock
import pytest
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError
from src.app.model.enums import CurType, EntityType, ItemType, UnitType
from src.app.model.invoice import Invoice, InvoiceItem, Item
        
def test_item(session_with_sample_choa, sample_items, test_item_dao):
    
    # test add item
    for item in sample_items:
        test_item_dao.add(item)
    with pytest.raises(AlreadyExistError):
        # add existing item will trigger error
        test_item_dao.add(sample_items[0])
        
    # test item get
    for item in sample_items:
        _item = test_item_dao.get(item.item_id)
        assert _item == item
    with pytest.raises(NotExistError):
        test_item_dao.get('random-item-id')
    
    # test item update
    item0 = sample_items[0]
    item0.item_type = ItemType.GOOD
    item0.name = 'Item - Test Good'
    item0.unit = UnitType.PIECE
    test_item_dao.update(item0)
    _item0 = test_item_dao.get(item0.item_id)
    assert _item0 == item0
    
    # test delete
    with pytest.raises(NotExistError):
        test_item_dao.remove('random-item-id')
    for item in sample_items:
        test_item_dao.remove(item.item_id)
        with pytest.raises(NotExistError):
            test_item_dao.get(item.item_id)
    
def test_invoice(session_with_sample_choa, sample_invoice, sample_journal_meal, test_invoice_dao, test_journal_dao):
    
    # add without journal and customer will fail
    with pytest.raises(FKNotExistError):
        test_invoice_dao.add(journal_id = 'test-jrn', invoice = sample_invoice)
    
    # add sample journal (does not matter which journal to link to, as long as there is one)
    test_journal_dao.add(sample_journal_meal) # add journal
    
    # finally you can add invoice
    test_invoice_dao.add(
        journal_id = sample_journal_meal.journal_id, 
        invoice = sample_invoice
    )
    # test get invoice
    _invoice, _jrn_id = test_invoice_dao.get(sample_invoice.invoice_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _invoice == sample_invoice
    assert len(_invoice.ginvoice_items) == 1
    assert len(_invoice.invoice_items) == 2
    
    # test list and filter
    _invoices = test_invoice_dao.list_invoice()
    assert len(_invoices) == 1
    _invoices = test_invoice_dao.list_invoice(currency=CurType.USD)
    assert len(_invoices) == 1
    _invoices = test_invoice_dao.list_invoice(currency=CurType.EUR)
    assert len(_invoices) == 0
    _invoices = test_invoice_dao.list_invoice(num_invoice_items=2)
    assert len(_invoices) == 1
    _invoices = test_invoice_dao.list_invoice(num_invoice_items=3)
    assert len(_invoices) == 0
    _invoices = test_invoice_dao.list_invoice(max_amount=1000)
    assert len(_invoices) == 1
    
    
    # test remove invoice
    test_invoice_dao.remove(sample_invoice.invoice_id)
    with pytest.raises(NotExistError):
        test_invoice_dao.get(sample_invoice.invoice_id)
    
    test_journal_dao.remove(sample_journal_meal.journal_id)
    
    
    
    
    
    
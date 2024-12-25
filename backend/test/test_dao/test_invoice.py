from datetime import date
from typing import Generator
from unittest import mock
import pytest
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError
from src.app.model.enums import CurType, EntityType, ItemType, UnitType
from src.app.model.invoice import Invoice, InvoiceItem, Item
        

@mock.patch("src.app.dao.connection.get_engine")
def test_item(mock_engine, engine_with_sample_choa, sample_items):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.dao.invoice import itemDao
    
    # test add item
    for item in sample_items:
        itemDao.add(item)
    with pytest.raises(AlreadyExistError):
        # add existing item will trigger error
        itemDao.add(sample_items[0])
        
    # test item get
    for item in sample_items:
        _item = itemDao.get(item.item_id)
        assert _item == item
    with pytest.raises(NotExistError):
        itemDao.get('random-item-id')
    
    # test item update
    item0 = sample_items[0]
    item0.item_type = ItemType.GOOD
    item0.name = 'Item - Test Good'
    item0.unit = UnitType.PIECE
    itemDao.update(item0)
    _item0 = itemDao.get(item0.item_id)
    assert _item0 == item0
    
    # test delete
    with pytest.raises(NotExistError):
        itemDao.remove('random-item-id')
    for item in sample_items:
        itemDao.remove(item.item_id)
        with pytest.raises(NotExistError):
            itemDao.get(item.item_id)
    
@mock.patch("src.app.dao.connection.get_engine")
def test_invoice(mock_engine, engine, sample_invoice, sample_journal_meal):
    mock_engine.return_value = engine
    
    from src.app.dao.invoice import invoiceDao
    from src.app.dao.journal import journalDao
    
    # add without journal and customer will fail
    with pytest.raises(FKNotExistError):
        invoiceDao.add(journal_id = 'test-jrn', invoice = sample_invoice)
    
    # add sample journal (does not matter which journal to link to, as long as there is one)
    journalDao.add(sample_journal_meal) # add journal
    
    # finally you can add invoice
    invoiceDao.add(
        journal_id = sample_journal_meal.journal_id, 
        invoice = sample_invoice
    )
    # test get invoice
    _invoice, _jrn_id = invoiceDao.get(sample_invoice.invoice_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _invoice == sample_invoice
    assert len(_invoice.ginvoice_items) == 1
    assert len(_invoice.invoice_items) == 2
    
    # test list and filter
    _invoices = invoiceDao.list()
    assert len(_invoices) == 1
    _invoices = invoiceDao.list(currency=CurType.USD)
    assert len(_invoices) == 1
    _invoices = invoiceDao.list(currency=CurType.EUR)
    assert len(_invoices) == 0
    _invoices = invoiceDao.list(num_invoice_items=2)
    assert len(_invoices) == 1
    _invoices = invoiceDao.list(num_invoice_items=3)
    assert len(_invoices) == 0
    _invoices = invoiceDao.list(max_amount=1000)
    assert len(_invoices) == 1
    
    
    # test remove invoice
    invoiceDao.remove(sample_invoice.invoice_id)
    with pytest.raises(NotExistError):
        invoiceDao.get(sample_invoice.invoice_id)
    
    journalDao.remove(sample_journal_meal.journal_id)
    
    
    
    
    
    
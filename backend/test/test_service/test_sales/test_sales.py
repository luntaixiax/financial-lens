from datetime import date
import logging
import pytest
from unittest import mock
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, NotMatchWithSystemError
from src.app.model.enums import CurType, EntityType, ItemType, JournalSrc, UnitType
from src.app.model.invoice import Invoice, InvoiceItem, Item
from src.app.model.const import SystemAcctNumber

@mock.patch("src.app.dao.connection.get_engine")
def test_create_journal_from_invoice(mock_engine, engine_with_sample_choa, sample_invoice):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.sales import SalesService
    from src.app.service.fx import FxService
    from src.app.service.entity import EntityService
    
    EntityService.create_sample()
    
    journal = SalesService.create_journal_from_invoice(sample_invoice)
    
    # should not be manual journal
    assert journal.jrn_src == JournalSrc.INVOICE
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
    
    EntityService.clear_sample()
    
    
@mock.patch("src.app.dao.connection.get_engine")
def test_validate_item(mock_engine, engine_with_sample_choa):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.sales import SalesService
    
    # test validate item
    # 1. add item with non-exist account
    item = Item(
        item_id='item-random',
        name='Item - Consulting',
        item_type=ItemType.SERVICE,
        unit=UnitType.HOUR,
        unit_price=100,
        currency=CurType.USD,
        default_acct_id='acct-random'
    )
    with pytest.raises(NotExistError):
        SalesService._validate_item(item)
    
    # 2. add item with existing, but non income expense account
    item = Item(
        item_id='item-random',
        name='Item - Consulting',
        item_type=ItemType.SERVICE,
        unit=UnitType.HOUR,
        unit_price=100,
        currency=CurType.USD,
        default_acct_id='acct-bank'
    )
    with pytest.raises(NotMatchWithSystemError):
        SalesService._validate_item(item)
    

@mock.patch("src.app.dao.connection.get_engine")
def test_item(mock_engine, engine_with_sample_choa):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.sales import SalesService
    
    item_consult = Item(
        item_id='item-consul',
        name='Item - Consulting',
        item_type=ItemType.SERVICE,
        unit=UnitType.HOUR,
        unit_price=100,
        currency=CurType.USD,
        default_acct_id='acct-consul'
    )
    # test add item
    SalesService.add_item(item_consult)
    with pytest.raises(AlreadyExistError):
        # should get error if trying to add one more time
        SalesService.add_item(item_consult)
    
    # test get item
    _item = SalesService.get_item(item_consult.item_id)
    assert _item == item_consult
    with pytest.raises(NotExistError):
        SalesService.get_item('item-random')
        
    # test update account
    item_consult.currency = CurType.JPY
    SalesService.update_item(item_consult)
    _item = SalesService.get_item(item_consult.item_id)
    assert _item == item_consult
    # test update not allowed change field
    item_consult.unit = UnitType.DAY
    with pytest.raises(NotMatchWithSystemError):
        SalesService.update_item(item_consult)
    item_consult.item_type = ItemType.GOOD
    with pytest.raises(NotMatchWithSystemError):
        SalesService.update_item(item_consult)
    item_consult.unit = UnitType.HOUR
    item_consult.item_type = ItemType.SERVICE
        
    # test delete item
    with pytest.raises(NotExistError):
        SalesService.delete_item('item-random')
    SalesService.delete_item(item_consult.item_id)
    with pytest.raises(NotExistError):
        SalesService.get_item(item_consult.item_id)
    
@mock.patch("src.app.dao.connection.get_engine")
def test_validate_invoice(mock_engine, engine_with_sample_choa):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.sales import SalesService
    from src.app.service.entity import EntityService
    from src.app.dao.invoice import itemDao
    
    # create items
    item_consult = Item(
        item_id='item-consul',
        name='Item - Consulting',
        item_type=ItemType.SERVICE,
        unit=UnitType.HOUR,
        unit_price=100,
        currency=CurType.USD,
        default_acct_id='acct-consul'
    )
    item_meeting = Item(
        item_id='item-meet',
        name='Item - Meeting',
        item_type=ItemType.SERVICE,
        unit=UnitType.HOUR,
        unit_price=75,
        currency=CurType.USD,
        default_acct_id='acct-consul'
    )
        
    # create invoice with non-exist customer
    invoice = Invoice(
        invoice_num='INV-001',
        invoice_dt=date(2024, 1, 1),
        due_dt=date(2024, 1, 5),
        entity_id='cust-random',
        entity_type=EntityType.CUSTOMER,
        subject='General Consulting - Jan 2024',
        currency=CurType.USD,
        invoice_items=[
            InvoiceItem(
                item=item_consult,
                quantity=5,
                description="Programming"
            ),
            InvoiceItem(
                item=item_meeting,
                quantity=10,
                description="Meeting Around",
                discount_rate=0.05,
            )
        ],
        shipping=10,
        note="Thanks for business"
    )
    with pytest.raises(FKNotExistError):
        # customer not exist
        SalesService._validate_invoice(invoice)
    
    # create the customer
    EntityService.create_sample()
    invoice.entity_id = 'cust-sample'
    
    with pytest.raises(FKNotExistError):
        # item not exist
        SalesService._validate_invoice(invoice)
        
    # add items
    itemDao.add(item_consult)
    itemDao.add(item_meeting)    
    
    # no problem this time
    SalesService._validate_invoice(invoice)
    
    # test with changed item
    invoice.invoice_items[0].item.unit_price = 200
    with pytest.raises(NotMatchWithSystemError):
        SalesService._validate_invoice(invoice)
    invoice.invoice_items[0].item.unit_price = 100 # change back
    
    # test with non-exist account
    invoice.invoice_items[0].acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        SalesService._validate_invoice(invoice)
    
    
    # clean up
    EntityService.clear_sample()
    itemDao.remove(item_consult.item_id)
    itemDao.remove(item_meeting.item_id)
    
    
@mock.patch("src.app.dao.connection.get_engine")
def test_invoice(mock_engine, engine_with_sample_choa, sample_invoice):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.sales import SalesService
    from src.app.service.entity import EntityService
    from src.app.service.journal import JournalService
    
    EntityService.create_sample()
    
    # test add invoice
    SalesService.add_invoice(sample_invoice)
    with pytest.raises(AlreadyExistError):
        SalesService.add_invoice(sample_invoice)
    
    _invoice, _journal = SalesService.get_invoice_journal(sample_invoice.invoice_id)
    assert _invoice == sample_invoice
    
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    with pytest.raises(NotExistError):
        SalesService.get_invoice_journal('random-invoice')
        
    # test list invoices
    invoices = SalesService.list_invoice()
    assert len(invoices) == 1
    invoices = SalesService.list_invoice(currency=CurType.USD)
    assert len(invoices) == 1
    invoices = SalesService.list_invoice(currency=CurType.AUD)
    assert len(invoices) == 0
    invoices = SalesService.list_invoice(num_invoice_items=2)
    assert len(invoices) == 1
    invoices = SalesService.list_invoice(num_invoice_items=3)
    assert len(invoices) == 0
    
    
    # test delete invoice
    with pytest.raises(NotExistError):
        SalesService.delete_invoice('random-invoice')
    SalesService.delete_invoice(sample_invoice.invoice_id)
    with pytest.raises(NotExistError):
        SalesService.get_invoice_journal(sample_invoice.invoice_id)
        
    EntityService.clear_sample()
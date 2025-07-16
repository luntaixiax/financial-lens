from datetime import date
import logging
import pytest
from unittest import mock
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, NotMatchWithSystemError
from src.app.model.enums import CurType, EntityType, ItemType, JournalSrc, UnitType
from src.app.model.invoice import GeneralInvoiceItem, Invoice, InvoiceItem, Item
from src.app.model.const import SystemAcctNumber

def test_create_journal_from_invoice(session_with_sample_choa, sample_invoice, 
                                     test_sales_service, test_fx_service, test_entity_service):
    
    test_entity_service.create_sample()
    
    journal = test_sales_service.create_journal_from_invoice(sample_invoice)
    
    # should not be manual journal
    assert journal.jrn_src == JournalSrc.SALES
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    # total amount from invoice should be same to total amount from journal (base currency)
    total_invoice = test_fx_service.convert_to_base(
        amount=sample_invoice.total, # total billable
        src_currency=sample_invoice.currency, # invoice currency
        cur_dt=sample_invoice.invoice_dt, # convert fx at invoice date
    )
    total_journal = journal.total_debits # total billable = total receivable
    assert total_invoice == total_journal
    
    # there should be and only 1 fx gain account
    gain_entries = [
        entry for entry in journal.entries 
        if entry.acct.acct_id == SystemAcctNumber.FX_GAIN
    ]
    assert len(gain_entries) == 1
    
    test_entity_service.clear_sample()
    
    
def test_validate_item(session_with_sample_choa, test_sales_service):
    
    # test validate item
    # 1. add item with non-exist account
    item = Item(
        item_id='item-random',
        name='Item - Consulting',
        item_type=ItemType.SERVICE,
        entity_type=EntityType.CUSTOMER,
        unit=UnitType.HOUR,
        unit_price=100,
        currency=CurType.USD,
        default_acct_id='acct-random'
    )
    with pytest.raises(NotExistError):
        test_sales_service._validate_item(item)
    
    # 2. add item with existing, but non income expense account
    item = Item(
        item_id='item-random',
        name='Item - Consulting',
        item_type=ItemType.SERVICE,
        entity_type=EntityType.CUSTOMER,
        unit=UnitType.HOUR,
        unit_price=100,
        currency=CurType.USD,
        default_acct_id='acct-bank'
    )
    with pytest.raises(NotMatchWithSystemError):
        test_sales_service._validate_item(item)
    

def test_item(session_with_sample_choa, test_item_service): 
    
    item_consult = Item(
        item_id='item-consul',
        name='Item - Consulting',
        item_type=ItemType.SERVICE,
        entity_type=EntityType.CUSTOMER,
        unit=UnitType.HOUR,
        unit_price=100,
        currency=CurType.USD,
        default_acct_id='acct-consul'
    )
    # test add item
    test_item_service.add_item(item_consult)
    with pytest.raises(AlreadyExistError):
        # should get error if trying to add one more time
        test_item_service.add_item(item_consult)
    
    # test get item
    _item = test_item_service.get_item(item_consult.item_id)
    assert _item == item_consult
    with pytest.raises(NotExistError):
        test_item_service.get_item('item-random')
        
    # test update account
    item_consult.currency = CurType.JPY
    test_item_service.update_item(item_consult)
    _item = test_item_service.get_item(item_consult.item_id)
    assert _item == item_consult
    # test update not allowed change field
    item_consult.unit = UnitType.DAY
    with pytest.raises(NotMatchWithSystemError):
        test_item_service.update_item(item_consult)
    item_consult.item_type = ItemType.GOOD
    with pytest.raises(NotMatchWithSystemError):
        test_item_service.update_item(item_consult)
    item_consult.unit = UnitType.HOUR
    item_consult.item_type = ItemType.SERVICE
        
    # test delete item
    with pytest.raises(NotExistError):
        test_item_service.delete_item('item-random')
    test_item_service.delete_item(item_consult.item_id)
    with pytest.raises(NotExistError):
        test_item_service.get_item(item_consult.item_id)


def test_validate_invoice(session_with_sample_choa, test_sales_service, test_entity_service, test_item_service):
    
    # create items
    item_consult = Item(
        item_id='item-consul',
        name='Item - Consulting',
        item_type=ItemType.SERVICE,
        entity_type=EntityType.CUSTOMER,
        unit=UnitType.HOUR,
        unit_price=100,
        currency=CurType.USD,
        default_acct_id='acct-consul'
    )
    item_meeting = Item(
        item_id='item-meet',
        name='Item - Meeting',
        item_type=ItemType.SERVICE,
        entity_type=EntityType.CUSTOMER,
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
                acct_id='',
                item=item_consult,
                quantity=5,
                description="Programming"
            ),
            InvoiceItem(
                acct_id='',
                item=item_meeting,
                quantity=10,
                description="Meeting Around",
                discount_rate=0.05,
            )
        ],
        ginvoice_items=[
            GeneralInvoiceItem(
                incur_dt=date(2023, 12, 10),
                acct_id='acct-meal',
                currency=CurType.EUR,
                amount_pre_tax_raw=100,
                amount_pre_tax=120,
                tax_rate=0.05,
                description='Meal for business trip'
            )
        ],
        shipping=10,
        note="Thanks for business"
    )
    with pytest.raises(FKNotExistError):
        # customer not exist
        test_sales_service._validate_invoice(invoice)
    
    # create the customer
    test_entity_service.create_sample()
    invoice.entity_id = 'cust-sample'
    
    with pytest.raises(FKNotExistError):
        # item not exist
        test_sales_service._validate_invoice(invoice)
        
    # add items
    test_item_service.add_item(item_consult)
    test_item_service.add_item(item_meeting)    
    
    # no problem this time
    test_sales_service._validate_invoice(invoice)
    
    # test with changed item
    invoice.invoice_items[0].item.unit_price = 200
    with pytest.raises(NotMatchWithSystemError):
        test_sales_service._validate_invoice(invoice)
    invoice.invoice_items[0].item.unit_price = 100 # change back
    
    # test with wrong account type
    invoice.invoice_items[0].acct_id = 'acct-rental'
    with pytest.raises(NotMatchWithSystemError):
        test_sales_service._validate_invoice(invoice)
    invoice.invoice_items[0].acct_id = 'acct-consul'
    # should not raise error
    invoice.ginvoice_items[0].acct_id = 'acct-consul' 
    test_sales_service._validate_invoice(invoice)
    invoice.ginvoice_items[0].acct_id = 'acct-meal'
    
    # test with non-exist account
    invoice.invoice_items[0].acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        test_sales_service._validate_invoice(invoice)
    invoice.ginvoice_items[0].acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        test_sales_service._validate_invoice(invoice)
    
    # clean up
    test_entity_service.clear_sample()
    test_item_service.delete_item(item_consult.item_id)
    test_item_service.delete_item(item_meeting.item_id)
    
    
def test_invoice(session_with_sample_choa, sample_invoice, test_sales_service, test_entity_service, test_journal_service):
    
    test_entity_service.create_sample()
    
    # test add invoice
    test_sales_service.add_invoice(sample_invoice)
    with pytest.raises(AlreadyExistError):
        test_sales_service.add_invoice(sample_invoice)
    
    _invoice, _journal = test_sales_service.get_invoice_journal(sample_invoice.invoice_id)
    assert _invoice == sample_invoice
    
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    with pytest.raises(NotExistError):
        test_sales_service.get_invoice_journal('random-invoice')
        
    # test list invoices
    invoices = test_sales_service.list_invoice()
    assert len(invoices) == 1
    invoices = test_sales_service.list_invoice(currency=CurType.USD)
    assert len(invoices) == 1
    invoices = test_sales_service.list_invoice(currency=CurType.AUD)
    assert len(invoices) == 0
    invoices = test_sales_service.list_invoice(num_invoice_items=2)
    assert len(invoices) == 1
    invoices = test_sales_service.list_invoice(num_invoice_items=3)
    assert len(invoices) == 0
    
    # test update invoice
    _invoice, _journal = test_sales_service.get_invoice_journal(sample_invoice.invoice_id)
    _jrn_id = _journal.journal_id # original journal id before updating
    ## update1 -- valid invoice level update
    sample_invoice.invoice_dt = date(2024, 1, 2)
    sample_invoice.invoice_items[0].quantity = 8
    test_sales_service.update_invoice(sample_invoice)
    _invoice, _journal = test_sales_service.get_invoice_journal(sample_invoice.invoice_id)
    assert _invoice == sample_invoice
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    with pytest.raises(NotExistError):
        # original journal should be deleted
        test_journal_service.get_journal(_jrn_id)
    
    # test delete invoice
    with pytest.raises(NotExistError):
        test_sales_service.delete_invoice('random-invoice')
    test_sales_service.delete_invoice(sample_invoice.invoice_id)
    with pytest.raises(NotExistError):
        test_sales_service.get_invoice_journal(sample_invoice.invoice_id)
        
    test_entity_service.clear_sample()
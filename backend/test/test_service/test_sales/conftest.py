from datetime import date
from typing import Generator
import pytest
from unittest import mock
from src.app.model.payment import Payment, PaymentItem
from src.app.model.const import SystemChartOfAcctNumber
from src.app.model.invoice import GeneralInvoiceItem, Invoice, InvoiceItem, Item
from src.app.model.enums import AcctType, CurType, EntityType, ItemType, UnitType
from src.app.model.accounts import Account

@pytest.fixture
def sample_invoice(session_with_sample_choa, test_item_dao) -> Generator[Invoice, None, None]:
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
    test_item_dao.add(item_consult)
    test_item_dao.add(item_meeting)
    
    # create invoice
    invoice = Invoice(
        invoice_id='inv-sample',
        invoice_num='INV-001',
        invoice_dt=date(2024, 1, 1),
        due_dt=date(2024, 1, 5),
        entity_id='cust-sample',
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
    
    
    yield invoice
    
    test_item_dao.remove(item_consult.item_id)
    test_item_dao.remove(item_meeting.item_id)
        
@pytest.fixture
def sample_payment(session_with_sample_choa, sample_invoice, test_entity_service, test_sales_service):
        
    test_entity_service.create_sample()
    test_sales_service.add_invoice(sample_invoice)
    
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
    
    test_sales_service.delete_invoice(sample_invoice.invoice_id)
    test_entity_service.clear_sample()
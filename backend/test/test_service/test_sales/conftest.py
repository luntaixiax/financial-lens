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
def sample_invoice(engine_with_sample_choa) -> Generator[Invoice, None, None]:
    with mock.patch("src.app.dao.connection.get_engine") as mock_engine:
        mock_engine.return_value = engine_with_sample_choa
        
        from src.app.dao.invoice import itemDao
        
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
        itemDao.add(item_consult)
        itemDao.add(item_meeting)
        
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
        
        itemDao.remove(item_consult.item_id)
        itemDao.remove(item_meeting.item_id)
        
@pytest.fixture
def sample_payment(engine, sample_invoice):
    with mock.patch("src.app.dao.connection.get_engine") as mock_engine:
        mock_engine.return_value = engine
        
        from src.app.service.sales import SalesService
        from src.app.service.entity import EntityService
        
        EntityService.create_sample()
        SalesService.add_invoice(sample_invoice)
        
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
        
        SalesService.delete_invoice(sample_invoice.invoice_id)
        EntityService.clear_sample()
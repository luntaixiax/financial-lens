from datetime import date
from typing import Generator
import pytest
from unittest import mock
from src.app.model.const import SystemChartOfAcctNumber
from src.app.model.invoice import Invoice, InvoiceItem, Item
from src.app.model.enums import AcctType, CurType, ItemType, UnitType
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
        itemDao.add(item_consult)
        itemDao.add(item_meeting)
        
        # create invoice
        invoice = Invoice(
            invoice_num='INV-001',
            invoice_dt=date(2024, 1, 1),
            due_dt=date(2024, 1, 5),
            customer_id='cust-sample',
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
        
        
        yield invoice
        
        itemDao.remove(item_consult.item_id)
        itemDao.remove(item_meeting.item_id)
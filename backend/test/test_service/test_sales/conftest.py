from datetime import date
from typing import Generator
import pytest
from unittest import mock
from src.app.model.const import SystemChartOfAcctNumber
from src.app.model.invoice import Invoice, InvoiceItem, Item
from src.app.model.enums import AcctType, CurType, ItemType, UnitType
from src.app.model.accounts import Account

@pytest.fixture
def sample_invoice(engine_with_test_choa) -> Generator[Invoice, None, None]:
    with mock.patch("src.app.dao.connection.get_engine") as mock_engine:
        mock_engine.return_value = engine_with_test_choa
        
        # non-model module need to import under mock replacement
        from src.app.service.acct import AcctService
        
        
        # create accounts (consulting income)
        rev_acct = Account(
            acct_name='Consulting Income',
            acct_type=AcctType.INC,
            chart=AcctService.get_coa(AcctType.INC).find_node_by_id(
                chart_id=SystemChartOfAcctNumber.TOTAL_INC
            ).chart
        )
        AcctService.add_account(rev_acct)
        
        # create items
        item_consult = Item(
            name='Item - Consulting',
            item_type=ItemType.SERVICE,
            unit=UnitType.HOUR,
            unit_price=100,
            currency=CurType.USD,
            default_acct_id=rev_acct.acct_id
        )
        item_meeting = Item(
            name='Item - Meeting',
            item_type=ItemType.SERVICE,
            unit=UnitType.HOUR,
            unit_price=75,
            currency=CurType.USD,
            default_acct_id=rev_acct.acct_id
        )
        
        # create invoice
        invoice = Invoice(
            invoice_num='INV-001',
            invoice_dt=date(2024, 1, 1),
            due_dt=date(2024, 1, 5),
            customer_id='C123',
            subject='General Consulting - Jan 2024',
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
        
        # delete account
        AcctService.delete_account(rev_acct.acct_id, restrictive=False)
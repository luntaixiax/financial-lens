
from datetime import date
from typing import Generator
from unittest import mock
import pytest
from src.app.model.accounts import Account, Chart, ChartNode
from src.app.model.const import SystemAcctNumber, SystemChartOfAcctNumber
from src.app.model.enums import AcctType, CurType, EntityType, EntryType, ItemType, JournalSrc, UnitType
from src.app.model.entity import Address, Contact, Customer
from src.app.model.journal import Entry, Journal
from src.app.model.invoice import GeneralInvoiceItem, Invoice, InvoiceItem, Item
        
            
@pytest.fixture
def contact1() -> Contact:
    return Contact(
        name='luntaixia',
        email='infodesk@ltxservice.ca',
        phone='123456789',
        address=Address(
            address1='00 XX St E',
            address2=None,
            suite_no=1234,
            city='Toronto',
            state='ON',
            country='Canada',
            postal_code='XYZABC'
        )
    )
    
@pytest.fixture
def customer1(contact1) -> Customer:
    return Customer(
        customer_name = 'LTX Company',
        is_business=True,
        bill_contact=contact1,
        ship_same_as_bill=True,
        ship_contact=None
    )
    

@pytest.fixture
def asset_node() -> ChartNode:
    total_asset = ChartNode(
        Chart(
            chart_id=SystemChartOfAcctNumber.TOTAL_ASSET, 
            name='1000 - Total Asset',
            acct_type=AcctType.AST
        )
    )
    current_asset = ChartNode(
        Chart(
            chart_id=SystemChartOfAcctNumber.CUR_ASSET,
            name='1100 - Current Asset',
            acct_type=AcctType.AST
        ), 
        parent = total_asset
    )
    bank_asset = ChartNode(
        Chart(
            chart_id=SystemChartOfAcctNumber.BANK_ASSET,
            name='1110 - Bank Asset',
            acct_type=AcctType.AST
        ), 
        parent = current_asset
    )
    noncurrent_asset = ChartNode(
        Chart(
            chart_id=SystemChartOfAcctNumber.NONCUR_ASSET,
            name='1200 - Non-Current Asset',
            acct_type=AcctType.AST
        ), 
        parent = total_asset
    )
    return total_asset

@pytest.fixture
def sample_accounts(asset_node: ChartNode, test_setting_service) -> list[Account]:
    
    # create system accounts (tax, AR/AP, etc.)
    input_tax = Account(
        acct_id=SystemAcctNumber.INPUT_TAX,
        acct_name="Input Tax",
        acct_type=AcctType.AST,
        currency=test_setting_service.get_base_currency(),
        chart=asset_node.find_node_by_id(SystemChartOfAcctNumber.NONCUR_ASSET).chart
    )
    ar = Account(
        acct_id=SystemAcctNumber.ACCT_RECEIV,
        acct_name="Account Receivable",
        acct_type=AcctType.AST,
        currency=test_setting_service.get_base_currency(),                
        chart=asset_node.find_node_by_id(SystemChartOfAcctNumber.CUR_ASSET).chart
    )
    check = Account(
        acct_name="TEST BANK CHECK",
        acct_type=AcctType.AST,
        currency=CurType.USD,
        chart=asset_node.find_node_by_id(SystemChartOfAcctNumber.BANK_ASSET).chart
    )
    return [input_tax, ar, check]


@pytest.fixture
def sample_journal_meal(session_with_sample_choa, test_acct_service, test_setting_service) -> Generator[Journal, None, None]:
        
        journal = Journal(
            journal_id='jrn-sample',
            jrn_date=date(2024, 1, 1),
            entries=[
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=test_acct_service.get_account('acct-meal'),
                    cur_incexp=test_setting_service.get_base_currency(),
                    amount=105.83,
                    amount_base=105.83,
                    description='Have KFC with client'
                ),
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=test_acct_service.get_account('acct-tip'),
                    cur_incexp=test_setting_service.get_base_currency(),
                    amount=13.93,
                    amount_base=13.93,
                    description='Tip for KFC'
                ),
                Entry(
                    entry_type=EntryType.DEBIT,
                    acct=test_acct_service.get_account(SystemAcctNumber.INPUT_TAX),
                    cur_incexp=None,
                    amount=13.35,
                    amount_base=13.35,
                    description=None
                ),
                Entry(
                    entry_type=EntryType.CREDIT,
                    acct=test_acct_service.get_account('acct-bank'),
                    cur_incexp=None,
                    amount=133.11,
                    amount_base=133.11,
                    description=None
                ),
            ],
            jrn_src=JournalSrc.MANUAL,
            note='sample meal journal'
        )
        
        yield journal
        
@pytest.fixture
def sample_items() -> list[Item]:
    item_consult = Item(
        name='Item - Consulting',
        item_type=ItemType.SERVICE,
        entity_type=EntityType.CUSTOMER,
        unit=UnitType.HOUR,
        unit_price=100,
        currency=CurType.USD,
        default_acct_id='acct-consul'
    )
    item_meeting = Item(
        name='Item - Meeting',
        item_type=ItemType.SERVICE,
        entity_type=EntityType.CUSTOMER,
        unit=UnitType.HOUR,
        unit_price=75,
        currency=CurType.USD,
        default_acct_id='acct-consul'
    )
    return [item_consult, item_meeting]

@pytest.fixture
def sample_invoice(
    session_with_sample_choa, 
    test_item_dao, 
    test_customer_dao, 
    test_contact_dao, 
    sample_items, 
    customer1
) -> Generator[Invoice, None, None]:
    
    # add customer
    test_contact_dao.add(contact = customer1.bill_contact)
    test_customer_dao.add(customer1)
    
    # add items
    for item in sample_items:
        test_item_dao.add(item)
    
    # create invoice
    invoice = Invoice(
        invoice_id='inv-sample',
        invoice_num='INV-001',
        invoice_dt=date(2024, 1, 1),
        due_dt=date(2024, 1, 5),
        entity_id=customer1.cust_id,
        entity_type=EntityType.CUSTOMER,
        subject='General Consulting - Jan 2024',
        currency=CurType.USD,
        invoice_items=[
            InvoiceItem(
                acct_id='',
                item=sample_items[0],
                quantity=5,
                description="Programming"
            ),
            InvoiceItem(
                acct_id='',
                item=sample_items[1],
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
    
    # delete items
    for item in sample_items:
        test_item_dao.remove(item.item_id)
        
    test_customer_dao.remove(customer1.cust_id)
    test_contact_dao.remove(customer1.bill_contact.contact_id)
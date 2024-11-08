import pytest
from unittest import mock
from pathlib import Path
import sqlalchemy
from src.app.model.invoice import Invoice, InvoiceItem, Item
from src.app.model.enums import AcctType, CurType, ItemType, UnitType
from src.app.dao.orm import SQLModel
from src.app.service.chart_of_accounts import AcctService

@pytest.fixture(scope='module')
def engine():
    # setup a sqlite database
    cur_path = Path() / 'test.db'
    engine = sqlalchemy.create_engine(f'sqlite:///{cur_path.as_posix()}')
    SQLModel.metadata.create_all(engine)
    print("Created SQLite Engine: ", engine)
    
    yield engine
        
    # TODO: delete the sqlite db
    


@pytest.fixture
def sample_invoice() -> Invoice:
    consulting_item = Item(
        name='General Consulting',
        item_type=ItemType.SERVICE,
        unit=UnitType.HOUR,
        unit_price=100,
        currency=CurType.USD,
        default_acct_id="",
    )
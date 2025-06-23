from datetime import date
import pytest
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError
from src.app.model.enums import CurType, PropertyType, PropertyTransactionType
from src.app.model.property import Property, PropertyTransaction

@pytest.fixture
def sample_property() -> Property:
    property = Property(
        property_id='test-prop',
        property_name='Computer',
        property_type=PropertyType.EQUIP,
        pur_dt=date(2024, 1, 3),
        pur_price=10000,
        tax=700,
        pur_acct_id='acct-fbank'
    )
    return property

@pytest.fixture
def sample_depreciation() -> PropertyTransaction:
    return PropertyTransaction(
        property_id='test-prop',
        trans_dt=date(2024, 2, 1),
        trans_type=PropertyTransactionType.DEPRECIATION,
        trans_amount=500
    )
    
@pytest.fixture
def sample_appreciation() -> PropertyTransaction:
    return PropertyTransaction(
        property_id='test-prop',
        trans_dt=date(2024, 2, 1),
        trans_type=PropertyTransactionType.APPRECIATION,
        trans_amount=500
    )
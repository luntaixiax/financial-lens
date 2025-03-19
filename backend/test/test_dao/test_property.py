from datetime import date
from typing import Generator
from unittest import mock
import pytest
from src.app.utils.tools import get_base_cur
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError
from src.app.model.enums import CurType, PropertyType
from src.app.model.property import Property, PropertyTransaction

@pytest.fixture
def sample_property() -> Property:
    property = Property(
        property_name='Computer',
        property_type=PropertyType.EQUIP,
        pur_dt=date(2024, 1, 3),
        pur_price=10000,
        pur_acct_id='acct-fbank'
    )
    return property
    
#@mock.patch("src.app.utils.tools.get_settings")
@mock.patch("src.app.dao.connection.get_engine")
def test_expense(mock_engine, engine_with_sample_choa, sample_property):
    mock_engine.return_value = engine_with_sample_choa

    
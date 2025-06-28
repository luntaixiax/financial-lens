from datetime import date
from typing import Generator
from unittest import mock
import pytest
from src.app.utils.tools import get_base_cur
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
        tax=500,
        pur_acct_id='acct-fbank',
        note='A computer'
    )
    return property

@pytest.fixture
def sample_depreciation() -> PropertyTransaction:
    return PropertyTransaction(
        trans_id='test-depre',
        property_id='test-prop',
        trans_dt=date(2024, 2, 1),
        trans_type=PropertyTransactionType.DEPRECIATION,
        trans_amount=500
    )
    
@pytest.fixture
def sample_appreciation() -> PropertyTransaction:
    return PropertyTransaction(
        trans_id='test-appre',
        property_id='test-prop',
        trans_dt=date(2024, 2, 1),
        trans_type=PropertyTransactionType.APPRECIATION,
        trans_amount=300
    )
    
@mock.patch("src.app.dao.connection.get_engine")
def test_property(mock_engine, engine_with_sample_choa, sample_property, sample_journal_meal):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.dao.property import propertyDao
    from src.app.dao.journal import journalDao
    
    # assert property not found, and have correct error type
    with pytest.raises(NotExistError):
        propertyDao.get(sample_property.property_id)

    # add without journal will fail
    with pytest.raises(FKNotExistError):
        propertyDao.add(journal_id = 'test-jrn', property = sample_property)
        
    # add sample journal (does not matter which journal to link to, as long as there is one)
    journalDao.add(sample_journal_meal) # add journal
    
    # then can add property
    propertyDao.add(journal_id = sample_journal_meal.journal_id, property = sample_property)
    
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        propertyDao.add(journal_id = sample_journal_meal.journal_id, property = sample_property)
    
    # test get property
    _property, _jrn_id = propertyDao.get(sample_property.property_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _property == sample_property
    
    # test update property
    sample_property.property_name = 'Laptop'
    sample_property.pur_price = 20000
    propertyDao.update(sample_journal_meal.journal_id, sample_property)
    _property, _jrn_id = propertyDao.get(sample_property.property_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _property == sample_property
    
    # delete property
    propertyDao.remove(sample_property.property_id)
    with pytest.raises(NotExistError):
        propertyDao.get(sample_property.property_id)
        
    # delete journal
    journalDao.remove(sample_journal_meal.journal_id)
    
    
@mock.patch("src.app.dao.connection.get_engine")
def test_property_trans(mock_engine, engine_with_sample_choa, sample_property, sample_depreciation, 
        sample_journal_meal):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.dao.property import propertyDao, propertyTransactionDao
    from src.app.dao.journal import journalDao
    
    # assert property not found, and have correct error type
    with pytest.raises(NotExistError):
        propertyTransactionDao.get(sample_depreciation.trans_id)
        
    # add without journal will fail
    with pytest.raises(FKNotExistError):
        propertyTransactionDao.add(journal_id = sample_journal_meal.journal_id, property_trans = sample_depreciation)
        
    # add sample journal (does not matter which journal to link to, as long as there is one)
    journalDao.add(sample_journal_meal) # add journal
    
    # add without property will also fail
    with pytest.raises(FKNotExistError):
        propertyTransactionDao.add(journal_id = sample_journal_meal.journal_id, property_trans = sample_depreciation)
    
    # add property first
    propertyDao.add(journal_id = sample_journal_meal.journal_id, property = sample_property)
    
    # then we can add transaction
    propertyTransactionDao.add(journal_id = sample_journal_meal.journal_id, property_trans = sample_depreciation)
    
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        propertyTransactionDao.add(journal_id = sample_journal_meal.journal_id, property_trans = sample_depreciation)
    
    # test get property trans
    _property_trans, _jrn_id = propertyTransactionDao.get(sample_depreciation.trans_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _property_trans == sample_depreciation
    
    # test update property trans
    sample_depreciation.trans_type = PropertyTransactionType.APPRECIATION
    propertyTransactionDao.update(sample_journal_meal.journal_id, sample_depreciation)
    _property_trans, _jrn_id = propertyTransactionDao.get(sample_depreciation.trans_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _property_trans == sample_depreciation
    
    # delete property trans
    propertyTransactionDao.remove(sample_depreciation.trans_id)
    with pytest.raises(NotExistError):
        propertyTransactionDao.get(sample_depreciation.trans_id)
    
    # delete property
    propertyDao.remove(sample_property.property_id)
    
    # delete journal
    journalDao.remove(sample_journal_meal.journal_id)
from datetime import date
from typing import Generator
from unittest import mock
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
        tax=500,
        pur_acct_id='acct-fbank',
        note='A computer',
        receipts=None
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
    
def test_property(session_with_sample_choa, test_property_dao, test_journal_dao, 
                  sample_property, sample_journal_meal):
    
    # assert property not found, and have correct error type
    with pytest.raises(NotExistError):
        test_property_dao.get(sample_property.property_id)

    # add without journal will fail
    with pytest.raises(FKNotExistError):
        test_property_dao.add(journal_id = 'test-jrn', property = sample_property)
        
    # add sample journal (does not matter which journal to link to, as long as there is one)
    test_journal_dao.add(sample_journal_meal) # add journal
    
    # then can add property
    test_property_dao.add(journal_id = sample_journal_meal.journal_id, property = sample_property)
    
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        test_property_dao.add(journal_id = sample_journal_meal.journal_id, property = sample_property)
    
    # test get property
    _property, _jrn_id = test_property_dao.get(sample_property.property_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _property == sample_property
    
    # test update property
    sample_property.property_name = 'Laptop'
    sample_property.pur_price = 20000
    test_property_dao.update(sample_journal_meal.journal_id, sample_property)
    _property, _jrn_id = test_property_dao.get(sample_property.property_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _property == sample_property
    
    # delete property
    test_property_dao.remove(sample_property.property_id)
    with pytest.raises(NotExistError):
        test_property_dao.get(sample_property.property_id)
        
    # delete journal
    test_journal_dao.remove(sample_journal_meal.journal_id)
    
    
def test_property_trans(session_with_sample_choa, test_property_trans_dao, test_journal_dao, 
                        test_property_dao, sample_property, sample_depreciation, sample_journal_meal):
    
    # assert property not found, and have correct error type
    with pytest.raises(NotExistError):
        test_property_trans_dao.get(sample_depreciation.trans_id)
        
    # add without journal will fail
    with pytest.raises(FKNotExistError):
        test_property_trans_dao.add(journal_id = sample_journal_meal.journal_id, property_trans = sample_depreciation)
        
    # add sample journal (does not matter which journal to link to, as long as there is one)
    test_journal_dao.add(sample_journal_meal) # add journal
    
    # add without property will also fail
    with pytest.raises(FKNotExistError):
        test_property_trans_dao.add(journal_id = sample_journal_meal.journal_id, property_trans = sample_depreciation)
    
    # add property first
    test_property_dao.add(journal_id = sample_journal_meal.journal_id, property = sample_property)
    
    # then we can add transaction
    test_property_trans_dao.add(journal_id = sample_journal_meal.journal_id, property_trans = sample_depreciation)
    
    # test no duplicate add
    with pytest.raises(AlreadyExistError):
        test_property_trans_dao.add(journal_id = sample_journal_meal.journal_id, property_trans = sample_depreciation)
    
    # test get property trans
    _property_trans, _jrn_id = test_property_trans_dao.get(sample_depreciation.trans_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _property_trans == sample_depreciation
    
    # test update property trans
    sample_depreciation.trans_type = PropertyTransactionType.APPRECIATION
    test_property_trans_dao.update(sample_journal_meal.journal_id, sample_depreciation)
    _property_trans, _jrn_id = test_property_trans_dao.get(sample_depreciation.trans_id)
    assert _jrn_id == sample_journal_meal.journal_id
    assert _property_trans == sample_depreciation
    
    # delete property trans
    test_property_trans_dao.remove(sample_depreciation.trans_id)
    with pytest.raises(NotExistError):
        test_property_trans_dao.get(sample_depreciation.trans_id)
    
    # delete property
    test_property_dao.remove(sample_property.property_id)
    
    # delete journal
    test_journal_dao.remove(sample_journal_meal.journal_id)
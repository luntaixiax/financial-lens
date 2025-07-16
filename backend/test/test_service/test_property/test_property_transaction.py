from datetime import date
from unittest import mock
import pytest
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, NotMatchWithSystemError
from src.app.model.enums import JournalSrc, PropertyType, PropertyTransactionType
from src.app.model.property import Property, PropertyTransaction


@pytest.fixture
def test_sample_property_session(session_with_sample_choa, sample_property, test_property_service):  
    
    test_property_service.add_property(sample_property)
    
    yield session_with_sample_choa
    
    test_property_service.delete_property(sample_property.property_id)
    
    
def test_create_journal_from_property_trans(test_sample_property_session, sample_property, sample_depreciation, 
                                            test_property_service, test_fx_service, test_acct_service):
    
    journal = test_property_service.create_journal_from_property_trans(sample_depreciation)
    assert journal.jrn_src == JournalSrc.PPNE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    
    # total amount from property_trans should be same to total amount from journal (base currency)
    pur_acct = test_acct_service.get_account(
        sample_property.pur_acct_id
    )
    amount_base = test_fx_service.convert_to_base(
        amount=sample_depreciation.trans_amount,
        src_currency=pur_acct.currency, # purchase currency
        cur_dt=sample_depreciation.trans_dt, # convert fx at depreciation date
    )
    assert amount_base == journal.total_debits
    
def test_validate_property_trans(test_sample_property_session, test_property_service):
    
    property_trans = PropertyTransaction(
        trans_id='test-depre',
        property_id='test-prop',
        trans_dt=date(2024, 2, 1),
        trans_type=PropertyTransactionType.DEPRECIATION,
        trans_amount=500
    )
    # successful validation
    test_property_service._validate_propertytrans(property_trans)
    
    # validate property id
    property_trans.property_id = 'prop-random'
    with pytest.raises(FKNotExistError):
        # account not exist
        test_property_service._validate_propertytrans(property_trans)
        
    # validate purchase date
    property_trans.property_id = 'test-prop'
    property_trans.trans_dt = date(2000, 1, 1)
    with pytest.raises(NotMatchWithSystemError):
        test_property_service._validate_propertytrans(property_trans)

def test_property_trans(test_sample_property_session, sample_depreciation, test_property_service, test_journal_service):
    # test add property_trans
    test_property_service.add_property_trans(sample_depreciation)
    with pytest.raises(AlreadyExistError):
        test_property_service.add_property_trans(sample_depreciation)
    
    # assert journal is correctly added
    _property_tans, _journal = test_property_service.get_property_trans_journal(sample_depreciation.trans_id)
    assert _property_tans == sample_depreciation
    
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    with pytest.raises(NotExistError):
        test_property_service.get_property_trans_journal('random-property-trans')
        
    # test update property_trans
    _property_tans, _journal = test_property_service.get_property_trans_journal(sample_depreciation.trans_id)
    _jrn_id = _journal.journal_id # original journal id before updating
    # update 1 --  valid property_trans update
    sample_depreciation.trans_amount = 600
    sample_depreciation.trans_dt = date(2024, 1, 15)
    test_property_service.update_property_trans(sample_depreciation)
    _property_tans, _journal = test_property_service.get_property_trans_journal(sample_depreciation.trans_id)
    assert _property_tans == sample_depreciation
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    with pytest.raises(NotExistError):
        # original journal should be deleted
        test_journal_service.get_journal(_jrn_id)
    
    # test delete property_trans
    with pytest.raises(NotExistError):
        test_property_service.delete_property_trans('random-property_trans')
    test_property_service.delete_property_trans(sample_depreciation.trans_id)
    with pytest.raises(NotExistError):
        test_property_service.get_property_trans_journal(sample_depreciation.trans_id)
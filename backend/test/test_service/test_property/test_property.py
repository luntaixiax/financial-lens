from datetime import date
from unittest import mock
import pytest
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, NotMatchWithSystemError
from src.app.model.enums import JournalSrc, PropertyType
from src.app.model.property import Property

def test_create_journal_from_property(session_with_sample_choa, sample_property, 
                test_property_service, test_fx_service, test_acct_service):
    
    journal = test_property_service.create_journal_from_property(sample_property)
    assert journal.jrn_src == JournalSrc.PPNE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    
    # total amount from property should be same to total amount from journal (base currency)
    pur_acct = test_acct_service.get_account(
        sample_property.pur_acct_id
    )
    amount_base = test_fx_service.convert_to_base(
        amount=sample_property.pur_price,
        src_currency=pur_acct.currency, # purchase currency
        cur_dt=sample_property.pur_dt, # convert fx at purchase date
    )
    assert amount_base == journal.total_debits
    
def test_validate_property(session_with_sample_choa, test_property_service):
    
    property = Property(
        property_id='test-prop',
        property_name='Computer',
        property_type=PropertyType.EQUIP,
        pur_dt=date(2024, 1, 3),
        pur_price=10000,
        pur_acct_id='acct-fbank',
        note=None,
        receipts=None
    )
    # successful validation
    test_property_service._validate_property(property)
    
    # validate purchase account id
    property.pur_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        # account not exist
        test_property_service._validate_property(property)
    property.pur_acct_id = 'acct-fbank'
    # validate purchase account type
    property.pur_acct_id = 'acct-rental'
    with pytest.raises(NotMatchWithSystemError):
        test_property_service._validate_property(property)

def test_property(session_with_sample_choa, sample_property, test_property_service, test_journal_service):
    
    # test add property
    test_property_service.add_property(sample_property)
    with pytest.raises(AlreadyExistError):
        test_property_service.add_property(sample_property)
    
    # assert journal is correctly added
    _property, _journal = test_property_service.get_property_journal(sample_property.property_id)
    assert _property == sample_property
    
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    with pytest.raises(NotExistError):
        test_property_service.get_property_journal('random-property')
        
    # test update property
    _property, _journal = test_property_service.get_property_journal(sample_property.property_id)
    _jrn_id = _journal.journal_id # original journal id before updating
    # update 1 --  valid property update
    sample_property.pur_price = 35000
    sample_property.pur_dt = date(2024, 1, 10)
    test_property_service.update_property(sample_property)
    _property, _journal = test_property_service.get_property_journal(sample_property.property_id)
    assert _property == sample_property
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    with pytest.raises(NotExistError):
        # original journal should be deleted
        test_journal_service.get_journal(_jrn_id)
    
    # test delete property
    with pytest.raises(NotExistError):
        test_property_service.delete_property('random-property')
    test_property_service.delete_property(sample_property.property_id)
    with pytest.raises(NotExistError):
        test_property_service.get_property_journal(sample_property.property_id)
from datetime import date
from unittest import mock
import pytest
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, NotMatchWithSystemError
from src.app.model.enums import JournalSrc, PropertyType
from src.app.model.property import Property

@mock.patch("src.app.dao.connection.get_engine")
def test_create_journal_from_property(mock_engine, engine_with_sample_choa, sample_property):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.property import PropertyService
    from src.app.service.fx import FxService
    from src.app.service.acct import AcctService
    
    journal = PropertyService.create_journal_from_property(sample_property)
    assert journal.jrn_src == JournalSrc.PPNE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    
    # total amount from property should be same to total amount from journal (base currency)
    pur_acct = AcctService.get_account(
        sample_property.pur_acct_id
    )
    amount_base = FxService.convert_to_base(
        amount=sample_property.pur_price,
        src_currency=pur_acct.currency, # purchase currency
        cur_dt=sample_property.pur_dt, # convert fx at purchase date
    )
    assert amount_base == journal.total_debits
    
@mock.patch("src.app.dao.connection.get_engine")
def test_validate_property(mock_engine, engine_with_sample_choa):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.property import PropertyService
    
    property = Property(
        property_id='test-prop',
        property_name='Computer',
        property_type=PropertyType.EQUIP,
        pur_dt=date(2024, 1, 3),
        pur_price=10000,
        pur_acct_id='acct-fbank',
        note=None
    )
    # successful validation
    PropertyService._validate_property(property)
    
    # validate purchase account id
    property.pur_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        # account not exist
        PropertyService._validate_property(property)
    property.pur_acct_id = 'acct-fbank'
    # validate purchase account type
    property.pur_acct_id = 'acct-rental'
    with pytest.raises(NotMatchWithSystemError):
        PropertyService._validate_property(property)

@mock.patch("src.app.dao.connection.get_engine")
def test_property(mock_engine, engine_with_sample_choa, sample_property):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.property import PropertyService
    from src.app.service.journal import JournalService
    
    # test add property
    PropertyService.add_property(sample_property)
    with pytest.raises(AlreadyExistError):
        PropertyService.add_property(sample_property)
    
    # assert journal is correctly added
    _property, _journal = PropertyService.get_property_journal(sample_property.property_id)
    assert _property == sample_property
    
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    with pytest.raises(NotExistError):
        PropertyService.get_property_journal('random-property')
        
    # test update property
    _property, _journal = PropertyService.get_property_journal(sample_property.property_id)
    _jrn_id = _journal.journal_id # original journal id before updating
    # update 1 --  valid property update
    sample_property.pur_price = 35000
    sample_property.pur_dt = date(2024, 1, 10)
    PropertyService.update_property(sample_property)
    _property, _journal = PropertyService.get_property_journal(sample_property.property_id)
    assert _property == sample_property
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    with pytest.raises(NotExistError):
        # original journal should be deleted
        JournalService.get_journal(_jrn_id)
    
    # test delete property
    with pytest.raises(NotExistError):
        PropertyService.delete_property('random-property')
    PropertyService.delete_property(sample_property.property_id)
    with pytest.raises(NotExistError):
        PropertyService.get_property_journal(sample_property.property_id)
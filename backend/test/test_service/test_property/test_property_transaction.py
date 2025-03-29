from datetime import date
from unittest import mock
import pytest
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, NotMatchWithSystemError
from src.app.model.enums import JournalSrc, PropertyType, PropertyTransactionType
from src.app.model.property import Property, PropertyTransaction


@pytest.fixture
def test_sample_property_engine(engine_with_sample_choa, sample_property):
    with mock.patch("src.app.dao.connection.get_engine")  as mock_engine:
        mock_engine.return_value = engine_with_sample_choa
    
        from src.app.service.property import PropertyService
        
        PropertyService.add_property(sample_property)
        
        yield engine_with_sample_choa
        
        PropertyService.delete_property(sample_property.property_id)
    
    

@mock.patch("src.app.dao.connection.get_engine")
def test_create_journal_from_property_trans(mock_engine, test_sample_property_engine, sample_property, sample_depreciation):
    mock_engine.return_value = test_sample_property_engine
    
    from src.app.service.property import PropertyService
    from src.app.service.fx import FxService
    from src.app.service.acct import AcctService
    
    journal = PropertyService.create_journal_from_property_trans(sample_depreciation)
    assert journal.jrn_src == JournalSrc.PPNE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    
    # total amount from property_trans should be same to total amount from journal (base currency)
    pur_acct = AcctService.get_account(
        sample_property.pur_acct_id
    )
    amount_base = FxService.convert_to_base(
        amount=sample_depreciation.trans_amount,
        src_currency=pur_acct.currency, # purchase currency
        cur_dt=sample_depreciation.trans_dt, # convert fx at depreciation date
    )
    assert amount_base == journal.total_debits
    
@mock.patch("src.app.dao.connection.get_engine")
def test_validate_property_trans(mock_engine, test_sample_property_engine):
    mock_engine.return_value = test_sample_property_engine
    
    from src.app.service.property import PropertyService
    
    property_trans = PropertyTransaction(
        trans_id='test-depre',
        property_id='test-prop',
        trans_dt=date(2024, 2, 1),
        trans_type=PropertyTransactionType.DEPRECIATION,
        trans_amount=500
    )
    # successful validation
    PropertyService._validate_propertytrans(property_trans)
    
    # validate property id
    property_trans.property_id = 'prop-random'
    with pytest.raises(FKNotExistError):
        # account not exist
        PropertyService._validate_propertytrans(property_trans)
        
    # validate purchase date
    property_trans.property_id = 'test-prop'
    property_trans.trans_dt = date(2000, 1, 1)
    with pytest.raises(NotMatchWithSystemError):
        PropertyService._validate_propertytrans(property_trans)

@mock.patch("src.app.dao.connection.get_engine")
def test_property_trans(mock_engine, test_sample_property_engine, sample_depreciation):
    mock_engine.return_value = test_sample_property_engine
    
    from src.app.service.property import PropertyService
    from src.app.service.journal import JournalService
    
    # test add property_trans
    PropertyService.add_property_trans(sample_depreciation)
    with pytest.raises(AlreadyExistError):
        PropertyService.add_property_trans(sample_depreciation)
    
    # assert journal is correctly added
    _property_tans, _journal = PropertyService.get_property_trans_journal(sample_depreciation.trans_id)
    assert _property_tans == sample_depreciation
    
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    with pytest.raises(NotExistError):
        PropertyService.get_property_trans_journal('random-property-trans')
        
    # test update property_trans
    _property_tans, _journal = PropertyService.get_property_trans_journal(sample_depreciation.trans_id)
    _jrn_id = _journal.journal_id # original journal id before updating
    # update 1 --  valid property_trans update
    sample_depreciation.trans_amount = 600
    sample_depreciation.trans_dt = date(2024, 1, 15)
    PropertyService.update_property_trans(sample_depreciation)
    _property_tans, _journal = PropertyService.get_property_trans_journal(sample_depreciation.trans_id)
    assert _property_tans == sample_depreciation
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    with pytest.raises(NotExistError):
        # original journal should be deleted
        JournalService.get_journal(_jrn_id)
    
    # test delete property_trans
    with pytest.raises(NotExistError):
        PropertyService.delete_property_trans('random-property_trans')
    PropertyService.delete_property_trans(sample_depreciation.trans_id)
    with pytest.raises(NotExistError):
        PropertyService.get_property_trans_journal(sample_depreciation.trans_id)
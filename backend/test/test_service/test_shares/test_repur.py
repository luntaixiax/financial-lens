from datetime import date
from unittest import mock
import pytest
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, NotMatchWithSystemError, OpNotPermittedError
from src.app.model.enums import JournalSrc
from src.app.model.shares import StockRepurchase

@mock.patch("src.app.dao.connection.get_engine")
def test_create_journal_from_repur(mock_engine, engine_with_sample_choa, sample_repur):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.shares import SharesService
    from src.app.service.fx import FxService
    from src.app.service.acct import AcctService
    
    journal = SharesService.create_journal_from_repur(sample_repur)
    assert journal.jrn_src == JournalSrc.SHARE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    
    # total amount from repur should be same to total amount from journal (base currency)
    credit_acct = AcctService.get_account(
        sample_repur.credit_acct_id
    )
    amount_base = FxService.convert_to_base(
        amount=sample_repur.repur_amt,
        src_currency=credit_acct.currency, # purchase currency
        cur_dt=sample_repur.repurchase_dt, # convert fx at repur date
    )
    assert amount_base == journal.total_debits
    
@mock.patch("src.app.dao.connection.get_engine")
def test_validate_repur(mock_engine, engine_with_sample_choa):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.shares import SharesService
    
    repur = StockRepurchase(
        repur_id='sample-repur',
        repurchase_dt=date(2024, 1, 3),
        num_shares=100,
        repur_price=5.4,
        credit_acct_id='acct-fbank',
        repur_amt=60000
    )
    # successful validation
    SharesService._validate_repur(repur)
    
    # validate credit account id
    repur.credit_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        # account not exist
        SharesService._validate_repur(repur)
    repur.credit_acct_id = 'acct-fbank'
    # validate purchase account type
    repur.credit_acct_id = 'acct-consul'
    with pytest.raises(NotMatchWithSystemError):
        SharesService._validate_repur(repur)
        
    # test same currency
    repur = StockRepurchase(
        repur_id='sample-repur',
        repurchase_dt=date(2024, 1, 3),
        num_shares=100,
        repur_price=5.4,
        credit_acct_id='acct-bank',
        repur_amt=600
    )
    with pytest.raises(OpNotPermittedError):
        SharesService._validate_repur(repur)

@mock.patch("src.app.dao.connection.get_engine")
def test_repur(mock_engine, engine_with_sample_choa, sample_repur):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.shares import SharesService
    from src.app.service.journal import JournalService
    
    # test add repur
    SharesService.add_repur(sample_repur)
    with pytest.raises(AlreadyExistError):
        SharesService.add_repur(sample_repur)
    
    # assert journal is correctly added
    _repur, _journal = SharesService.get_repur_journal(sample_repur.repur_id)
    assert _repur == sample_repur
    
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    with pytest.raises(NotExistError):
        SharesService.get_repur_journal('random-repur')
        
    # test update repur
    _repur, _journal = SharesService.get_repur_journal(sample_repur.repur_id)
    _jrn_id = _journal.journal_id # original journal id before updating
    # update 1 --  valid repur update
    sample_repur.repur_price = 6
    sample_repur.repur_amt=120
    sample_repur.repurchase_dt = date(2024, 1, 10)
    SharesService.update_repur(sample_repur)
    _repur, _journal = SharesService.get_repur_journal(sample_repur.repur_id)
    assert _repur == sample_repur
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    with pytest.raises(NotExistError):
        # original journal should be deleted
        JournalService.get_journal(_jrn_id)
    
    # test delete repur
    with pytest.raises(NotExistError):
        SharesService.delete_repur('random-repur')
    SharesService.delete_repur(sample_repur.repur_id)
    with pytest.raises(NotExistError):
        SharesService.get_repur_journal(sample_repur.repur_id)
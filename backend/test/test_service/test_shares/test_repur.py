from datetime import date
from unittest import mock
import pytest
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, NotMatchWithSystemError, OpNotPermittedError
from src.app.model.enums import JournalSrc
from src.app.model.shares import StockRepurchase

def test_create_journal_from_repur(session_with_sample_choa, sample_repur, test_shares_service, test_fx_service, test_acct_service):
    
    journal = test_shares_service.create_journal_from_repur(sample_repur)
    assert journal.jrn_src == JournalSrc.SHARE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    
    # total amount from repur should be same to total amount from journal (base currency)
    credit_acct = test_acct_service.get_account(
        sample_repur.credit_acct_id
    )
    amount_base = test_fx_service.convert_to_base(
        amount=sample_repur.repur_amt,
        src_currency=credit_acct.currency, # purchase currency
        cur_dt=sample_repur.repur_dt, # convert fx at repur date
    )
    assert amount_base == journal.total_debits
    
def test_validate_repur(session_with_sample_choa, test_shares_service):
    
    repur = StockRepurchase(
        repur_id='sample-repur',
        repur_dt=date(2024, 1, 3),
        num_shares=100,
        repur_price=5.4,
        credit_acct_id='acct-fbank',
        repur_amt=60000,
        note=None
    )
    # successful validation
    test_shares_service._validate_repur(repur)
    
    # validate credit account id
    repur.credit_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        # account not exist
        test_shares_service._validate_repur(repur)
    repur.credit_acct_id = 'acct-fbank'
    # validate purchase account type
    repur.credit_acct_id = 'acct-consul'
    with pytest.raises(NotMatchWithSystemError):
        test_shares_service._validate_repur(repur)
        
    # test same currency
    repur = StockRepurchase(
        repur_id='sample-repur',
        repur_dt=date(2024, 1, 3),
        num_shares=100,
        repur_price=5.4,
        credit_acct_id='acct-bank',
        repur_amt=600,
        note=None
    )
    with pytest.raises(OpNotPermittedError):
        test_shares_service._validate_repur(repur)

def test_repur(session_with_sample_choa, sample_repur, test_shares_service, test_journal_service):
    
    # test add repur
    test_shares_service.add_repur(sample_repur)
    with pytest.raises(AlreadyExistError):
        test_shares_service.add_repur(sample_repur)
    
    # assert journal is correctly added
    _repur, _journal = test_shares_service.get_repur_journal(sample_repur.repur_id)
    assert _repur == sample_repur
    
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    with pytest.raises(NotExistError):
        test_shares_service.get_repur_journal('random-repur')
        
    # test update repur
    _repur, _journal = test_shares_service.get_repur_journal(sample_repur.repur_id)
    _jrn_id = _journal.journal_id # original journal id before updating
    # update 1 --  valid repur update
    sample_repur.repur_price = 6
    sample_repur.repur_amt=120
    sample_repur.repur_dt = date(2024, 1, 10)
    test_shares_service.update_repur(sample_repur)
    _repur, _journal = test_shares_service.get_repur_journal(sample_repur.repur_id)
    assert _repur == sample_repur
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    with pytest.raises(NotExistError):
        # original journal should be deleted
        test_journal_service.get_journal(_jrn_id)
    
    # test delete repur
    with pytest.raises(NotExistError):
        test_shares_service.delete_repur('random-repur')
    test_shares_service.delete_repur(sample_repur.repur_id)
    with pytest.raises(NotExistError):
        test_shares_service.get_repur_journal(sample_repur.repur_id)
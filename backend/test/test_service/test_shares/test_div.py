from datetime import date
from unittest import mock
import pytest
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, NotMatchWithSystemError, OpNotPermittedError
from src.app.model.enums import JournalSrc
from src.app.model.shares import Dividend

def test_create_journal_from_div(session_with_sample_choa, sample_div, test_shares_service, test_fx_service, test_acct_service):
    
    journal = test_shares_service.create_journal_from_div(sample_div)
    assert journal.jrn_src == JournalSrc.SHARE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    
    # total amount from div should be same to total amount from journal (base currency)
    credit_acct = test_acct_service.get_account(
        sample_div.credit_acct_id
    )
    amount_base = test_fx_service.convert_to_base(
        amount=sample_div.div_amt,
        src_currency=credit_acct.currency, # purchase currency
        cur_dt=sample_div.div_dt, # convert fx at div date
    )
    assert amount_base == journal.total_debits
    
def test_validate_div(session_with_sample_choa, test_shares_service):
    
    div = Dividend(
        div_id='sample-div',
        div_dt=date(2024, 1, 3),
        credit_acct_id='acct-fbank',
        div_amt=60000,
        note=None
    )
    # successful validation
    test_shares_service._validate_div(div)
    
    # validate credit account id
    div.credit_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        # account not exist
        test_shares_service._validate_div(div)
    div.credit_acct_id = 'acct-fbank'
    # validate purchase account type
    div.credit_acct_id = 'acct-consul'
    with pytest.raises(NotMatchWithSystemError):
        test_shares_service._validate_div(div)


def test_div(session_with_sample_choa, sample_div, test_shares_service, test_journal_service):
    
    # test add div
    test_shares_service.add_div(sample_div)
    with pytest.raises(AlreadyExistError):
        test_shares_service.add_div(sample_div)
    
    # assert journal is correctly added
    _div, _journal = test_shares_service.get_div_journal(sample_div.div_id)
    assert _div == sample_div
    
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    with pytest.raises(NotExistError):
        test_shares_service.get_div_journal('random-div')
        
    # test update div
    _div, _journal = test_shares_service.get_div_journal(sample_div.div_id)
    _jrn_id = _journal.journal_id # original journal id before updating
    # update 1 --  valid div update
    sample_div.div_amt=120
    sample_div.div_dt = date(2024, 1, 10)
    test_shares_service.update_div(sample_div)
    _div, _journal = test_shares_service.get_div_journal(sample_div.div_id)
    assert _div == sample_div
    _journal_ = test_journal_service.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    with pytest.raises(NotExistError):
        # original journal should be deleted
        test_journal_service.get_journal(_jrn_id)
    
    # test delete div
    with pytest.raises(NotExistError):
        test_shares_service.delete_div('random-div')
    test_shares_service.delete_div(sample_div.div_id)
    with pytest.raises(NotExistError):
        test_shares_service.get_div_journal(sample_div.div_id)
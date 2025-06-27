from datetime import date
from unittest import mock
import pytest
from src.app.model.exceptions import AlreadyExistError, FKNotExistError, NotExistError, NotMatchWithSystemError, OpNotPermittedError
from src.app.model.enums import JournalSrc
from src.app.model.shares import Dividend

@mock.patch("src.app.dao.connection.get_engine")
def test_create_journal_from_div(mock_engine, engine_with_sample_choa, sample_div):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.shares import SharesService
    from src.app.service.fx import FxService
    from src.app.service.acct import AcctService
    
    journal = SharesService.create_journal_from_div(sample_div)
    assert journal.jrn_src == JournalSrc.SHARE
    # should be non-redudant, i.e, similar entries have been combined
    assert not journal.is_redundant
    
    # total amount from div should be same to total amount from journal (base currency)
    credit_acct = AcctService.get_account(
        sample_div.credit_acct_id
    )
    amount_base = FxService.convert_to_base(
        amount=sample_div.div_amt,
        src_currency=credit_acct.currency, # purchase currency
        cur_dt=sample_div.div_dt, # convert fx at div date
    )
    assert amount_base == journal.total_debits
    
@mock.patch("src.app.dao.connection.get_engine")
def test_validate_div(mock_engine, engine_with_sample_choa):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.shares import SharesService
    
    div = Dividend(
        div_id='sample-div',
        div_dt=date(2024, 1, 3),
        credit_acct_id='acct-fbank',
        div_amt=60000
    )
    # successful validation
    SharesService._validate_div(div)
    
    # validate credit account id
    div.credit_acct_id = 'acct-random'
    with pytest.raises(FKNotExistError):
        # account not exist
        SharesService._validate_div(div)
    div.credit_acct_id = 'acct-fbank'
    # validate purchase account type
    div.credit_acct_id = 'acct-consul'
    with pytest.raises(NotMatchWithSystemError):
        SharesService._validate_div(div)


@mock.patch("src.app.dao.connection.get_engine")
def test_div(mock_engine, engine_with_sample_choa, sample_div):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.service.shares import SharesService
    from src.app.service.journal import JournalService
    
    # test add div
    SharesService.add_div(sample_div)
    with pytest.raises(AlreadyExistError):
        SharesService.add_div(sample_div)
    
    # assert journal is correctly added
    _div, _journal = SharesService.get_div_journal(sample_div.div_id)
    assert _div == sample_div
    
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    
    with pytest.raises(NotExistError):
        SharesService.get_div_journal('random-div')
        
    # test update div
    _div, _journal = SharesService.get_div_journal(sample_div.div_id)
    _jrn_id = _journal.journal_id # original journal id before updating
    # update 1 --  valid div update
    sample_div.div_amt=120
    sample_div.div_dt = date(2024, 1, 10)
    SharesService.update_div(sample_div)
    _div, _journal = SharesService.get_div_journal(sample_div.div_id)
    assert _div == sample_div
    _journal_ = JournalService.get_journal(_journal.journal_id)
    assert _journal_ == _journal
    with pytest.raises(NotExistError):
        # original journal should be deleted
        JournalService.get_journal(_jrn_id)
    
    # test delete div
    with pytest.raises(NotExistError):
        SharesService.delete_div('random-div')
    SharesService.delete_div(sample_div.div_id)
    with pytest.raises(NotExistError):
        SharesService.get_div_journal(sample_div.div_id)
from datetime import date
from unittest import mock
import pytest
from src.app.model.accounts import Account, Chart
from src.app.model.enums import AcctType
from src.app.model.exceptions import NotExistError, AlreadyExistError, FKNotExistError

@mock.patch("src.app.dao.connection.get_engine")
def test_journal(mock_engine, engine_with_sample_choa, sample_journal_meal):
    mock_engine.return_value = engine_with_sample_choa
    
    from src.app.dao.journal import journalDao
    
    # test add journal
    journalDao.add(sample_journal_meal)
    # test add journal one more time
    with pytest.raises(AlreadyExistError):
        journalDao.add(sample_journal_meal)
    
    
    # test get journal
    _journal = journalDao.get(sample_journal_meal.journal_id)
    assert _journal == sample_journal_meal
    
    # test remove journal
    journalDao.remove(sample_journal_meal.journal_id)
    with pytest.raises(NotExistError):
        journalDao.get(sample_journal_meal.journal_id)
        
    # test add journal entry with accounts not exist
    _copy_journal = sample_journal_meal.model_copy(deep=True)
    _copy_journal.entries[0].acct = Account(
        acct_id='acct-fake',
        acct_name='Fake Expense',
        acct_type=AcctType.EXP,
        chart=Chart(name='fake-chart', acct_type=AcctType.EXP)
    )
    with pytest.raises(FKNotExistError):
        journalDao.add(_copy_journal)
    # assert if journal is also removed
    with pytest.raises(NotExistError):
        journalDao.get(_copy_journal.journal_id)
        
    # test if can update the modified journal
    sample_journal_meal.jrn_date = date(2024, 1, 2)
    sample_journal_meal.entries[1].description = 'Unhappy Tip'
    journalDao.update(sample_journal_meal)
    _sample_jrn = journalDao.get(sample_journal_meal.journal_id)
    assert _sample_jrn.jrn_date == date(2024, 1, 2)
    # find the 1st entry
    _entry = list(filter(
        lambda e: e.entry_id == sample_journal_meal.entries[1].entry_id,
        _sample_jrn.entries
    ))[0]
    assert _entry.description == 'Unhappy Tip'
    
    # remove journal
    journalDao.remove(sample_journal_meal.journal_id)
    with pytest.raises(NotExistError):
        journalDao.get(sample_journal_meal.journal_id)
    
    
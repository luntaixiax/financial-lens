from datetime import date
from unittest import mock
import pytest
from src.app.model.accounts import Account, Chart
from src.app.model.enums import AcctType, JournalSrc
from src.app.model.exceptions import NotExistError, AlreadyExistError, FKNotExistError

def test_journal(session_with_sample_choa, sample_journal_meal, test_journal_dao):
    
    # test add journal
    test_journal_dao.add(sample_journal_meal)
    # test add journal one more time
    with pytest.raises(AlreadyExistError):
        test_journal_dao.add(sample_journal_meal)
    
    # test get journal
    _journal = test_journal_dao.get(sample_journal_meal.journal_id)
    assert _journal == sample_journal_meal
    
    # test list
    jb, _ = test_journal_dao.list_journal()
    assert len(jb) == 1
    jb, _ = test_journal_dao.list_journal(jrn_src = JournalSrc.MANUAL)
    assert len(jb) == 1
    jb, _ = test_journal_dao.list_journal(num_entries=4)
    assert len(jb) == 1
    jb, _ = test_journal_dao.list_journal(acct_ids=['acct-meal'])
    assert len(jb) == 1
    jb, _ = test_journal_dao.list_journal(acct_names=['acct-random'])
    assert len(jb) == 0
    
    # test flow
    acct_flow_agg = test_journal_dao.sum_acct_flow(
        'acct-bank', 
        start_dt=date(2024, 1, 1), 
        end_dt=date(2024, 12, 31)
    )
    flow_agg = test_journal_dao.agg_accts_flow(
        start_dt=date(2024, 1, 1), 
        end_dt=date(2024, 12, 31)
    )
    # test list entry
    entries = test_journal_dao.list_entry_by_acct(
        acct_id = 'acct-bank'
    )
    
    # test remove journal
    test_journal_dao.remove(sample_journal_meal.journal_id)
    with pytest.raises(NotExistError):
        test_journal_dao.get(sample_journal_meal.journal_id)
        
    # test add journal entry with accounts not exist
    _copy_journal = sample_journal_meal.model_copy(deep=True)
    _copy_journal.entries[0].acct = Account(
        acct_id='acct-fake',
        acct_name='Fake Expense',
        acct_type=AcctType.EXP,
        currency=None,
        chart=Chart(name='fake-chart', acct_type=AcctType.EXP)
    )
    with pytest.raises(FKNotExistError):
        test_journal_dao.add(_copy_journal)
    # assert if journal is also removed
    with pytest.raises(NotExistError):
        test_journal_dao.get(_copy_journal.journal_id)
        
    # test if can update the modified journal
    test_journal_dao.add(sample_journal_meal) # add back meal
    sample_journal_meal.jrn_date = date(2024, 1, 2)
    sample_journal_meal.entries[1].description = 'Unhappy Tip'
    test_journal_dao.update(sample_journal_meal)
    _sample_jrn = test_journal_dao.get(sample_journal_meal.journal_id)
    assert _sample_jrn.jrn_date == date(2024, 1, 2)
    # find the 1st entry
    _entry = list(filter(
        lambda e: e.entry_id == sample_journal_meal.entries[1].entry_id,
        _sample_jrn.entries
    ))[0]
    assert _entry.description == 'Unhappy Tip'
    
    
    # remove journal
    test_journal_dao.remove(sample_journal_meal.journal_id)
    with pytest.raises(NotExistError):
        test_journal_dao.get(sample_journal_meal.journal_id)
    
    
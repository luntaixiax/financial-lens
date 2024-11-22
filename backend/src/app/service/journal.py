
from src.app.dao.journal import journalDao
from src.app.model.journal import Journal


class JournalService:
        
    @classmethod
    def save_journal(cls, journal: Journal):
        # add journal and entries
        journalDao.add(journal)
        
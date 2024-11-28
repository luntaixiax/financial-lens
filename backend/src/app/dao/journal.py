import logging
from sqlmodel import Session, select, delete
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.dao.orm import EntryORM, JournalORM, infer_integrity_error
from src.app.model.journal import Entry, Journal
from src.app.dao.accounts import acctDao, chartOfAcctDao
from src.app.dao.connection import get_engine
from src.app.model.exceptions import AlreadyExistError, NotExistError

class journalDao:
    @classmethod
    def fromEntry(cls, journal_id: str, entry: Entry) -> EntryORM:
        return EntryORM(
            entry_id=entry.entry_id,
            journal_id=journal_id,
            entry_type=entry.entry_type,
            acct_id=entry.acct.acct_id,
            cur_incexp=entry.cur_incexp,
            amount=entry.amount,
            amount_base=entry.amount_base,
            description=entry.description,
        )
        
    @classmethod
    def toEntry(cls, entry_orm: EntryORM) -> Entry:
        
        # TODO: optimize it to not use acctDao
        chart_id = acctDao.get_chart_id_by_acct(entry_orm.acct_id)
        chart = chartOfAcctDao.get_chart(chart_id)
        acct = acctDao.get(entry_orm.acct_id, chart)
        return Entry(
            entry_id=entry_orm.entry_id,
            entry_type=entry_orm.entry_type,
            acct=acct,
            cur_incexp=entry_orm.cur_incexp,
            amount=entry_orm.amount,
            amount_base=entry_orm.amount_base,
            description=entry_orm.description,
        )
        
    @classmethod
    def fromJournal(cls, journal: Journal) -> JournalORM:
        return JournalORM(
            journal_id=journal.journal_id,
            jrn_date=journal.jrn_date,
            is_manual=journal.is_manual,
            note=journal.note
        )
        
    @classmethod
    def toJournal(cls, journal_orm: JournalORM, entry_orms: list[EntryORM]) -> Journal:
        return Journal(
            journal_id=journal_orm.journal_id,
            jrn_date=journal_orm.jrn_date,
            entries=[
                cls.toEntry(entry_orm) for entry_orm in entry_orms
            ],
            is_manual=journal_orm.is_manual,
            note=journal_orm.note,
        )
        
    @classmethod
    def add(cls, journal: Journal):
        with Session(get_engine()) as s:
            # add journal first
            journal_orm = cls.fromJournal(journal)
            s.add(journal_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise AlreadyExistError(details=str(e))
            else:
                logging.info(f"Added {journal_orm} to Journal table")
            
            # add individual entries
            for entry in journal.entries:
                entry_orm = cls.fromEntry(
                    journal_id=journal.journal_id,
                    entry=entry
                )
                s.add(entry_orm)
            try:
                s.commit()
            except IntegrityError as e:
                s.rollback()
                # remove journal as well
                s.delete(journal_orm)
                s.commit()
                raise infer_integrity_error(e, during_creation=True)
            else:
                logging.info(f"Added {entry_orm} to Entry table")
    
    @classmethod
    def get(cls, journal_id: str) -> Journal:
        with Session(get_engine()) as s:
            # get entries
            sql = select(EntryORM).where(
                EntryORM.journal_id == journal_id
            )
            try:
                entry_orms = s.exec(sql).all()
            except NoResultFound as e:
                raise NotExistError(details=str(e))

            # get journal
            sql = select(JournalORM).where(
                JournalORM.journal_id == journal_id
            )
            try:
                journal_orm = s.exec(sql).one() # get the journal
            except NoResultFound as e:
                raise NotExistError(details=str(e))
            
            journal = cls.toJournal(
                journal_orm=journal_orm,
                entry_orms=entry_orms
            )
        return journal
    
    @classmethod
    def remove(cls, journal_id: str):
        with Session(get_engine()) as s:
            # remove entries
            sql = delete(EntryORM).where(
                EntryORM.journal_id == journal_id
            )
            s.exec(sql)
            # remove journal
            sql = delete(JournalORM).where(
                JournalORM.journal_id == journal_id
            )
            s.exec(sql)
            
            # commit at same time
            s.commit()
            logging.info(f"deleted journal and entries for {journal_id}")
            
    @classmethod
    def update(cls, journal: Journal):
        # delete the given journal and create new one
        cls.remove(journal_id = journal.journal_id)
        # add the new one
        cls.add(journal)
        logging.info(f"updated {journal} by removing existing one and added new one")
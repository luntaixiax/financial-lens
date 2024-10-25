

import logging
from sqlmodel import Session, select, delete
from src.app.dao.orm import EntryORM, JournalORM
from src.app.model.journal import Entry, Journal
from src.app.dao.accounts import acctDao
from src.app.dao.connection import engine

class journalDao:
    @classmethod
    def fromEntry(cls, journal_id: str, entry: Entry) -> EntryORM:
        return EntryORM(
            journal_id=journal_id,
            entry_type=entry.entry_type,
            acct_id=entry.acct.acct_id,
            amount=entry.amount,
            amount_base=entry.amount_base,
            description=entry.description,
        )
        
    @classmethod
    def toEntry(cls, entry_orm: EntryORM) -> Entry:
        acct = acctDao.get(acct_id=entry_orm.acct_id)
        return Entry(
            entry_type=entry_orm.entry_type,
            acct=acct,
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
        with Session(engine) as s:
            # add journal first
            journal_orm = cls.fromJournal(journal)
            s.add(journal_orm)
            s.commit()
            logging.info(f"Added {journal_orm} to Journal table")
            
            # add individual entries
            for entry in journal.entries:
                entry_orm = cls.fromEntry(
                    journal_id=journal.journal_id,
                    entry=entry
                )
                s.add(entry_orm)
                s.commit()
                logging.info(f"Added {entry_orm} to Entry table")
    
    @classmethod
    def get(cls, journal_id: str) -> Journal:
        with Session(engine) as s:
            # get entries
            sql = select(EntryORM).where(
                EntryORM.journal_id == journal_id
            )
            entry_orms = s.exec(sql).all()

            # get journal
            sql = select(JournalORM).where(
                JournalORM.journal_id == journal_id
            )
            journal_orm = s.exec(sql).one() # get the journal
            
            journal = cls.toJournal(
                journal_orm=journal_orm,
                entry_orms=entry_orms
            )
        return journal
    
    @classmethod
    def remove(cls, journal_id: str):
        with Session(engine) as s:
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
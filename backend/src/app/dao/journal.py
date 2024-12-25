from datetime import date
import logging
from sqlmodel import Session, select, delete, case, func as f
from sqlalchemy.exc import NoResultFound, IntegrityError
from src.app.model.enums import EntryType, JournalSrc
from src.app.dao.orm import AcctORM, EntryORM, JournalORM, infer_integrity_error
from src.app.model.journal import _JournalBrief, Entry, Journal
from src.app.dao.accounts import acctDao, chartOfAcctDao
from src.app.dao.connection import get_engine
from src.app.model.exceptions import AlreadyExistError, FKNoDeleteUpdateError, NotExistError

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
            jrn_src=journal.jrn_src,
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
            jrn_src=journal_orm.jrn_src,
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
            sql = select(JournalORM).where(
                JournalORM.journal_id == journal_id
            )
            j = s.exec(sql).one()
            
            # commit at same time
            try:
                s.delete(j)
                s.commit()
            except IntegrityError as e:
                s.rollback()
                raise infer_integrity_error(e, during_creation=False)
            logging.info(f"deleted journal and entries for {journal_id}")
            
    @classmethod
    def update(cls, journal: Journal):
        # delete the given journal and create new one
        cls.remove(journal_id = journal.journal_id)
        # add the new one
        cls.add(journal)
        logging.info(f"updated {journal} by removing existing one and added new one")
        
    @classmethod
    def list(
        cls,
        limit: int = 50,
        offset: int = 0,
        jrn_ids: list[str] | None = None,
        jrn_src: JournalSrc | None = None, 
        min_dt: date = date(1970, 1, 1), 
        max_dt: date = date(2099, 12, 31),
        acct_ids: list[str] | None = None,
        acct_names: list[str] | None = None, 
        note_keyword: str = '', 
        min_amount: float = -999999999,
        max_amount: float = 999999999,
        num_entries: int | None = None
    ) -> list[_JournalBrief]:
        with Session(get_engine()) as s:
            
            acct_case_when = []
            if acct_ids is not None:
                acct_case_when.append(
                    f.max(
                        case(
                            (AcctORM.acct_id.in_(acct_ids), 1),
                            else_=0
                        )
                    ).label('contains_acct_id'),
                )
            if acct_names is not None:
                acct_case_when.append(
                    f.max(
                        case(
                            (AcctORM.acct_name.in_(acct_names), 1),
                            else_=0
                        )
                    ).label('contains_acct_name')
                )
            
            entry_agg = (
                select(
                    EntryORM.journal_id,
                    f.group_concat(AcctORM.acct_name).label('acct_name_strs'),
                    f.sum(
                        case(
                            (EntryORM.entry_type == EntryType.DEBIT, EntryORM.amount_base), 
                            else_ = 0
                        )
                    ).label('total_base_amount'), 
                    f.count(EntryORM.entry_id).label('num_entries'),
                    *acct_case_when
                )
                .join(
                    AcctORM,
                    onclause=EntryORM.acct_id == AcctORM.acct_id,
                    isouter=True  # left join
                )
                .group_by(EntryORM.journal_id)
                .subquery()
            )
            
            # join the two
            jrn_filters = [
                JournalORM.jrn_date.between(min_dt, max_dt), 
                JournalORM.note.contains(note_keyword),
                entry_agg.c.total_base_amount.between(min_amount, max_amount)
            ]
            if jrn_ids is not None:
                jrn_filters.append(JournalORM.journal_id.in_(jrn_ids))
            if jrn_src is not None:
                jrn_filters.append(JournalORM.jrn_src == jrn_src)
            if num_entries is not None:
                jrn_filters.append(entry_agg.c.num_entries == num_entries)
            if acct_ids is not None:
                jrn_filters.append(entry_agg.c.contains_acct_id == 1)
            if acct_names is not None:
                jrn_filters.append(entry_agg.c.contains_acct_name == 1)
            
            sql = (
                select(
                    JournalORM.journal_id, 
                    JournalORM.jrn_date, 
                    JournalORM.jrn_src,
                    entry_agg.c.acct_name_strs,
                    entry_agg.c.num_entries,
                    entry_agg.c.total_base_amount,
                    JournalORM.note
                )
                .where(*jrn_filters)
                .join(
                    entry_agg,
                    onclause=JournalORM.journal_id == entry_agg.c.journal_id,
                    isouter=False
                )
                .order_by(JournalORM.jrn_date.desc(), JournalORM.journal_id)
                .offset(offset)
                .limit(limit)
            )
            
            jrns = s.exec(sql).all()
            
        return [
            _JournalBrief(
                journal_id=jrn.journal_id,
                jrn_date=jrn.jrn_date,
                jrn_src=jrn.jrn_src,
                acct_name_strs=jrn.acct_name_strs,
                num_entries=jrn.num_entries,
                total_base_amount=jrn.total_base_amount,
                note=jrn.note
            ) 
            for jrn in jrns
        ]
        
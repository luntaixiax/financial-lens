import tempfile
from pathlib import Path
import sqlalchemy
from sqlalchemy import MetaData, JSON, column, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlite3 import Connection as SQLite3Connection
from sqlmodel import Session, select, delete
from src.app.dao.orm import get_class_by_tablename, SQLModelWithSort
from src.app.utils.tools import get_file_root
from src.app.dao.connection import get_storage_fs, get_engine

def drop_tables(engine: Engine):
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    # respect foreign key constraints so sort the tables
    with Session(engine) as s:
        src_metadata = MetaData()
        src_metadata.reflect(bind=engine)
    
        for tbl in reversed(metadata.sorted_tables):
            table_cls = get_class_by_tablename(tbl.name)
            table_cls.__table__.drop(bind=engine)
            
def migrate_database(src_engine: Engine, tgt_engine: Engine):

    src_metadata = MetaData()
    src_metadata.reflect(bind=src_engine)
    
    # create table schema in target engine
    SQLModelWithSort.metadata.create_all(tgt_engine)
    
    # open connection to backup database
    with Session(tgt_engine) as s:
        
        tgt_metadata = MetaData()
        tgt_metadata.reflect(bind=tgt_engine)

        for table in tgt_metadata.sorted_tables:
            stmt = table.insert()
            # read objects from file system
            with Session(src_engine) as e:            
                src_table = src_metadata.tables[table.name]
                
                # select all rows
                rows = e.exec(src_table.select())
                
                # need to sort the results to insert, otherwise some FK may be violated
                table_cls = get_class_by_tablename(table.name)
                rows = table_cls.sort_for_backup(rows)
                
                for index, row in enumerate(rows):
                    s.exec(stmt.values(row))
                    s.commit()

class backupDao:
    
    @classmethod
    def get_backup_folder_path(cls, backup_id: str) -> str:
        return (Path(get_file_root('backup')) / backup_id).as_posix()
    
    @classmethod
    def get_backup_db_fname(cls) -> str:
        return 'backup-data.db'
    
    @classmethod
    def list_backup_ids(cls) -> list[str]:
        bk_fs = get_storage_fs('backup')
        file_root = Path(get_file_root('backup'))
        files = bk_fs.ls(file_root, detail=True)
        ids = []
        for file in files:
            if file['type'] == 'directory':
                ids.append(file['Key'].split('/')[-1])
        return ids
    
    @classmethod
    def backup_files(cls, backup_id: str):
        # backup all files, e.g., receipts
        # create backup folder
        bk_root = Path(cls.get_backup_folder_path(backup_id)) / 'bk_files'
        bk_fs = get_storage_fs('backup')
        bk_fs.mkdirs(bk_root, exist_ok=True)
        
        fs = get_storage_fs('files')
        
        with tempfile.TemporaryDirectory() as tmpdirname:
            # download files from fs to local temp dir first
            fs.get(
                rpath=get_file_root('files'),
                lpath=Path(tmpdirname) / 'bk_files',
                recursive=True
            )
            
            # upload files to backup folder
            bk_fs.put(
                lpath=Path(tmpdirname) / 'bk_files',
                rpath=bk_root.as_posix(),
                recursive=True
            )
    
    @classmethod
    def backup_database(cls, backup_id: str):
        # read all data from src database and save to a sqlite database as backup
        
        # create backup folder
        bk_fs = get_storage_fs('backup')
        bk_fs.mkdirs(cls.get_backup_folder_path(backup_id), exist_ok=True)
        
        with tempfile.TemporaryDirectory() as tmpdirname:
            
            # create sqlite3 database
            @event.listens_for(Engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, connection_record):
                if isinstance(dbapi_connection, SQLite3Connection):
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON;")
                    cursor.close()
            
            # setup sqlite database with all tables
            cur_path = Path(tmpdirname) / cls.get_backup_db_fname()
            tgt_engine = sqlalchemy.create_engine(f'sqlite:///{cur_path.as_posix()}')
                            
            migrate_database(
                src_engine = get_engine(),
                tgt_engine = tgt_engine
            )
            
            # upload backup file to backup server
            bk_fs.put_file(
                lpath=cur_path,
                rpath=Path(cls.get_backup_folder_path(backup_id)) / cls.get_backup_db_fname()
            )
            
    @classmethod
    def restore_files(cls, backup_id: str):
        # read all files (e.g., receipts) from backup storage and save/overwrite current fs
        bk_root = Path(cls.get_backup_folder_path(backup_id)) / 'bk_files'
        bk_fs = get_storage_fs('backup')
        
        fs = get_storage_fs('files')
        
        with tempfile.TemporaryDirectory() as tmpdirname:
            
            # download from backup storage to local first
            bk_fs.get(
                rpath=bk_root.as_posix(),
                lpath=Path(tmpdirname) / 'bk_files',
                recursive=True
            )
            
            # upload to current storage
            fs.put(
                lpath=Path(tmpdirname) / 'bk_files',
                rpath=get_file_root('files'),
                recursive=True
            )
            
            
    @classmethod
    def restore_database(cls, backup_id: str):
        # read all data from backup sqlite database (source) and overwrite the target database
        
        bk_fs = get_storage_fs('backup')
        
        with tempfile.TemporaryDirectory() as tmpdirname:
            cur_path = Path(tmpdirname) / cls.get_backup_db_fname()
            # download the file to local first
            bk_fs.get_file(
                rpath=Path(cls.get_backup_folder_path(backup_id)) / cls.get_backup_db_fname(),
                lpath=cur_path
            )
            
            src_engine = sqlalchemy.create_engine(f'sqlite:///{cur_path.as_posix()}')
            tgt_engine = get_engine()
            
            # drop all existing tables
            drop_tables(tgt_engine)
            
            # copy data from source to target
            migrate_database(
                src_engine = src_engine,
                tgt_engine = tgt_engine
            )
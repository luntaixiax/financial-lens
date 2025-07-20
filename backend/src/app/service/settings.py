from typing import Any, Tuple
from datetime import datetime
from src.app.model.enums import CurType
from src.app.model.entity import Address, Contact
from src.app.dao.config import configDao
from src.app.dao.backup import backupDao
from src.app.model.exceptions import NotExistError, OpNotPermittedError
from src.app.service.files import FileService
from src.app.utils.tools import get_secret
from src.app.model.misc import FileWrapper

class ConfigService:
    LOGO_FILE_ID = 'settings-logo'
    
    def __init__(self, file_service: FileService, config_dao: configDao):
        self.file_service = file_service
        self.config_dao = config_dao
        
    def create_sample(self):
        # set base settings
        self.set_base_currency(CurType.CAD)
        self.set_default_tax_rate(0.13)
        self.set_par_share_price(0.01)
        # set company
        self.set_company(
            name='LTX FinLens Inc.', 
            contact=Contact(
                name='Sample Contact', 
                email='sample@example.com', 
                phone='123-456-7890',
                address=Address(
                    address1='123 Main St',
                    address2=None,
                    suite_no=100,
                    city='Toronto',
                    state='Ontario',
                    country='Canada',
                    postal_code='XYZ ABC'
                )
            )
        )
    
    def set_logo(self, content: str):
        logo = FileWrapper(
            file_id=self.LOGO_FILE_ID,
            filename='SETTINGS_LOGO.PNG', 
            content=content
        )
        try:
            self.file_service.get_file(self.LOGO_FILE_ID)
        except NotExistError:
            self.file_service.add_file(logo)
        else:
            # if exist, remove current one and replace with new one
            self.file_service.delete_file(self.LOGO_FILE_ID)
            self.file_service.add_file(logo)
        
    def get_logo(self) -> FileWrapper:
        try:
            logo = self.file_service.get_file(self.LOGO_FILE_ID)
        except NotExistError as e:
            raise NotExistError(message="Logo not set yet! " + e.message, details=e.details)
        return logo
    
    def get_config(self) -> dict[str, Any]:
        return self.config_dao.get_config()
    
    def get_config_value(self, key: str) -> Any:
        return self.config_dao.get_config_value(key)
    
    def set_config_value(self, key: str, value: Any):
        self.config_dao.set_config_value(key, value)
        
    def get_company(self) -> Tuple[str, Contact]:
        company = self.get_config_value('company')
        if company is None:
            raise NotExistError(message="Your Company profile not set yet")
        
        name = company['name']
        contact = Contact.model_validate(company['contact'])
        return name, contact
    
    def set_company(self, name: str, contact: Contact):
        conf = {
            'name' : name,
            'contact': contact.model_dump()
        }
        self.set_config_value('company', conf)
        
    def is_setup(self) -> bool:
        # see if the account has setup yet
        # if yes, no change to base currency
        # if no, should display button to initialize the settings (bootstrapping)
        return self.get_config_value('is_setup') or False
    
    def confirm_setup(self):
        self.set_config_value('is_setup', True)
    
    def get_base_currency(self) -> CurType:
        base_currency = self.get_config_value('base_currency')
        if base_currency is None:
            raise NotExistError("Base Currency not set yet")
        return CurType(base_currency)
    
    def set_base_currency(self, base_currency: CurType):
        try:
            base_currency = self.get_base_currency()
        except NotExistError:
            self.set_config_value('base_currency', base_currency)
        else:
            if self.is_setup():
                raise OpNotPermittedError(f"Account already setup, cannot change base curreny")
            else:
                # still want to set if setup is not finalized yet
                self.set_config_value('base_currency', base_currency)
                
    def get_default_tax_rate(self) -> float:
        default_tax_rate = self.get_config_value('default_tax_rate')
        if default_tax_rate is None:
            raise NotExistError("Default Tax rate not set yet")
        return default_tax_rate
    
    def set_default_tax_rate(self, default_tax_rate: float):
        self.set_config_value('default_tax_rate', default_tax_rate)
        
    def get_par_share_price(self) -> float:
        par_share_price = self.get_config_value('par_share_price')
        if par_share_price is None:
            raise NotExistError("Par share price not set yet")
        return par_share_price
    
    def set_par_share_price(self, par_share_price: float):
        try:
            par_share_price = self.get_par_share_price()
        except NotExistError:
            self.set_config_value('par_share_price', par_share_price)
        else:
            if self.is_setup():
                raise OpNotPermittedError(f"Account already setup, cannot change par share price")
            else:
                # still want to set if setup is not finalized yet
                self.set_config_value('par_share_price', par_share_price)
        
    def get_static_server_path(self) -> str:
        secret = get_secret()['static_server']
        return f"http://{secret['hostname']}:{secret['port']}"
    
    
class BackupService:
    
    def __init__(self, backup_dao: backupDao):
        self.backup_dao = backup_dao
    
    def list_backup_ids(self) -> list[str]:
        return self.backup_dao.list_backup_ids()
    
    def backup(self, backup_id: str | None) -> str:
        # use current timestamp if not given backup id
        backup_id = backup_id or datetime.now().strftime('%Y%m%dT%H%M%S')
        
        # backup database
        self.backup_dao.backup_database(backup_id)
        # backup files
        self.backup_dao.backup_files(backup_id)
        
        return backup_id
    
    def restore(self, backup_id: str):
        
        # restore files
        self.backup_dao.restore_files(backup_id)
        # restore database
        self.backup_dao.restore_database(backup_id)
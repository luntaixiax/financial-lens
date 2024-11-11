
from functools import partial
from pydantic import BaseModel, ConfigDict, Field
from src.app.model.enums import BankAcctType, CurType
from src.app.utils.tools import id_generator
from src.app.utils.base import EnhancedBaseModel

class BankAcct(EnhancedBaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
    bank_acct_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='bank-',
            length=8,
        ),
        frozen=True,
    )
    bank_acct_number: str
    bank_acct_name: str
    bank_acct_type: BankAcctType = Field(
        frozen=True
    )
    currency: CurType = Field(
        frozen=True
    )
    is_business: bool = Field(False) # if True, will record in accts
    extra_info: dict | None = Field(None)
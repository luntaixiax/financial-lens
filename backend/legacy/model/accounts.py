from typing import List, Dict, Union, Optional, ClassVar
from dataclasses import dataclass
from legacy.model.enums import CurType, BalShType, IncExpType

@dataclass(kw_only=True)
class BaseAcct:
    acct_id: str = None
    acct_name: str
    entity_id: str
    
@dataclass(kw_only=True)
class BalSh(BaseAcct):
    # balance sheet item
    _type: ClassVar[str] = 'BalSh'
    acct_type: BalShType
    currency: CurType
    accrual: bool = False # whether AR/AP

@dataclass(kw_only=True)
class IncExp(BaseAcct):
    # income/expense item
    _type: ClassVar[str] = 'IncExp'
    acct_type: IncExpType
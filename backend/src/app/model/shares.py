from datetime import date
from functools import partial
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field

from src.app.utils.base import EnhancedBaseModel
from src.app.model.enums import BankAcctType, CurType
from src.app.utils.tools import finround, id_generator, get_par_share_price

class StockIssue(EnhancedBaseModel):
    
    issue_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='issue-',
            length=8,
        ),
        frozen=True,
    )
    issue_dt: date
    is_reissue: bool = Field(
        default=False,
        description="whether it is reissue of treasury stock"
        # need to check if num_shares <= total repurchased shares
        # use repurchase price instead of par_price
    )
    num_shares: float
    issue_price: float = Field(
        description='Issue price of new stock, expressed in base currency'
    )
    cost_price: float = Field(
        default_factory=get_par_share_price,
        description='Par price of the new stock issue for new issue, and cost of repurchase for reissue'
    )
    debit_acct_id: str = Field(
        description='Which account receives the new issue, typically asset or expense'
    )
    issue_amt: float = Field(
        description='dollar amount of the new issue, expressed in debit account currency'
    )
    
    @computed_field()
    def issue_amt_base(self) -> float:
        # base currency
        return finround(self.issue_price * self.num_shares)
    
    @computed_field()
    def issue_premium_base(self) -> float:
        # only applies for new issue, not repurchase reissue
        # base currency
        return finround((self.issue_price - self.par_price) * self.num_shares)


class StockRepurchase(EnhancedBaseModel):
    
    repur_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='repur-',
            length=8,
        ),
        frozen=True,
    )
    repurchase_dt: date
    num_shares: float
    repur_price: float = Field(
        description='Repurchase price of own stock, expressed in base currency'
    )
    credit_acct_id: str = Field(
        description='Which account pays the repurchase, typically asset'
    )
    repur_amt: float = Field(
        description='dollar amount of the repurchase, expressed in credit account currency'
    )
    
    @computed_field()
    def repurchase_amt_base(self) -> float:
        # base currency
        return finround(self.repur_price * self.num_shares)

    
class Dividend(EnhancedBaseModel):
    
    div_id: str = Field(
        default_factory=partial(
            id_generator,
            prefix='div-',
            length=8,
        ),
        frozen=True,
    )
    div_dt: date
    div_amt: float = Field(
        description='Amount of the dividend, expressed in credit account currency'
    )
    credit_acct_id: str = Field(
        description='Which account pays the dividend, typically asset'
    )
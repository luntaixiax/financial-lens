from enum import Enum, unique
from functools import lru_cache


@unique
class SystemAcctNumber(str, Enum):
    # accounts that are not meant to be delete by user, and created at init
    # the service module may use it directly
    INPUT_TAX = "acct-ipt"
    OUTPUT_TAX = "acct-opt"
    ACCT_RECEIV = "acct-ar"
    ACCT_PAYAB = "acct-ap"
    CONTR_CAP = "acct-cc"
    ADD_PAID_IN = "acct-api"
    RETAIN_EARN = "acct-re"
    OTH_COMP_INC = "acct-oci"
    SHIP_CHARGE = "acct-spc"
    DISCOUNT = "acct-disc"
    FX_GAIN = "acct-fxgain"
    BANK_FEE = "acct-bnkfee"
    
    @classmethod
    @lru_cache
    def list_(cls) -> list[str]:
        return list(map(lambda c: c.value, cls))


@unique
class SystemChartOfAcctNumber(str, Enum):
    # chart of account id that are not meant to be delete by user, 
    # and created at init, the service module may use it directly
    TOTAL_ASSET = 'choa-totass'
    CUR_ASSET = 'choa-curass'
    BANK_ASSET = 'choa-bnkass'
    NONCUR_ASSET = 'choa-ncurass'
    TOTAL_LIB = 'choa-totlib'
    CUR_LIB = 'choa-curlib'
    BANK_LIB = 'choa-bnklib'
    NONCUR_LIB = 'choa-ncurlib'
    TOTAL_EQU = 'choa-totequ'
    TOTAL_INC = 'choa-totinc'
    TOTAL_EXP = 'choa-totexp'
    
    @classmethod
    @lru_cache
    def list_(cls) -> list[str]:
        return list(map(lambda c: c.value, cls))

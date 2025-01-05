import streamlit as st
from utils.apis import get_account, get_all_accounts
from utils.tools import DropdownSelect
from utils.enums import CurType, EntryType, AcctType

all_accts = get_all_accounts()
acct_options = [
    {
        'acct_id': a['acct_id'],
        'acct_name': a['acct_name'],
        'acct_type': AcctType(a['acct_type']).name,
        'currency': CurType(a['currency']).name if a['currency'] else '-'
    }
    for a in all_accts
]
dds_accts = DropdownSelect(
    briefs=acct_options,
    include_null=False,
    id_key='acct_id',
    display_keys=['acct_name', 'currency', 'acct_type']
)

acct_name = st.selectbox(
    label='Select Account',
    options=dds_accts.options,
    key='acct_name'
)
acct_id = dds_accts.get_id(acct_name)
acct = get_account(acct_id)
st.json(acct)

if acct['acct_type'] in (1, 2, 3):
    print('balance sheet item, display balance and everything expressed in raw currency')
    
else:
    print('income statement item, display period cumulative total (MTD/YTD), everything expressed in base currency')
import streamlit as st

pages = {
    "Test" : [
        st.Page("sections/test_api.py", title="Test API"),
    ],
    "Accountant": [
        st.Page("sections/chart_of_accounts.py", title="Chart of Accounts", icon='📚'),
        st.Page("sections/journal.py", title="Journal Entry", icon='✍🏼'),
        st.Page("sections/acct_flows.py", title="Account Transactions", icon='📑'),
    ],
    "Entity": [
        st.Page("sections/contact.py", title="Manage Contact", icon='📞'),
        st.Page("sections/customer.py", title="Manage Customer", icon='👨🏻‍💼'),
        st.Page("sections/supplier.py", title="Manage Supplier", icon='👨🏻‍🔧'),
        st.Page("sections/item.py", title="Manage Item", icon='📦'),
    ],
    "Transaction": [
        st.Page("sections/sales.py", title="Manage Sales", icon='💸'),
        st.Page("sections/purchase.py", title="Manage Purchase", icon='🛒'),
        st.Page("sections/expense.py", title="Manage Expense", icon='✈️'),
    ],
}

pg = st.navigation(pages)
pg.run()
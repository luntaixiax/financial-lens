import streamlit as st

pages = {
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
    "Sales": [
        st.Page("sections/sales_overview.py", title="Sales Overview", icon='💸'),
        st.Page("sections/sales_invoice.py", title="Manage Invoice", icon='🛒'),
        st.Page("sections/sales_payment.py", title="Manage Payment", icon='✈️'),
    ],
}

pg = st.navigation(pages)
pg.run()
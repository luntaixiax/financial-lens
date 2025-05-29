import streamlit as st

pages = {
    "Settings": [
        st.Page("sections/settings.py", title="Manage Your Company", icon='⚙️'),
        st.Page("sections/db_management.py", title="Manage Data", icon='⛅'),
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
    "Sales": [
        st.Page("sections/sales_overview.py", title="Sales Overview", icon='📊'),
        st.Page("sections/sales_invoice.py", title="Manage Invoice", icon='💶'),
        st.Page("sections/sales_payment.py", title="Manage Payment", icon='💸'),
    ],
    "Expense": [
        st.Page("sections/expense_overview.py", title="Expense Overview", icon='📊'),
        st.Page("sections/expense.py", title="Manage Expense", icon='🛒'),
    ],
    "Property": [
        st.Page("sections/property.py", title="Buy Property", icon='🏠'),
        st.Page("sections/property_trans.py", title="Manage Property", icon='🚧'),
    ],
    "Reporting": [
        st.Page("sections/balance_sheet.py", title="Balance Sheet", icon='⚖️'),
        st.Page("sections/income_statement.py", title="Income Statement", icon='💰'),
    ]
}

pg = st.navigation(pages)
pg.run()
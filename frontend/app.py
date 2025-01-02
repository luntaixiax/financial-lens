import streamlit as st

pages = {
    "Test" : [
        st.Page("sections/test_api.py", title="Test API"),
    ],
    "Entity": [
        st.Page("sections/contact.py", title="Manage Contact"),
        st.Page("sections/customer.py", title="Manage Customer"),
        st.Page("sections/supplier.py", title="Manage Supplier"),
    ],
    "Chart of Accounts": [
        st.Page("sections/chart.py", title="Manage Chart")
    ]
}

pg = st.navigation(pages)
pg.run()
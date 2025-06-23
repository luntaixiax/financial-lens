from functools import wraps
from datetime import datetime
import io
import streamlit as st
import streamlit_shadcn_ui as ui
from utils.tools import DropdownSelect
from utils.apis import backup, restore, list_backup_ids, get_comp_contact, get_logo, \
    get_batch_exp_excel_template, upload_batch_exp_excel

st.set_page_config(layout="centered")
with st.sidebar:
    comp_name, _ = get_comp_contact()
    
    st.markdown(f"Hello, :rainbow[**{comp_name}**]")
    st.logo(get_logo(), size='large')

st.subheader('Data Backup/Restore')
st.button(
    label='Backup Data',
    key='backup',
    type='primary',
    icon='💾',
    on_click=backup
)

backup_ids = sorted(list_backup_ids(), reverse=True)

if len(backup_ids) > 0:
    backup_id = st.radio(
        label='Existing Backups',
        options=backup_ids,
        index=0,
        horizontal=True
    )

    st.button(
        label='Restore Data',
        key='restore',
        type='secondary',
        icon='📩',
        on_click=restore,
        kwargs=dict(
            backup_id=backup_id
        )
    )

else:
    st.warning("No backup found", icon='🥵')

st.subheader('Expense Batch Import')
exp_cols = st.columns(2)
with exp_cols[1]:
    st.download_button(
        label="Download Expense Template",
        data=get_batch_exp_excel_template(),
        file_name="expense_batch.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/download:",
        type='tertiary'
    )
    
with exp_cols[0]:
    st.info("Download the template and fill in **Expense** tab")
    
exp_batch = st.file_uploader(
    label='Upload Batch Expense',
    type=['xls', 'xlsx'],
    accept_multiple_files=False
)
st.warning("Make sure all the receipts with same filename in the Excel are uploaded to the storage server", icon='🙉')
if exp_batch is not None:
    st.button(
        label='Confirm Upload',
        on_click=upload_batch_exp_excel,
        args=(exp_batch,),
        type='primary',
        icon=":material/upload:",
    )
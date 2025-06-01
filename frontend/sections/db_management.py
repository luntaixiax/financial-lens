from functools import wraps
from datetime import datetime
import streamlit as st
import streamlit_shadcn_ui as ui
from utils.tools import DropdownSelect
from utils.apis import backup, restore, list_backup_ids


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
        horizontal=False
    )

    st.button(
        label='Backup Data',
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


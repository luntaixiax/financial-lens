import streamlit as st
import streamlit_shadcn_ui as ui
from utils.enums import EntityType, ItemType, UnitType, CurType, AcctType
from utils.tools import DropdownSelect
from utils.apis import list_item, get_item, delete_item, update_item, add_item, get_accounts_by_type

st.set_page_config(layout="centered")

def show_item(item: dict) -> dict:
    # convert enums
    r = {}
    r['Item ID'] = item['item_id']
    r['Name'] = item['name']
    r['Item Type'] = ItemType(item['item_type']).name
    r['Unit'] = UnitType(item['unit']).name
    r['Currency'] = CurType(item['currency']).name
    r['Unit Price'] = item['unit_price']
    return r

st.subheader('Manage Items')

tabs = st.tabs(['Items', 'Add/Edit Sales Item', 'Add/Edit Purchase Item'])
with tabs[0]:
    sales_items = list_item(entity_type=EntityType.CUSTOMER.value)
    purch_items = list_item(entity_type=EntityType.SUPPLIER.value)
    
    sales_item_display = [show_item(it) for it in sales_items]
    purch_item_display = [show_item(it) for it in purch_items]

    col_items = st.columns(2)
    with col_items[0]:
        ui.metric_card(
            title="# Sales Items", 
            content=len(sales_items), 
            description="available for sale", 
            key="card1"
        )
        
    with col_items[1]:
        ui.metric_card(
            title="# Purchase Items", 
            content=len(purch_items), 
            description="available for purchase", 
            key="card2"
        )
        
    st.caption('Sales Items')
    st.data_editor(
        data=sales_item_display, 
        use_container_width=True,
        hide_index=True,
        disabled=True
    )
    
    st.caption('Purchase Items')
    st.data_editor(
        data=purch_item_display, 
        use_container_width=True,
        hide_index=True,
        disabled=True
    )

item_types = DropdownSelect.from_enum(
    ItemType,
    include_null=False
)
cur_types = DropdownSelect.from_enum(
    CurType,
    include_null=False
)
unit_types = DropdownSelect.from_enum(
    UnitType,
    include_null=False
)


with tabs[1]:
    dds_sales = DropdownSelect(
        briefs=sales_item_display,
        include_null=False,
        id_key='Item ID',
        display_keys=['Name', 'Currency', 'Unit Price']
    )
    
    edit_cols = st.columns([1, 3])
    with edit_cols[0]:
        edit_mode = st.radio(
            label='Edit Mode',
            options=['Add', 'Edit'],
            #default='Add',
            #selection_mode ='single',
            key='radio1',
            horizontal=True,
        )
        
    if edit_mode == 'Edit':
        with edit_cols[1]:
            edit_sales = st.selectbox(
                label='👇 Select Item',
                options=dds_sales.options,
                index=0,
                key='sales-item'
            )
        # selected something, will load it from database first
        existing_sales_item_id = dds_sales.get_id(edit_sales)
        existing_sales_item = get_item(existing_sales_item_id)
    
    st.divider()
    
    if edit_mode == 'Edit':
        ui.badges(
            badge_list=[("Item ID", "default"), (existing_sales_item_id, "secondary")], 
            class_name="flex gap-2", 
            key="badges1"
        )
        
    sales_item_name = st.text_input(
        label="Name",
        value="" if edit_mode == 'Add' else existing_sales_item['name'],
        type='default', 
        placeholder="item name here", 
        key="sname"
    )
    
    item_cols = st.columns(2)
    with item_cols[0]:
        # item type
        if edit_mode == 'Add':
            sales_item_type = st.radio(
                label = '📦 Item Type',
                options=item_types.options,
                index=0,
                horizontal=True,
                key='radio2',
            )
        elif edit_mode == 'Edit':
            sales_item_type = st.radio(
                label = '📦 Item Type',
                options=item_types.options,
                index=item_types.get_idx_from_option(ItemType(existing_sales_item['item_type']).name),
                horizontal=True,
                key='radio3',
            )
    
    with item_cols[1]:
        # unit type
        if edit_mode == 'Add':
            sales_unit_type = st.selectbox(
                label = '⏱️ Unit Type',
                options=unit_types.options,
                index=0,
                key='sales-unit'
            )
        elif edit_mode == 'Edit':
            sales_unit_type = st.selectbox(
                label = '⏱️ Unit Type',
                options=unit_types.options,
                index=unit_types.get_idx_from_option(UnitType(existing_sales_item['unit']).name),
                key='sales-unit2'
            )
        
    with item_cols[0]:
        # currency type
        if edit_mode == 'Add':
            sales_cur = st.selectbox(
                label = '💲 Currency',
                options=cur_types.options,
                index=0,
                key='sales-cur'
            )
        elif edit_mode == 'Edit':
            sales_cur = st.selectbox(
                label = '💲 Currency',
                options=cur_types.options,
                index=cur_types.get_idx_from_option(CurType(existing_sales_item['currency']).name),
                key='sales-cur2'
            )
        
    with item_cols[1]:
        # unit price
        sales_unit_price = st.number_input(
            label='🏷️ Unit Price',
            value=0 if edit_mode == 'Add' else existing_sales_item['unit_price'],
            key='sales-price'
        )
        
    # default account (only income type)
    sales_accts = get_accounts_by_type(acct_type=AcctType.INC.value)
    dds_sales_accts = DropdownSelect(
        briefs=sales_accts,
        include_null=False,
        id_key='acct_id',
        display_keys=['acct_id', 'acct_name']
    )
    if edit_mode == 'Add':
        default_acct = st.selectbox(
            label = '📝 Default Account to record Sales',
            options=dds_sales_accts.options,
            index=0,
            key='sales-acct'
        )
    elif edit_mode == 'Edit':
        default_acct = st.selectbox(
            label = '📝 Default Account to record Sales',
            options=dds_sales_accts.options,
            index=dds_sales_accts.get_idx_from_id(existing_sales_item['default_acct_id']),
            key='sales-acct2'
        )
        
        
    if edit_mode == 'Add':
        # add button
        st.button(
            label='Add Item',
            on_click=add_item,
            kwargs=dict(
                name=sales_item_name, 
                item_type=item_types.get_id(sales_item_type).value, 
                entity_type=EntityType.CUSTOMER.value, 
                unit=unit_types.get_id(sales_unit_type).value, 
                unit_price=sales_unit_price, 
                currency=cur_types.get_id(sales_cur).value, 
                default_acct_id=dds_sales_accts.get_id(default_acct)
            ),
            key='sales-add'
        )
    else:
        # update and remove button
        btn_cols = st.columns([1, 1, 5])
        with btn_cols[0]:
            st.button(
                label='Update',
                type='secondary',
                on_click=update_item,
                kwargs=dict(
                    item_id=existing_sales_item_id,
                    name=sales_item_name, 
                    item_type=item_types.get_id(sales_item_type).value, 
                    entity_type=EntityType.CUSTOMER.value, 
                    unit=unit_types.get_id(sales_unit_type).value, 
                    unit_price=sales_unit_price, 
                    currency=cur_types.get_id(sales_cur).value, 
                    default_acct_id=dds_sales_accts.get_id(default_acct)
                ),
                key='sales-update'
            )
        with btn_cols[1]:
            st.button(
                label='Delete',
                type='primary',
                on_click=delete_item,
                kwargs=dict(
                    item_id=existing_sales_item_id
                ),
                key='sales-remove'
            )
        
        
with tabs[2]:
    dds_purchase = DropdownSelect(
        briefs=purch_item_display,
        include_null=False,
        id_key='Item ID',
        display_keys=['Name', 'Currency', 'Unit Price']
    )
    
    edit_cols = st.columns([1, 3])
    with edit_cols[0]:
        edit_mode = st.radio(
            label='Edit Mode',
            options=['Add', 'Edit'],
            #default='Add',
            #selection_mode ='single',
            horizontal=True,
        )
        
    if edit_mode == 'Edit':
        with edit_cols[1]:
            edit_purch = st.selectbox(
                label='👇 Select Item',
                options=dds_purchase.options,
                index=0,
                key='purch-item'
            )
        # selected something, will load it from database first
        existing_purch_item_id = dds_purchase.get_id(edit_purch)
        existing_purch_item = get_item(existing_purch_item_id)
    
    st.divider()
    
    if edit_mode == 'Edit':
        ui.badges(
            badge_list=[("Item ID", "default"), (existing_purch_item_id, "secondary")], 
            class_name="flex gap-2", 
            key="badges2"
        )
        
    purch_item_name = st.text_input(
        label="Name",
        value="" if edit_mode == 'Add' else existing_purch_item['name'],
        type='default', 
        placeholder="item name here", 
        key="pname"
    )
    
    item_cols = st.columns(2)
    with item_cols[0]:
        # item type
        if edit_mode == 'Add':
            purch_item_type = st.radio(
                label = '📦 Item Type',
                options=item_types.options,
                index=0,
                horizontal=True,
                key='purch-radio'
            )
        elif edit_mode == 'Edit':
            purch_item_type = st.radio(
                label = '📦 Item Type',
                options=item_types.options,
                index=item_types.get_idx_from_option(ItemType(existing_purch_item['item_type']).name),
                horizontal=True,
                key='purch-radio2'
            )
    
    with item_cols[1]:
        # unit type
        if edit_mode == 'Add':
            purch_unit_type = st.selectbox(
                label = '⏱️ Unit Type',
                options=unit_types.options,
                index=0,
                key='purch-unit'
            )
        elif edit_mode == 'Edit':
            purch_unit_type = st.selectbox(
                label = '⏱️ Unit Type',
                options=unit_types.options,
                index=unit_types.get_idx_from_option(UnitType(existing_purch_item['unit']).name),
                key='purch-unit2'
            )
    with item_cols[0]:
        # currency type
        if edit_mode == 'Add':
            purch_cur = st.selectbox(
                label = '💲 Currency',
                options=cur_types.options,
                index=0,
                key='purch-cur'
            )
        elif edit_mode == 'Edit':
            purch_cur = st.selectbox(
                label = '💲 Currency',
                options=cur_types.options,
                index=cur_types.get_idx_from_option(CurType(existing_purch_item['currency']).name),
                key='purch-cur2'
            )
        
    with item_cols[1]:
        # unit price
        purch_unit_price = st.number_input(
            label='🏷️ Unit Price',
            value=0 if edit_mode == 'Add' else existing_purch_item['unit_price'],
            key='purch-price'
        )
        
    # default account (only income type)
    purch_accts = get_accounts_by_type(acct_type=AcctType.EXP.value)
    dds_purch_accts = DropdownSelect(
        briefs=purch_accts,
        include_null=False,
        id_key='acct_id',
        display_keys=['acct_id', 'acct_name']
    )
    if edit_mode == 'Add':
        default_acct = st.selectbox(
            label = '📝 Default Account to record Purchase',
            options=dds_purch_accts.options,
            index=0,
            key='purch-acct'
        )
    elif edit_mode == 'Edit':
        default_acct = st.selectbox(
            label = '📝 Default Account to record Purchase',
            options=dds_purch_accts.options,
            index=dds_purch_accts.get_idx_from_id(existing_purch_item['default_acct_id']),
            key='purch-acct2'
        )
        
        
    if edit_mode == 'Add':
        # add button
        st.button(
            label='Add Item',
            on_click=add_item,
            kwargs=dict(
                name=purch_item_name, 
                item_type=item_types.get_id(purch_item_type).value, 
                entity_type=EntityType.SUPPLIER.value, 
                unit=unit_types.get_id(purch_unit_type).value, 
                unit_price=purch_unit_price, 
                currency=cur_types.get_id(purch_cur).value, 
                default_acct_id=dds_purch_accts.get_id(default_acct)
            ),
            key='purch-add'
        )
    else:
        # update and remove button
        btn_cols = st.columns([1, 1, 5])
        with btn_cols[0]:
            st.button(
                label='Update',
                type='secondary',
                on_click=update_item,
                kwargs=dict(
                    item_id=existing_purch_item_id,
                    name=purch_item_name, 
                    item_type=item_types.get_id(purch_item_type).value, 
                    entity_type=EntityType.SUPPLIER.value, 
                    unit=unit_types.get_id(purch_unit_type).value, 
                    unit_price=purch_unit_price, 
                    currency=cur_types.get_id(purch_cur).value, 
                    default_acct_id=dds_purch_accts.get_id(default_acct)
                ),
                key='purch-update'
            )
        with btn_cols[1]:
            st.button(
                label='Delete',
                type='primary',
                on_click=delete_item,
                kwargs=dict(
                    item_id=existing_purch_item_id
                ),
                key='purch-remove'
            )
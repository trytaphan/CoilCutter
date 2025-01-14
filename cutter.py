import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
from support import SupportBracket

st.title("Cutter")
a = SupportBracket(" C 100*35*10*2.5*9775")
b = SupportBracket("H200*150*3.2*4.5*2000")
d = SupportBracket("C100*35*10*2.5*9775")
print(a.to_dict())
df = pd.DataFrame(columns=SupportBracket.property_list)
print(len(df.index))
df.loc[len(df.index)] = a.to_dict()
df.loc[len(df.index)] = b.to_dict()
edited_df = st.data_editor(SupportBracket.display_in_CN(df))
# 配置GridOptions
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_selection(selection_mode="multiple",    # 允许多选行
                       use_checkbox=True)            # 加勾选框
gb.configure_grid_options(enableRangeSelection=True)    # 框选多个单元格，支持shift和ctrl
grid_options = gb.build()


grid_response = AgGrid(df,
                       gridOptions=grid_options,
                       editable=True,
                       height=100
                       )
# st.dataframe(df)


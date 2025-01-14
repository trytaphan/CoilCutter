import streamlit as st
import pandas as pd
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

print(df)
print(a.specification)
print(a.specification_r)
print(SupportBracket.display_in_CN(df))

edited_df = st.data_editor(SupportBracket.display_in_CN(df))



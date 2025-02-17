from st_aggrid import AgGrid, GridOptionsBuilder
from support import *
from solution import *
from pathlib import Path
from support import display_in_Chinese

st.set_page_config(page_title="带钢裁剪系统", layout="wide")
st.title("📏 带钢裁剪系统")

# 下载标准模板
template_path = Path(r"assets/input_template.xlsx")
with open(template_path, "rb") as template:
    st.download_button(
        label="下载模板",
        data=template,
        file_name="模版.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon="📥",
        help="请下载、填写该模板后上传数据"

    )
# 再次上传已经填好的数据
uploaded_file = st.file_uploader(label="📂 上传数据",
                                 type=["xlsx"],
                                 help="请按上面的模板上传数据")
if uploaded_file:
    # 解析
    brackets = Brackets.from_excel(uploaded_file, re_parse=True)
    df = brackets.to_dataframe()

    # 选定需要展示的列, 并翻译
    columns = ["name", "specification", "grade", "count", "specification_t"]
    filtered_df = display_in_Chinese(df[columns])
    # 配置GridOptions
    gb = GridOptionsBuilder.from_dataframe(filtered_df)
    gb.configure_selection(selection_mode="multiple",  # 允许多选行
                           use_checkbox=True)  # 加勾选框
    gb.configure_grid_options(enableRangeSelection=True)  # 框选多个单元格，支持shift和ctrl
    grid_options = gb.build()
    grid_response = AgGrid(filtered_df,
                           gridOptions=grid_options,
                           editable=True,
                           height=max(50 * len(filtered_df), 300)
                           )

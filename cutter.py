from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from support import *
from solution import *
from pathlib import Path
from support import display_in_Chinese, SupportBracket

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
    brackets.init_target_dimensions()
    df = brackets.to_dataframe()

    # 选定需要展示的列, 并翻译
    columns_to_diplay = ["name", "grade", "specification", "specification_t", "count", "height_t", "dimension_B_t",
                     "dimension_C_t", "thickness_t"]
    filtered_df = display_in_Chinese(df[columns_to_diplay])
    # 配置GridOptions
    gb = GridOptionsBuilder.from_dataframe(filtered_df)
    gb.configure_columns(["目标规格", "总数量"], editable=True)
    gb.configure_selection(selection_mode="multiple")
    gb.configure_grid_options(enableRangeSelection=True)  # 框选多个单元格，支持shift和ctrl
    grid_options = gb.build()

    grid_response = AgGrid(filtered_df,
                           gridOptions=grid_options,
                           editable=True,
                           height=max(50 * len(filtered_df), 300),
                           update_mode=GridUpdateMode.VALUE_CHANGED #仅在数值变化时重新渲染
                           )
    if st.button("应用修改并展示"):
        # 获取编辑后的 DataFrame
        updated_df = display_in_English(grid_response['data'])  # 将中文列名转换回英文列名

        # 使用更新后的 DataFrame 创建新的 Brackets 对象
        brackets = Brackets.from_dataframe(updated_df, re_parse=False)  # 重新加载更新后的数据到 Brackets

        # 更新目标规格字段
        brackets.update_target_dimensions()  # 确保所有 SupportBracket 对象的目标规格都得到更新

        st.write(str(brackets.list[0].specification_t))
        st.write(str(brackets.list[1].specification_t))
        print(str(brackets.list[0].specification_t))
        print(str(brackets.list[1].specification_t))


        #再利用更新的brackets更新updated_df
        updated_df = brackets.to_dataframe()

        # 确保更新后的 DataFrame 被重新显示
        st.write(r"更新后的 DataFrame：")
        st.dataframe(updated_df)  # 在页面上显示更新后的 DataFrame
        products = st.dataframe(brackets.prepare4solution())

        # 求解

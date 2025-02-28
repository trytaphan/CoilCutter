from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from support import *
from solution import *
from pathlib import Path
import plotly_express as px

def process_uploaded_file(_uploaded_file):
    _brackets = Brackets.from_excel(uploaded_file, re_parse=True)
    _brackets.init_target_dimensions()
    return _brackets.to_dataframe()

def visualize_key_elements(_combined_df):
    st.divider()
    # st.dataframe(_combined_df)
    # 添加关键指标看板
    total_weight = _combined_df["重量(吨)"].sum()
    avg_efficiency = _combined_df["原料利用率"].mean()

    st.markdown("### 关键指标")
    col1, col2, col3 = st.columns(3)
    col1.metric("总重量", f"{total_weight:.2f} 吨")
    col3.metric("平均利用率", f"{avg_efficiency:.1%}")
    st.markdown("### 📊 分析")
    if len(all_results) > 0:
        col1, col2 = st.columns([3, 2])
        with col1:
            # 重量构成旭日图
            st.markdown("**方案构成**")
            fig1 = px.sunburst(
                _combined_df,
                path=['group_description', '原料宽度(mm)'],
                values='重量(吨)',
                color='原料利用率',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.markdown("**原料使用量排名**")
            st.dataframe(
                combined_df.groupby("原料宽度(mm)")
                .agg(总重量=("重量(吨)", "sum"), 平均利用率=("原料利用率", "mean"))
                .sort_values("总重量", ascending=False)
                .style.format({"平均利用率": "{:.1%}"}),
                height=400
            )




st.set_page_config(page_title="带钢裁剪系统", layout="wide")
st.title("📏 带钢裁剪系统")
st.sidebar.header("操作菜单")

# 下载标准模板
template_path = Path(r"assets/input_template.xlsx")
with open(template_path, "rb") as template:
    st.sidebar.download_button(
        label="下载模板",
        data=template,
        file_name="模版.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon="📥",
        help="请下载、填写该模板后上传数据"

    )

# 再次上传已经填好的数据
uploaded_file = st.sidebar.file_uploader(label="📂 上传数据",
                                 type=["xlsx"],
                                 help="请按上面的模板上传数据")

if not uploaded_file:
    st.subheader("📌 使用指南")
    col1, col2 = st.columns([3, 2.5])
    with col1:
        st.markdown("""
                    #### 操作方法
                    1. 下载左侧的输入模板
                    2. 按照模板格式填写数据
                    3. 上传填写好的数据文件
                    4. 在表格中调整关键参数
                    5. 点击求解按钮获取方案
                    #### 数据要求
                    - 尺寸单位：统一使用毫米(mm)
                    #### 系统原理说明
                    - 自动解析上传的模版中的规格
                    - 按材质和厚度分组
                    - 对每一个分组使用动态规划模型求解
                    """)

    with col2:
        st.image("assets/coilgirl.png", use_container_width=True,
                 caption="领导发现前删除")








if uploaded_file:
    # 解析
    df = process_uploaded_file(uploaded_file)

    # 选定需要展示的列, 并翻译
    columns_to_display = ["name", "grade", "specification", "specification_t", "count", "height_t", "dimension_B_t",
                     "dimension_C_t", "thickness_t", "unfolded_width"]
    filtered_df = display_in_Chinese(df[columns_to_display])

    # 配置GridOptions
    gb = GridOptionsBuilder.from_dataframe(filtered_df)
    gb.configure_columns(["目标规格", "总数量", "展开宽度"], editable=True)
    gb.configure_selection(selection_mode="multiple")
    gb.configure_grid_options(enableRangeSelection=True)  # 框选多个单元格，支持shift和ctrl
    grid_options = gb.build()
    grid_response = AgGrid(filtered_df,
                           gridOptions=grid_options,
                           editable=True,
                           height=max(50 * len(df), 170),
                           update_mode=GridUpdateMode.VALUE_CHANGED #仅在数值变化时重新渲染
                           )

    if st.button("🚀 应用修改并求解", type="primary"):
        # 获取编辑后的 DataFrame
        updated_df = display_in_English(grid_response['data'])  # 将中文列名转换回英文列名

        # 使用更新后的 DataFrame 创建新的 Brackets 对象
        brackets = Brackets.from_dataframe(updated_df, re_parse=False)  # 重新加载更新后的数据到 Brackets

        # 更新目标规格字段
        brackets.update_target_dimensions()  # 确保所有 SupportBracket 对象的目标规格都得到更新

        # 再利用更新的brackets更新updated_df
        updated_df = brackets.to_dataframe()

        # 存储整体结果
        all_results = []
        group_descriptions = []

        # 按目标厚度和材质分组
        grouped = updated_df.groupby(["grade", "thickness_t"])
        group_index = 1
        for (grade, thick), group in grouped:
            group["total_length"] = group["count"] * group["length"]
            products = group[["unfolded_width", "total_length"]].rename(columns={"unfolded_width":"width"})
            products = products.groupby("width").sum().reset_index()

            # 对每组求解
            max_patterns = 5
            sol = Solution(products=products)
            result = sol.solve(max_patterns=max_patterns)

            if result is not None:
                # 处理求解结果
                result = display_in_Chinese(result)
                result["使用长度(m)"] = result["使用长度(mm)"] / 1000
                result["重量(吨)"] =(
                        result["使用长度(m)"] * result["原料宽度(mm)"] * thick
                        / 1e6 * 7.85 )
                result["原料利用率"] = (1 - result["边丝宽度(mm)"] / result["原料宽度(mm)"])
                col_in_order = (["原料宽度(mm)", "使用长度(m)","重量(吨)","原料利用率"] +
                                [column for column in result.columns if isinstance(column, float)])
                result = result[col_in_order]

                # 在下拉框里展示每一个分组的信息
                with st.expander(f"# 第{group_index}组: 材质：{grade}、厚度：{thick}",
                                 expanded=True):
                    # 用无序列表展示该分组包含的成品
                    st.markdown(f"**包含成品:**")
                    for _, row in group.iterrows():
                        escaped_spec = row['specification_t'].replace("*", "\\*")
                        st.markdown(f"- {row['name']}：材质{row['grade']}, 规格{escaped_spec}, 展开宽度{row['unfolded_width']}")
                    st.markdown("**裁剪方案：**")
                    # 展示该分组的裁剪方案
                    st.dataframe(result)

                # 记录分组信息
                description_text = f'第{group_index}组 ({grade}, {thick}mm)'
                result["group_description"] = description_text
                group_descriptions.append({"group_description": description_text,
                                           "products":group})
                all_results.append(result)

                group_index += 1

        # 全局结果分析
        combined_df = pd.concat(all_results)

        # 数据可视化
        visualize_key_elements(combined_df)












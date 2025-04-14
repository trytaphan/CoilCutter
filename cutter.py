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

    # 关键指标看板
    total_weight = _combined_df["重量(吨)"].sum()
    avg_efficiency = np.average(_combined_df["原料利用率"], weights=_combined_df["重量(吨)"])
    total_cost = (_combined_df["重量(吨)"] * _combined_df["单价(元/吨)"]).sum()

    st.markdown("### 关键指标")
    col1, col2, col3 = st.columns(3)
    col1.metric("总重量", f"{total_weight:.2f} 吨")
    col2.metric("平均利用率", f"{avg_efficiency:.1%}")
    col3.metric("总成本", f"¥{total_cost:,.0f}")

    st.markdown("### 📊 分析")
    # tab1, tab2 = st.tabs(["方案构成", "宽度分析"])
    # 
    # with tab1:
    #     # 旭日图
    #     fig1 = px.sunburst(
    #         _combined_df,
    #         path=['原料宽度(mm)', '分组描述'],
    #         values='重量(吨)',
    #         color='原料利用率',
    #         color_continuous_scale='Blues',
    #         range_color=[_combined_df['原料利用率'].min(), 1]
    #     )
    #     st.plotly_chart(fig1, use_container_width=True)
    # 
    # with tab2:
    #     # 各宽度使用情况
    #     fig2 = px.bar(
    #         _combined_df.groupby("原料宽度(mm)").agg(总重量=("重量(吨)", "sum")).reset_index(),
    #         x='原料宽度(mm)',
    #         y='总重量',
    #         text='总重量',
    #         color_discrete_sequence=['#2E86AB']
    #     )
    #     fig2.update_traces(texttemplate='%{y:.1f}t')
    #     st.plotly_chart(fig2, use_container_width=True)

    # 详细数据表
    st.markdown("### 详细数据")
    st.dataframe(
        _combined_df[
            ["分组描述", "原料宽度(mm)", "使用长度(m)", "重量(吨)", "单价(元/吨)", "成本", "原料利用率"]]
        .style.format({
            "使用长度(m)": "{:.1f}",
            "重量(吨)": "{:.3f}",
            "单价(元/吨)": "¥{:.0f}",
            "成本": "¥{:.0f}",
            "原料利用率": "{:.1%}"
        }),
        height=600
    )

def get_density(material_type):
    return SupportBracket.DENSITY[material_type]


# 主程序
st.set_page_config(page_title="带钢裁剪系统", layout="wide")
st.title("🏭 带钢裁剪优化系统")
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
uploaded_file = st.sidebar.file_uploader(label="📂 上传成品数据",
                                         type=["xlsx"],
                                         help="请按上面的模板上传数据")

# 使用指南
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
                    - 支持C型、U型钢（如C100\*35\*10\*2.5\*9775），数值分别会被解析为：
                        - 高度、宽度、卷边宽度、厚度和长度
                    - 对于C型和U型钢，如果只有4个维度，会认为卷边宽度为0
                    - 支持圆管（如Φ6\*2.5\*5200），数值分别会被解析为：
                        - 直径、厚度、长度
                        
                    #### 系统原理说明
                    - 自动解析上传的模版中的规格
                    - 按材质和厚度分组
                    - 对每一个分组使用动态规划模型求解
                    """)

    with col2:
        st.image("assets/coilgirl.png", use_container_width=True,
                 caption="不知道放个啥在这")

# 求解参数设置
with st.sidebar.expander(label="⚙️ 求解参数设置", expanded=True):
    config = {"max_patterns": st.slider("最大裁剪方案数", 1, 10, 5),
              "trim_tolerance": st.slider("边丝容忍度(mm)", 0, 150, 50)}

# 原料参数
discrete_widths = None  # widths在选择分立宽度时被设定
with st.sidebar.expander(label="⚙️ 原料设定", expanded=True):
    config["raw_type"] = st.radio("原料宽度范围",
                                  ["连续范围", "分立宽度"],
                                  help="选择使用连续范围的原料还是指定具体宽度")
    if config["raw_type"] == "连续范围":
        config["raw_range"] = st.slider("原料宽度范围(mm)", 1000, 1300, (1000, 1300))
        st.write(f"原料宽度范围为：{config['raw_range']}")
    elif config["raw_type"] == "分立宽度":
        raw_discrete = st.text_input("输入原料宽度，以逗号分隔")
        try:
            # 处理掉空字符串以及中文逗号
            discrete_widths = raw_discrete.replace(" ", "").replace("，", ",")
            # 将分立宽度写入config
            config["discrete_widths"] = [float(width) for width in discrete_widths.split(sep=",")]
        except ValueError:
            if discrete_widths:
                st.warning("请输入合法的原料宽度：以逗号分隔的数字")
                st.stop()
        if discrete_widths:
            for width in config["discrete_widths"]:
                if width<1000 or width>1300:
                    st.warning("请输入合法的原料宽度：1000到1300之内的数值")
                    st.stop()
            st.write(f"原料宽度为：{discrete_widths}")
with st.sidebar.expander(label="⚙️ 原料价格设定", expanded=True):
    config["price_1000_1249"] = st.number_input("1200mm以下单价(元/吨)", 3000, 5000, 3460)
    config["price_1250plus"] = st.number_input("1200mm以上单价(元/吨)", 3000, 5000, 3410)

if uploaded_file:
    # 解析
    df = process_uploaded_file(uploaded_file)
    df["density"] = df["material_type"].apply(get_density)

    # 选定需要展示的列, 并翻译
    columns_to_display = ["name", "material_type", "density", "grade", "specification", "specification_t", "count",
                          "unfolded_width"]
    # columns_to_display = ["name", "grade", "specification", "specification_t", "count", "height_t", "dimension_B_t",
    #                  "dimension_C_t", "thickness_t", "diameter", "unfolded_width"]
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
                           update_mode=GridUpdateMode.VALUE_CHANGED  # 仅在数值变化时重新渲染
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
        分组描述s = []

        # 准备参数，raw_materials
        if config["raw_type"] == "连续范围":
            r_widths = range(config["raw_range"][0], config["raw_range"][1] + 1)
        elif config["raw_type"] == "分立宽度":
            r_widths = config["discrete_widths"]
        raw_materials = pd.DataFrame(data=r_widths, columns=['width'])
        raw_materials = raw_materials.sort_values(by="width",ignore_index=True)

        # 准备参数，cost_df
        cost_df = pd.DataFrame({"start_width": [1000, 1250],
                                "cost": [config["price_1000_1249"], config["price_1250plus"] ]})


        # 按目标厚度和材质分组
        grouped = updated_df.groupby(["grade", "thickness_t", "material_type"])
        group_index = 1
        for (grade, thick, material), group in grouped:
            group["total_length"] = group["count"] * group["length"]
            products = group[["unfolded_width", "total_length"]].rename(columns={"unfolded_width": "width"})
            products = products.groupby("width").sum().reset_index()
            # 对每组求解
            sol = Solution(raw_materials=raw_materials,
                           products=products,
                           cost_df=cost_df)
            result = sol.solve(max_patterns=config["max_patterns"])

            if result is not None:
                # 处理求解结果
                result = display_in_Chinese(result)
                result["使用长度(m)"] = result["使用长度(mm)"] / 1000
                result["重量(吨)"] = (
                        result["使用长度(m)"] * result["原料宽度(mm)"] * thick
                        / 1e6 * get_density(material))
                result["原料利用率"] = (1 - result["边丝宽度(mm)"] / result["原料宽度(mm)"])
                col_in_order = (["原料宽度(mm)", "使用长度(m)", "重量(吨)", "原料利用率"] +
                                [column for column in result.columns if isinstance(column, float)])
                result = result[col_in_order]

                # 在下拉框里展示每一个分组的信息
                with st.expander(f"# 第{group_index}组: 材料： {material}、材质：{grade}、厚度：{thick}",
                                 expanded=True):
                    # 用无序列表展示该分组包含的成品
                    st.markdown(f"**包含成品:**")
                    for _, row in group.iterrows():
                        escaped_spec = row['specification_t'].replace("*", "\\*")
                        st.markdown(
                            f"- {row['name']}：材质{row['grade']}, 规格{escaped_spec}, 展开宽度{row['unfolded_width']}")
                    st.markdown("**裁剪方案：**")
                    # 展示该分组的裁剪方案
                    # 在生成result时添加单价列
                    result["单价(元/吨)"] = result["原料宽度(mm)"].map(lambda w:
                                                                    config["price_1000_1249"] if w < 1250 else config[
                                                                        "price_1250plus"]
                                                                    )

                    # 计算每个方案的成本
                    result["成本"] = result["重量(吨)"] * result["单价(元/吨)"]
                    styled_df = result.style.format({
                        "使用长度(m)": "{:.1f}",
                        "重量(吨)": "{:.3f}",
                        "原料利用率": "{:.1%}",
                        "成本": "{:.02f}",
                        **{str(w): "{:.0f}" for w in products.width.unique()}  # 成品数量整数显示
                    })
                    st.dataframe(styled_df)

                # 记录分组信息
                description_text = f'第{group_index}组 ({material}, {grade}, {thick}mm)'
                result["分组描述"] = description_text
                分组描述s.append({"分组描述": description_text,
                                           "products": group})
                all_results.append(result)

                group_index += 1

        # 全局结果分析
        combined_df = pd.concat(all_results)
        combined_df = combined_df.reset_index(drop=True)

        # 数据可视化
        visualize_key_elements(combined_df)

from ortools.linear_solver import pywraplp
import itertools
import pandas as pd

def generate_cutting_patterns(raw_materials, products):
    # 假设每个pattern都只有一种成品，它的个数不会超过(原料宽度//成品宽度)
    max_counts = (raw_materials.width.values.reshape(-1, 1) //
                  products.width.values.reshape(1, -1))

    patterns = []
    for i in range(len(raw_materials)):

        # 生成所有可能的组合
        temp = itertools.product(*[range(count + 1) for count in max_counts[i]])
        temp_df = pd.DataFrame(temp)

        # 计算每种组合的总宽度
        determiner = temp_df.dot(products.width.values)

        # 筛选有效的裁剪方案
        patterns.append(temp_df[determiner <= raw_materials.loc[i, "width"]])
    return patterns

def solve():

    # 原材料
    raw_materials = pd.DataFrame(columns=["width", "patterns"])
    raw_materials.width = [1280, 1260, 1000, 950, 1250, 1200]

    # 成品
    products = pd.DataFrame({
        "len": [7, 4, 8, 11],  # 单个长度
        "width": [166, 285, 160, 112],  # 单个宽度
        "len_w": [9775, 7444, 7444, 9775]  # 总长度
    })

    # 生成所有的裁剪方案
    raw_materials.patterns = generate_cutting_patterns(raw_materials, products)
    # 创建SCIP求解器实例
    solver = pywraplp.Solver.CreateSolver("SCIP")
    return raw_materials

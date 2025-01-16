from ortools.linear_solver import pywraplp
import itertools
import pandas as pd


def generate_cutting_patterns(raw_materials, products):
    """
    pattern_matrices[r]:第r种原料的裁剪方式矩阵
    pattern_matrices[r].at[i, p]:第r种原料中第i种裁剪方式中第p种成品的重复次数
    """
    # 假设每个pattern都只有一种成品，它的个数不会超过(原料宽度//成品宽度)
    max_counts = (raw_materials.width.values.reshape(-1, 1) //
                  products.width.values.reshape(1, -1))

    pattern_matrices = []
    for i in range(len(raw_materials)):
        # 生成所有可能的组合
        temp = itertools.product(*[range(count + 1) for count in max_counts[i]])
        temp_df = pd.DataFrame(temp)

        # 计算每种组合的总宽度
        whole_width = temp_df.dot(products.width.values)

        # 筛选有效的裁剪方案
        pattern_matrices.append(temp_df[whole_width <= raw_materials.loc[i, "width"]])
    return pattern_matrices


def solve():
    # 原材料
    raw_materials = pd.DataFrame(columns=["width"])
    raw_materials.width = [1280, 1260, 1000, 950, 1250, 1200]

    # 成品
    products = pd.DataFrame({
        "length": [9775, 7444, 7444, 9775],  # 单个长度
        "width": [166, 285, 160, 112],  # 单个宽度
        "count": [400, 350, 350, 400]  # 件数
    })

    # 生成所有的裁剪方案
    pattern_matrices = generate_cutting_patterns(raw_materials, products)

    # 创建SCIP求解器实例
    solver = pywraplp.Solver.CreateSolver("SCIP")

    # 定义变量, l[(i, j)]为第i种原料的第j种pattern使用的长度
    l = {}
    for i, pattern_m in enumerate(pattern_matrices):
        for j in range(len(pattern_m)):
            l[(i, j)] = solver.NumVar(0, solver.Infinity(), f"l[{i}, {j}]")

    # 定义目标函数
    objective = solver.Objective()  #目标为使用原材料的总面积最小
    for (i, j), var in l.items():
        objective.SetCoefficient(var, float(raw_materials.loc[i, "width"]))
    objective.SetMinimization()

    # 添加约束条件
    for p, width in enumerate(products.width):
        # 对第p个成品，添加约束，使得该成品的总长度不小于要求的count*length.
        lower_bound = float(products.loc[p, "count"]) * float(products.loc[p, "length"])
        constraint = solver.Constraint(lower_bound, solver.infinity())
        for (i, j), var in l.items():
            coeff = float(pattern_matrices[i].iloc[j, p])
            constraint.SetCoefficient(var, coeff)


    # 求解
    status = solver.Solve()

    # 输出结果
    if status == pywraplp.Solver.OPTIMAL:
        print("已找到最优解！")
        col= [products.loc[idx, "width"] for idx in range(len(products))] + ["len_used"]
        result = pd.DataFrame(columns = col)
        for (i, j), var in l.items():
            if var.solution_value() > 0:
                pattern_content = pattern_matrices[i].iloc[j]   #当前pattern的内容
                result.loc[len(result)] = list(pattern_content) + [var.solution_value()]


    return result
solve()

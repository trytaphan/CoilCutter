from ortools.linear_solver import pywraplp
import itertools
import pandas as pd


class CuttingPatterns:
    def __init__(self, products):
        self.raw_matrices = {}  # 存储不同原材料宽度的裁剪方案
        self.products = products  # 记录成品信息

    def print(self):
        for raw_width, df in self.raw_matrices.items():
            print(f"宽度为{raw_width}的原料裁剪方案为：")
            print(df)

    def generate(self, raw_materials, cost_df):
        """

        :param raw_materials: DataFrame, 有一列为可选原料的宽度
        :param cost_df: DataFrame, 两列:start_width, cost，
        从一个start_width（包含）到另一个start_width（不包含）为止的原料的成本为cost
        :return: None
        """
        # 首先进行排序
        cost_df.sort_values(by="start_width", axis=0, inplace=True, ignore_index=True)

        pass


    @staticmethod
    def merge(one, another):
        """
        合并两个 CuttingPatterns 的裁剪方案。
        要求两个对象的成品宽度必须一致。
        """
        if not one.products.width.equals(another.products.width):
            raise ValueError("合并方案要求成品宽度一致")

        # 复制当前对象的raw_matrices，避免修改原数据
        merged_matrices = one.raw_matrices.copy()

        for raw_width, m2_df in another.raw_matrices.items():
            if raw_width in merged_matrices:
                # 合并两个 DataFrame，去重
                merged_matrices[raw_width] = pd.concat(
                    [merged_matrices[raw_width], m2_df]
                                                      ).drop_duplicates(ignore_index=True)
            else:
                merged_matrices[raw_width] = m2_df

        result = CuttingPatterns(one.products)
        result.raw_matrices = merged_matrices
        return result

    def generate_without_redundancy(self, raw_materials):
        """
        生成无边丝（无冗余宽度）的裁剪方案

        arguments：
        - raw_materials: DataFrame，包含 "width"（原材料宽度）
        - products: DataFrame，包含 "width"（成品宽度）

        return：
        - pattern_matrices: 一个列表，每个元素是一个 DataFrame（表示该原材料的所有裁剪方案）
        """
        max_counts = (raw_materials.width.values.reshape(-1, 1) //
                      self.products.width.values.reshape(1, -1))
        pattern_matrices = {}
        for r in range(len(raw_materials.width)):
            # 生成所有组合
            temp = itertools.product(*[range(count + 1) for count in max_counts[r]])
            temp_df = pd.DataFrame(temp, columns=self.products.width)

            # 计算每种组合的总宽度
            whole_width = temp_df.values.dot(self.products.width.values.reshape(-1, 1))

            # 筛选无边丝的方案
            filtered_df = temp_df[whole_width.flatten() == raw_materials.loc[r, "width"]]

            if len(filtered_df) > 0:
                pattern_matrices[raw_materials.loc[r, 'width']] = filtered_df.reset_index(drop=True)

        return pattern_matrices

    def generate_with_redundancy(self, raw_materials):
        """
        处理价格区间边缘位置的原料的方案，此时允许有边丝，但是边丝不得超过成品宽度的最小值
        （否则显然有更佳的方案）。
        arguments:
        - raw_materials: DataFrame，包含 "width"（原材料宽度）
        - products: DataFrame，包含 "width"（成品宽度）
        - width_cost: DataFrame, 包含"width"(区间最小宽度,区间包含此宽度), "cost":成本。

        return:
        - pattern_matrices: 一个dict，每个元素是一个 DataFrame（表示该原材料的所有裁剪方案）
        """
        max_counts = (raw_materials.width.values.reshape(-1, 1) //
                      self.products.width.values.reshape(1, -1))
        pattern_matrices = {}
        for r in range(len(raw_materials.width)):
            # 生成所有组合
            temp = itertools.product(*[range(count + 1) for count in max_counts[r]])
            temp_df = pd.DataFrame(temp, columns=self.products.width)

            # 计算每种组合的总宽度
            whole_width = temp_df.values.dot(self.products.width.values.reshape(-1, 1))

            # 筛选边丝宽度不超过最小成品宽度的
            filtered_df = temp_df[(whole_width.flatten() <= raw_materials.loc[r, "width"]) &
                                  (whole_width.flatten() >= (
                                              raw_materials.loc[r, "width"] - self.products.width.min()))]

            if len(filtered_df) > 0:
                pattern_matrices[raw_materials.loc[r, 'width']] = filtered_df.reset_index(drop=True)
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
    objective = solver.Objective()  # 目标为使用原材料的总面积最小
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
        col = [products.loc[idx, "width"] for idx in range(len(products))] + ["len_used"]
        result = pd.DataFrame(columns=col)
        for (i, j), var in l.items():
            if var.solution_value() > 0:
                pattern_content = pattern_matrices[i].iloc[j]  # 当前pattern的内容
                result.loc[len(result)] = list(pattern_content) + [var.solution_value()]

    return result


solve()

from ortools.linear_solver import pywraplp
import itertools
import pandas as pd
from streamlit import columns


class CuttingPatterns:
    def __init__(self, products):
        self.raw_matrices = {}  # Key: raw_width, Value: DataFrame of patterns
        self.products = products.sort_values(by="width", ignore_index=True)

    def print(self, detailed=False):
        """
        打印裁剪方案。
        :param detailed: 是否打印完整裁剪模式（False 仅显示方案数量）
        """
        pattern_count = 0
        width_count = 0

        for raw_width, df in self.raw_matrices.items():
            pattern_count += len(df)
            print(f"宽度为{raw_width}的原料裁剪方案为：共{len(df)}种。")
            if detailed and not df.empty:
                print(df)
            if not df.empty:
                width_count +=1

        print(f"总共为{width_count}种原料生成了{pattern_count}种方案。")

    def generate(self, raw_materials, cost_df):
        """

        :param raw_materials: DataFrame, 有一列为可选原料的宽度
        :param cost_df: DataFrame, 两列:start_width, cost，
        从一个start_width（包含）到另一个start_width（不包含）为止的原料的成本为cost
        :return: None
        """
        # 排序数据
        cost_df.sort_values(by="start_width", axis=0, inplace=True, ignore_index=True)
        self.products.sort_values(by="width", axis=0, inplace=True, ignore_index=True)

        # 生成无边丝方案
        p1 = CuttingPatterns(self.products)
        p1.raw_matrices = self.generate_without_redundancy(raw_materials)

        # 寻找离价格区间最近的原料，生成无边丝方案
        raw_materials_edge = pd.DataFrame(columns=["width"])
        index = 0
        for start_width in cost_df.start_width:
            while index < len(raw_materials.width):
                if raw_materials.width[index] >= start_width:
                    raw_materials_edge.loc[len(raw_materials_edge)] = [start_width]
                    index += 1
                    break
                index += 1

        # 生成无边丝方案
        p2 = CuttingPatterns(self.products)
        p2.raw_matrices = p2.generate_with_redundancy(raw_materials_edge)

        self.merge(p1).merge(p2)

    def merge(self, another):
        """
        直接合并另一个 CuttingPatterns 的裁剪方案到当前实例。
        要求两个对象的成品宽度必须一致。
        """
        if not self.products.width.equals(another.products.width):
            raise ValueError("合并方案要求成品宽度一致")

        for raw_width, m2_df in another.raw_matrices.items():
            if raw_width in self.raw_matrices:
                # 合并两个 DataFrame，去重
                self.raw_matrices[raw_width] = pd.concat(
                    [self.raw_matrices[raw_width], m2_df]
                ).drop_duplicates(ignore_index=True)
            else:
                self.raw_matrices[raw_width] = m2_df

        return self  # 返回自身，支持链式调用

    def generate_without_redundancy(self, raw_materials):
        """
        生成无边丝（无冗余宽度）的裁剪方案

        arguments：
        - raw_materials: DataFrame，包含 "width"（原材料宽度）
        - products: DataFrame，包含 "width"（成品宽度）

        return：
        - pattern_matrices: 一个列表，每个元素是一个 DataFrame（表示该原材料的所有裁剪方案）
        """

        if not len(raw_materials.width) > 0:
            return pd.DataFrame(columns=self.products.width)
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

        if not len(raw_materials.width) > 0:
            return pd.DataFrame(columns=self.products.width)

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


class Solution:
    def __init__(self):
        pass

    @staticmethod
    def get_raw_materials():
        raw_materials = pd.DataFrame(columns=["width"])
        raw_materials.width = [1280, 1260, 1000, 950, 1250, 1200]
        return raw_materials

    @staticmethod
    def get_products():
        products = pd.DataFrame({
            "length": [9775, 7444, 7444, 9775],  # 单个长度
            "width": [166, 285, 160, 112],  # 单个宽度
            "count": [400, 350, 350, 400]  # 件数
        })
        return products

    @staticmethod
    def solve(self):
        # 原材料
        raw_materials = Solution.get_raw_materials()

        # 成品
        products = Solution.get_products()

        # 生成所有的裁剪方案
        generator = CuttingPatterns()
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




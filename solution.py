from ortools.linear_solver import pywraplp
import itertools
import pandas as pd
import numpy as np
import bisect


class CuttingPatterns:
    def __init__(self,
                 products=pd.DataFrame(columns=["width"]),
                 raw_materials=pd.DataFrame(columns=["width"])):
        self.raw_matrices = {}  # Key: raw_width, Value: DataFrame of patterns
        self.products = products.sort_values(by="width", ignore_index=True)
        self.raw_materials = raw_materials.sort_values(by="width", ignore_index=True)

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
                width_count += 1

        print(f"总共为{width_count}种原料生成了{pattern_count}种方案。")

    def _add_patterns(self, raw_width, patterns):
        """
        为当前实例添加方案。
        :param raw_width: 添加方案的原材料宽度。
        :param patterns: DataFrame: 加入的方案
        """
        if raw_width in self.raw_matrices:
            self.raw_matrices[raw_width] = (pd.concat([
                self.raw_matrices[raw_width], patterns]).
                                            drop_duplicates(ignore_index=True))
        else:
            self.raw_matrices[raw_width] = patterns

    def merge(self, other):
        """合并另一个 CuttingPatterns 实例的方案"""
        if not self.products.width.equals(other.products.width):
            raise ValueError("成品规格不一致，无法合并")
        for raw_width, df in other.raw_matrices.items():
            self._add_patterns(raw_width, df)
        return self

    @staticmethod
    def _generate_combination(tolerance, width, products, current_comb, idx):
        # 若剩余宽度在容忍区间内且非负，生成当前组合，此方法暂时不用，留作参考
        if 0 <= width <= tolerance:
            yield current_comb.copy()
            return

        # 终止条件：宽度不足或处理完所有产品
        if width < 0 or idx == len(products):
            return

        # 计算当前产品的最大可能数量并遍历
        max_count = width // products[idx]
        original_value = current_comb[idx]  # 保存当前idx的值
        for i in range(max_count + 1):
            current_comb[idx] = i
            new_width = width - i * products[idx]
            yield from CuttingPatterns._generate_combination(tolerance, new_width, products, current_comb, idx + 1)
        # 每个层级yield之后负责把当前层级的current_comb恢复原值
        current_comb[idx] = original_value

    def _generate_patterns(self, tolerance: int, raw_materials=None, products=None):
        """

        :param tolerance: 允许的边丝宽度。
        :param raw_materials: DataFrame，包含 "width"（原材料宽度）。
        :param products: DataFrame，包含 "width"（成品宽度）
        :return: pattern_matrix: DataFrame, 表示该原材料的所有裁剪方案
        """
        if raw_materials is None:
            raw_materials = self.raw_materials
        if products is None:
            products = self.products
        if not len(raw_materials.width) > 0:
            return pd.DataFrame(columns=products.width)

        max_counts = (raw_materials.width.values.reshape(-1, 1) //
                      products.width.values.reshape(1, -1))
        patterns = []
        for r in range(len(raw_materials.width)):
            # 生成所有组合
            temp = itertools.product(*[range(int(count) + 1) for count in max_counts[r]])
            temp_df = pd.DataFrame(temp, columns=products.width.values)

            # 计算每种组合的总宽度
            whole_width = temp_df.values.dot(products.width.values.reshape(-1, 1))
            temp_df["trim_width"] = raw_materials.loc[r, "width"] - whole_width
            temp_df["raw_width"] = raw_materials.loc[r, "width"]

            # 筛选边丝宽度不超过最小成品宽度的
            filtered_df = temp_df[(whole_width.flatten() <= raw_materials.loc[r, "width"]) &
                                  (whole_width.flatten() > (
                                          raw_materials.loc[r, "width"] - tolerance))]

            if len(filtered_df) > 0:
                patterns.append(filtered_df)
        return pd.concat(patterns, ignore_index=True)

    @staticmethod
    def _price_patterns(patterns, cost_df):
        if patterns.raw_width.min() < cost_df.start_width.min():
            raise ValueError("原料宽度超过价格范围。")
        cost_df = cost_df.sort_values(by="start_width", ignore_index=True)
        cost_list = list(cost_df.start_width)

        def _price_raw(raw_width):
            idx = bisect.bisect_right(cost_list, raw_width) - 1
            return cost_df.loc[idx, "cost"]

        patterns["cost"] = patterns["raw_width"].map(_price_raw)
        return patterns

    @staticmethod
    def _filter_patterns(patterns):
        """对于生成完全相同成品的pattern，对每种价格只取其中边丝最少的"""
        by = list(patterns.columns[:-3]) + ["cost"]
        indices = patterns.groupby(by)["trim_width"].idxmin()
        return patterns.loc[indices].reset_index(drop=True)

    def generate(self, cost_df):
        # 排序数据
        cost_df.sort_values(by="start_width", axis=0, inplace=True, ignore_index=True)
        self.products.sort_values(by="width", axis=0, inplace=True, ignore_index=True)

        # 生成全部pattern
        self.raw_matrix = self._generate_patterns(tolerance=self.products.width.min(),
                                             raw_materials=self.raw_materials,
                                             products=self.products)

        # 给每个pattern标价格
        self.raw_matrix = self._price_patterns(self.raw_matrix, cost_df)

        # 过滤低效pattern
        self.raw_matrix = self._filter_patterns(self.raw_matrix)
        return self.raw_matrix


class Solution:
    def __init__(self, raw_materials=None, products=None):
        """
        :param raw_materials: DataFrame,包含width
        :param products: DataFrame,包含width和total_length两列
        """
        self.result = None
        self.products = products
        if raw_materials is not None:
            self.raw_materials = raw_materials
        else:
            self.get_raw_materials()

        self.cost_df = Solution.get_cost_df()

    def get_raw_materials(self):
        """提供默认的原材料设置"""
        raw_materials = pd.DataFrame(data=range(1000, 1301), columns=['width'])
        self.raw_materials = raw_materials.sort_values(by="width", ignore_index=True)
        return self.raw_materials

    @staticmethod
    def get_cost_df():
        return pd.DataFrame({"start_width": [1000, 1200, 1300],
                        "cost": [4240, 4190, 4150]})


    def solve(self, max_patterns):


        # 生成所有的裁剪方案
        generator = CuttingPatterns(raw_materials=self.raw_materials, products=self.products)
        patterns_df = generator.generate(cost_df=self.cost_df)  # {width:DataFrame(Patterns)}

        # 创建SCIP求解器实例
        solver = pywraplp.Solver.CreateSolver("SCIP")
        if not solver:
            return "Solver 初始化失败。"

        # 定义变量
        variables = {}
        for idx, row in patterns_df.iterrows():
            variables[idx] = {
                "l": solver.NumVar(0, solver.Infinity(), f"l_{idx}"),
                "y": solver.BoolVar( f"y_{idx}")
                              }

        # 定义目标函数
        objective = solver.Objective()  # 目标为使用原材料的价值最小
        for idx, row in patterns_df.iterrows():
            cost = float(row["cost"]*(row["raw_width"] - row["trim_width"]/2))
            objective.SetCoefficient(variables[idx]["l"], cost)
        objective.SetMinimization()

        # 约束条件1: 每种成品的总长度均被满足
        for _, product in self.products.iterrows():
            # 对每种成品，添加约束，使得该成品的总长度不低于要求。
            lower_bound = float(product["total_length"])
            constraint = solver.Constraint(lower_bound, solver.infinity())
            for idx, pattern in patterns_df.iterrows():
                constraint.SetCoefficient(variables[idx]["l"], float(pattern[product["width"]]))

        # 约束条件2：使用的pattern数不超过限制
        constraint = solver.Constraint(0, max_patterns)
        for idx in patterns_df.index:
            constraint.SetCoefficient(variables[idx]["y"], 1)

        # 约束条件3: 限制长度为0时，使用标记y必须为0
        M = 1e11
        for idx in patterns_df.index:
            solver.Add(variables[idx]["l"] <= variables[idx]["y"] * M)

        # 求解
        status = solver.Solve()

        # 输出结果
        if status == pywraplp.Solver.OPTIMAL:
            print("已找到最优解！")

            # 初始化结果DataFrame
            result = patterns_df.copy()
            result["len_used"] =\
                [variables[idx]["l"].solution_value() for idx in result.index]
            result = result[result["len_used"] >= 1e-6].copy()
            self.result = result
            return result
        else:
            print("未找到最优解")
            return None

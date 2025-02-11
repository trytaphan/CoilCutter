from ortools.linear_solver import pywraplp
import itertools
import pandas as pd
from pandas.util.version import Infinity
from streamlit import columns


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

    def _generate_patterns(self, tolerance: int, raw_materials=None, products=None):
        """

        :param tolerance: 允许的边丝宽度。
        :param raw_materials: DataFrame，包含 "width"（原材料宽度）。
        :param products: DataFrame，包含 "width"（成品宽度）
        :return: pattern_matrices: 一个dict，每个元素是一个 DataFrame（表示该原材料的所有裁剪方案）
        """
        if raw_materials is None:
            raw_materials = self.raw_materials
        if products is None:
            products = self.products
        if not len(raw_materials.width) > 0:
            return pd.DataFrame(columns=products.width)

        max_counts = (raw_materials.width.values.reshape(-1, 1) //
                      products.width.values.reshape(1, -1))
        pattern_matrices = {}
        for r in range(len(raw_materials.width)):
            # 生成所有组合
            temp = itertools.product(*[range(count + 1) for count in max_counts[r]])
            temp_df = pd.DataFrame(temp, columns=products.width.values)

            # 计算每种组合的总宽度
            whole_width = temp_df.values.dot(products.width.values.reshape(-1, 1))

            # 筛选边丝宽度不超过最小成品宽度的
            filtered_df = temp_df[(whole_width.flatten() <= raw_materials.loc[r, "width"]) &
                                  (whole_width.flatten() >= (
                                          raw_materials.loc[r, "width"] - tolerance))]

            if len(filtered_df) > 0:
                pattern_matrices[raw_materials.loc[r, 'width']] = filtered_df.reset_index(drop=True)
        return pattern_matrices

    def _select_edge_raw_materials(self, cost_df):
        """选择价格区间边缘的原材料"""
        edge_raw_materials = pd.DataFrame(columns=["width"])
        index = 0
        for start_width in cost_df.start_width:
            while index < len(self.raw_materials.width):
                if self.raw_materials.width[index] >= start_width:
                    edge_raw_materials.loc[len(edge_raw_materials)] = [start_width]
                    index += 1
                    break
                index += 1
        return edge_raw_materials

    def generate(self, cost_df):
        """

        :param raw_materials: DataFrame, 有一列为可选原料的宽度
        :param cost_df: DataFrame, 两列:start_width, cost，
        从一个start_width（包含）到另一个start_width（不包含）为止的原料的成本为cost
        :return: 实例的raw_matrices
        """
        # 排序数据
        cost_df.sort_values(by="start_width", axis=0, inplace=True, ignore_index=True)
        self.products.sort_values(by="width", axis=0, inplace=True, ignore_index=True)

        # 生成无边丝方案，并存入 self.raw_matrices
        matrices1 = self._generate_patterns(tolerance=0)
        for raw_width, df in matrices1.items():
            self._add_patterns(raw_width, df)

        # 寻找离价格区间最近的原料，生成无边丝方案
        edge_raw_materials = self._select_edge_raw_materials(cost_df)

        # 生成有边丝方案，并存入 self.raw_matrices
        matrices2 = self._generate_patterns(tolerance=self.products.width.min(),
                                            raw_materials=edge_raw_materials)

        for raw_width, df in matrices2.items():
            self._add_patterns(raw_width, df)

        return self.raw_matrices


class Solution:
    def __init__(self):
        self.result = None


    @staticmethod
    def get_raw_materials():
        raw_materials = pd.DataFrame(columns=["width"])
        raw_materials.width = [1280, 1260, 1000, 950, 1250, 1200]
        return raw_materials.sort_values(by="width", ignore_index=True)

    @staticmethod
    def get_products():
        products = pd.DataFrame({
            "total_length": [400*9775, 350*7444, 350*7444, 400*9775],  # 总长度
            "width":        [166, 285, 160, 112],  # 宽度
        })
        return products.sort_values(by="width", ignore_index=True)

    @staticmethod
    def get_cost_df():
        cost_df = pd.DataFrame({"start_width":[1200, 1000, 1250],
                                "cost":       [4050, 4000, 4100]})
        return cost_df

    @staticmethod
    def solve(self, min_l=0):
        # 原材料
        raw_materials = Solution.get_raw_materials()

        # 成品
        products = Solution.get_products()

        # 价格表
        cost_df = Solution.get_cost_df()

        # 生成所有的裁剪方案
        cost_df = Solution.get_cost_df()
        generator = CuttingPatterns(raw_materials=raw_materials, products=products)
        raw_matrices = generator.generate(cost_df=cost_df) # {width:DataFrame(Patterns)}

        # 创建SCIP求解器实例
        solver = pywraplp.Solver.CreateSolver("SCIP")
        if not solver:
            return "Solver 初始化失败。"

        # 定义变量, l[(w, p)]为宽度为w的原料的第p种pattern使用的长度
        l = {}
        y = {}
        for raw_width, patterns in raw_matrices.items():
            for p in range(len(patterns)):
                l[(raw_width, p)] = solver.NumVar(min_l,
                                                  solver.Infinity(),
                                                  f"l[{raw_width}, {p}]")
                y[(raw_width, p)] = solver.BoolVar(f"y[{raw_width}, {p}]")




        # 定义目标函数
        objective = solver.Objective()  # 目标为使用原材料的总面积最小
        for (w, p), var in l.items():
            objective.SetCoefficient(var, float(w))
        objective.SetMinimization()

        # 约束条件1: 每种成品的总长度均被满足
        for p, width in enumerate(products.width):
            # 对每种成品，添加约束，使得该成品的总长度不低于要求。
            lower_bound = float(products.loc[p, "count"])
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

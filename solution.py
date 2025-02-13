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
    def _generate_combination(tolerance, raw_width, products, current_comb, idx):
        # 剩余宽度小于0，不符合条件，直接返回
        if raw_width < 0:
            return

        # 剩余宽度不超过限度，yield结果
        if raw_width <= tolerance:
            yield current_comb

        # 遍历products里的每种宽度
        for i, width in enumerate(products[idx:]):
            max_count = raw_width // width
            # 遍历每一个可能的出现次数
            for count in range(max_count + 1):
                current_comb[i] = count
                raw_width -= count * width
                yield from CuttingPatterns._generate_patterns(tolerance, raw_width,
                                                              products, current_comb, i+1)
    # @staticmethod
    # def _generate_combination(tolerance, raw_width, products, current_comb, idx):
    #     # 剩余宽度小于0，不符合条件，直接返回
    #     if raw_width < 0:
    #         return
    #
    #     # 剩余宽度不超过限度，yield结果
    #     if raw_width <= tolerance:
    #         yield current_comb
    #
    #     # 遍历products里的每种宽度
    #     for i, width in enumerate(products[idx:]):
    #         max_count = raw_width // width
    #         # 遍历每一个可能的出现次数
    #         for count in range(max_count + 1):
    #             current_comb[i] += count
    #             raw_width -= count * width
    #             yield from CuttingPatterns._generate_patterns(tolerance, raw_width,
    #                                                           products, current_comb, i+1)
    #             current_comb[i] -= count


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
            temp = itertools.product(*[range(int(count) + 1) for count in max_counts[r]])
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
        edge_width = set()
        raw_width = self.raw_materials.width.values.astype(float).tolist()
        for start_width in cost_df.start_width.values.astype(float):
            i = bisect.bisect_left(raw_width, start_width)
            if i < len(raw_width):
                edge_width.add(raw_width[i])
        result = pd.DataFrame({"width": list(edge_width)}).sort_values(by="width", ignore_index=True)
        return result

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

    @staticmethod
    def trim_width(raw_width, pattern, products):
        pattern_np = np.array(pattern)
        products_width_np = products.width.values
        return raw_width - pattern_np.dot(products_width_np)


class Solution:
    def __init__(self):
        self.result = None
        self.cost_df = pd.DataFrame()
        self.raw_materials = pd.DataFrame()
        self.products = pd.DataFrame()

    def get_raw_materials(self):
        raw_materials = pd.DataFrame(columns=["width"])
        raw_materials = pd.DataFrame(data=range(1000, 1301), columns=['width'])
        # raw_materials = pd.DataFrame(data=[1250], columns = ['width'])
        self.raw_materials = raw_materials.sort_values(by="width", ignore_index=True)
        return self.raw_materials

    def get_products(self):
        # products = pd.DataFrame({
        #     "total_length": [6400 * 9775, 6400 * 7444, 6400 * 7444, 6400 * 9775],  # 总长度
        #     "width": [166, 166, 166, 200],  # 宽度
        # })
        products = pd.DataFrame({
            "total_length": [6400 * 9775],  # 总长度
            "width": [166],  # 宽度
        })
        self.products = products.sort_values(by="width", ignore_index=True)
        return self.products

    def set_cost(self, cost_df=None):

        # 如果 cost_df 为空，使用默认值:实例属性cost_df
        cost_df = self.cost_df if cost_df is None else cost_df

        # 排序cost_df
        cost_df.sort_values(by="start_width", ignore_index=True, inplace=True)

        # 检验cost_df合理性
        if cost_df.start_width[0] > self.raw_materials.width[0]:
            raise ValueError("价格表不能覆盖所有原料宽度，请检查。")

        # 查找每个原材料属于哪个价格区间
        idx = np.searchsorted(cost_df.start_width.values,
                              self.raw_materials.width.values,
                              side="right")  # 价格区间为左开右闭

        # 将每一种原料的价格存储在raw_materials DataFrame里面
        self.raw_materials["cost"] = [cost_df.loc[i - 1, "cost"] for i in idx]
        return self.raw_materials

    def get_cost_df(self):
        cost_df = pd.DataFrame({"start_width": [1000, 1200],
                                "cost": [4240, 4190]})
        self.cost_df = cost_df.sort_values(by="start_width", ignore_index=True)
        self.set_cost()
        return self.cost_df

    def solve(self, max_patterns, min_l=0):
        # 原材料
        self.get_raw_materials()

        # 成品
        self.get_products()

        # 价格表
        self.get_cost_df()

        # 生成所有的裁剪方案
        generator = CuttingPatterns(raw_materials=self.raw_materials, products=self.products)
        raw_matrices = generator.generate(cost_df=self.cost_df)  # {width:DataFrame(Patterns)}
        trim_width = {}  # {(raw_width, pattern_index) : trim_width}
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
        objective = solver.Objective()  # 目标为使用原材料的价值最小
        for (w, p), var in l.items():
            cost = self.raw_materials[self.raw_materials.width == w].iloc[0]["cost"]  # 此宽度原料的价格
            trim_width[(w, p)] = CuttingPatterns.trim_width(raw_width=w,
                                                            pattern=raw_matrices[w].loc[p],
                                                            products=self.products)
            width_cost = float(w * cost - trim_width[(w, p)] * cost / 2)  # 边丝折损一半货值

            objective.SetCoefficient(var, width_cost)
        objective.SetMinimization()

        # 约束条件1: 每种成品的总长度均被满足
        for p, width in enumerate(self.products.width):
            # 对每种成品，添加约束，使得该成品的总长度不低于要求。
            lower_bound = float(self.products.loc[p, "total_length"])
            constraint = solver.Constraint(lower_bound, solver.infinity())
            for (w, j), var in l.items():
                coeff = float(raw_matrices[w].iloc[j, p])
                constraint.SetCoefficient(var, coeff)

        # 约束条件2：使用的pattern数不超过限制
        constraint = solver.Constraint(0, max_patterns)
        for (w, j), var in y.items():
            constraint.SetCoefficient(var, 1)

        # 约束条件3: 限制长度为0时，使用标记y必须为0
        M = 1e11
        for (w, j), var in l.items():
            solver.Add(var <= y[(w, j)] * M)

        # 求解
        status = solver.Solve()

        # 输出结果
        if status == pywraplp.Solver.OPTIMAL:
            print("已找到最优解！")

            # 初始化结果DataFrame
            col = ["raw_width"] + self.products.width.tolist() + ["len_used", "trim_width"]
            result = pd.DataFrame(columns=col)

            for (w, j), var in y.items():
                if var.solution_value() > 0:
                    pattern = raw_matrices[w].iloc[j]
                    new_row = {"raw_width": w,
                               "len_used": l[(w, j)].solution_value(),
                               "trim_width": trim_width[(w, j)]}
                    for width in self.products.width:
                        new_row[width] = pattern[width]

                    result = pd.concat([result, pd.DataFrame([new_row])], ignore_index=True)
            return result
        else:
            print("未找到最优解")
            return None

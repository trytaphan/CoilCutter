import pandas as pd
import streamlit as st
import math


# import openpyxl


class SupportBracket:
    property_list = ["shape", "height", "dimension_B", "dimension_C", "thickness",
                     "length", "specification", "height_t", "dimension_B_t",
                     "dimension_C_t", "thickness_t", "specification_t", "unfolded_width",
                     "count", "name", "grade", "diameter", "diameter_t", "material_type", "density"]

    English_Chinese_mapping = {
        "shape": "形状",
        "height": "高度",
        "dimension_B": "宽度",
        "dimension_C": "卷边宽度",
        "thickness": "厚度",
        "length": "长度",
        "specification": "规格",
        "height_t": "目标高度",
        "dimension_B_t": "目标宽度",
        "dimension_C_t": "目标卷边宽度",
        "thickness_t": "目标厚度",
        "specification_t": "目标规格",
        "count": "总数量",
        "grade": "材质",
        "name": "名称",
        "unfolded_width": "展开宽度",
        "raw_width": "原料宽度(mm)",
        "len_used": "使用长度(mm)",
        "trim_width": "边丝宽度(mm)",
        "diameter": "直径",
        "diameter_t": "目标直径",
        "material_type": "材料类型",
        "density": "密度(g/cm3)"
    }
    Chinese_English_mapping = \
        {chinese: english for english, chinese in English_Chinese_mapping.items()}
    # 不同材料的密度，单位g/cm3
    DENSITY = {"锌铝镁": 7.1,
               "低碳钢": 7.85
               }

    # 检查一下是不是都有翻译
    for prop in property_list:
        if not prop in English_Chinese_mapping:
            raise ValueError("SupportBrackets: 有属性未翻译！")

    def __init__(self, count=0, specification=None):
        """
        specification: 规格，如C100*35*10*2.5*9775
        """
        if specification is None:
            # 为空对象设置默认值
            self.shape = ""
            self.height = 0
            self.dimension_B = 0
            self.dimension_C = 0
            self.thickness = 0
            self.length = 0
            self.diameter = 0
            self.specification = ""
        else:
            # 解析规格
            self.parse_specification(specification)
            # 计算目标尺寸
            self.init_target_dimensions()

        # 其他属性
        self.count = count

    @staticmethod
    def validate_specification(spec: str):
        # 预处理，变为大写，去除所有空格，替换φ的错误写法Ø
        spec = spec.upper().replace(" ", "").replace("Ø", "Φ")

        try:
            # 验证首字母
            shape = spec[0]
            if shape not in ["C", "U", "Φ"]:
                raise ValueError("规格应该以C、U或者Φ开头。")

            # 看看是不是只有首字母
            if len(spec) < 2:
                raise ValueError("规格必须带参数。")

            # 检查是否有空参数
            parts = spec[1:].split(sep="*")
            for part in parts:
                if part == "":
                    raise ValueError(f"有空参数（*前后没有数字，或者连用两个*）。")

            # 检查参数数量
            if shape == "Φ" and len(parts) != 3:
                raise ValueError("圆管应该有三个参数。")
            elif shape == "U" and len(parts) != 4:
                raise ValueError(f"U型钢应该有4个参数。")
            elif shape == "C" and len(parts) != 5:
                raise ValueError(f"C型钢应该有5个参数。")


        except ValueError as e:
            st.warning(f"请检查规格{spec}: {e}")
            return False

        # 验证参数是否为数值
        try:
            [float(part) for part in parts]
        except ValueError:
            st.warning(f"请检查规格{spec}: 包含非数字的参数。")
            return False

        return True

    @staticmethod
    def _parse_spec(spec: str):
        # 预处理，变为大写，去除所有空格，替换φ的错误写法Ø
        spec = spec.upper().replace(" ", "").replace("Ø", "Φ")

        # 检查规格字符串规范性
        SupportBracket.validate_specification(spec)

        # 解析
        shape = spec[0]
        parts = [float(p) for p in spec[1:].split("*")]

        # 分类型解析
        if shape == "C":
            # C型钢直接解析5个参数
            height, dimension_B, dimension_C, thickness, length = parts
            diameter = 0.0
        elif shape == "U":
            parts.insert(2, 0)
            height, dimension_B, dimension_C, thickness, length = parts  # 按顺序赋值
            diameter = 0.0
        elif shape == "Φ":
            diameter, thickness, length = parts
            height, dimension_B, dimension_C = [0.0] * 3

        return (shape, height, dimension_B, dimension_C, thickness, length, diameter, spec)

    def parse_specification(self, specification=None):
        """解析规格"""
        # 允许按指定的规格解析，默认使用实例属性
        if specification is not None:
            specification = specification
        else:
            specification = self.specification

        # 解析
        (self.shape, self.height, self.dimension_B, self.dimension_C, self.thickness,
         self.length, self.diameter, self.specification) = SupportBracket._parse_spec(specification)

    def update_target_dimensions(self, spec_t=None):
        """利用已有的目标规格计算其他属性"""
        if spec_t is not None:
            spec_t = spec_t.replace(" ", "")
        else:
            spec_t = self.specification_t.replace(" ", "")

        # 解析
        (self.shape, self.height_t, self.dimension_B_t, self.dimension_C_t, self.thickness_t,
         self.length, self.diameter_t, self.specification_t) = SupportBracket._parse_spec(spec_t)


    def init_target_dimensions(self):
        """目标尺寸：实际生产时要达到的尺寸"""
        if self.shape == "C":
            self.height_t = self.height - 1
            self.dimension_B_t = self.dimension_B - 1
            self.dimension_C_t = self.dimension_C - 0.5
            self.thickness_t = self.thickness
            self.specification_t = (f"{self.shape}{self.height_t}*{self.dimension_B_t}*{self.dimension_C_t}"
                                    f"*{self.thickness_t}*{self.length}")
        elif self.shape == "U":
            self.height_t = self.height - 1
            self.dimension_B_t = self.dimension_B - 1
            self.dimension_C_t = 0
            self.thickness_t = self.thickness
            self.specification_t = (f"{self.shape}{self.height_t}*{self.dimension_B_t}"
                                    f"*{self.thickness_t}*{self.length}")
        elif self.shape == "Φ":
            # 圆管处理逻辑
            self.diameter_t = self.diameter
            self.thickness_t = self.thickness
            self.specification_t = f"{self.shape}{self.diameter_t}*{self.thickness_t}*{self.length}"
    def to_dict(self):
        return {str(prop): getattr(self, prop, None) for prop in self.property_list}

    @property
    def unfolded_width(self):
        if hasattr(self, "_unfolded_width") and self._unfolded_width is not None:
            return self._unfolded_width
        else:
            return self.calculate_unfolded_width()

    @unfolded_width.setter
    def unfolded_width(self, value):
        self._unfolded_width = value

    def calculate_unfolded_width(self):
        if self.shape == "C":
            # C型展开公式: H + 2B + 2C - 8t
            return (
                    self.height_t
                    + self.dimension_B_t * 2
                    + self.dimension_C_t * 2
                    - self.thickness_t * 8
            )
        elif self.shape == "U":
            # U型展开公式: H + 2B + 2C - 4t, 正常情况没有卷边C
            return (
                    self.height_t
                    + self.dimension_B_t * 2
                    + self.dimension_C_t * 2
                    - self.thickness_t * 4
            )
        elif self.shape == "Φ":
            # 圆管展开宽度 = π*(D - t)
            return round(math.pi * (self.diameter_t - self.thickness_t), 2)
        else:
            pass
            # raise ValueError(f"不支持的类型：{self.shape}")

    @staticmethod
    def from_dataframe(df, idx, re_parse=False):
        """用指定DataFrame的idx行填充实例属性"""
        inst = SupportBracket()
        for prop in df.columns:
            setattr(inst, prop, df.loc[idx, prop])
        if re_parse:
            inst.parse_specification()
        return inst


class Brackets:
    def __init__(self):
        self.list = []

    def add_bracket(self, bracket: SupportBracket):
        """添加一个新的 bracket 到列表"""
        self.list.append(bracket)
        return self

    def remove_bracket(self, idx: int):
        """删除指定索引的bracket"""
        if 0 <= idx < len(self.list):
            del self.list[idx]
        else:
            st.warning(f"remove_bracket:传入的索引{idx}不在目标范围内！")

    def to_dataframe(self):
        """转换为 DataFrame"""
        data = [bracket.to_dict() for bracket in self.list]
        return pd.DataFrame(data)

    def update_target_dimensions(self):
        for bracket in self.list:
            bracket.update_target_dimensions()

    def init_target_dimensions(self):
        for bracket in self.list:
            bracket.init_target_dimensions()

    @staticmethod
    def from_dataframe(df, re_parse=False):
        """从DataFrame加载"""
        df = df.fillna(0)
        b = Brackets()
        b.list = [SupportBracket.from_dataframe(df, idx, re_parse) for idx in df.index]
        return b

    @staticmethod
    def from_csv(file_path):
        df = pd.read_csv(file_path)
        return Brackets.from_dataframe(df)

    def to_csv(self, file_path):
        df = self.to_dataframe()
        df.to_csv(file_path, index=False)

    @staticmethod
    def from_excel(file_path, re_parse=False):
        df = pd.read_excel(file_path, engine="openpyxl")
        df = display_in_English(df)
        return Brackets.from_dataframe(df, re_parse)


def display_in_Chinese(df):
    return df.rename(columns=SupportBracket.English_Chinese_mapping)


def display_in_English(df):
    return df.rename(columns=SupportBracket.Chinese_English_mapping)

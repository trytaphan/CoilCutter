import pandas as pd
import streamlit as st
import openpyxl


class SupportBracket:
    property_list = ["shape", "height", "dimension_B", "dimension_C", "thickness",
                     "length", "specification", "height_t", "dimension_B_t",
                     "dimension_C_t", "thickness_t", "specification_t", "unfolded_width",
                     "count", "name", "grade"]

    English_Chinese_mapping = {
        "shape": "形状",
        "height": "高度",
        "dimension_B": "宽度B",
        "dimension_C": "宽度C",
        "thickness": "厚度",
        "length": "长度",
        "specification": "规格",
        "height_t": "目标高度",
        "dimension_B_t": "目标宽度B",
        "dimension_C_t": "目标宽度C",
        "thickness_t": "目标厚度",
        "specification_t": "目标规格",
        "count": "总数量",
        "grade": "材质",
        "name": "名称",
        "unfolded_width": "展开宽度"
    }
    Chinese_English_mapping = \
        {chinese: english for english, chinese in English_Chinese_mapping.items()}

    # 检查一下是不是都有翻译
    if not len(property_list) == len(Chinese_English_mapping):
        raise ValueError("SupportBrackets: 有属性未翻译或者有属性没加入property_list！")
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
            self.specification = ""
        else:
            # 解析规格
            self.parse_specification(specification)
            # 计算目标尺寸
            self.init_target_dimensions()

        # 其他属性
        self.count = count

    def parse_specification(self, specification=None):
        """解析规格"""
        if specification is not None:
            specification = specification.replace(" ", "")
        else:
            specification = self.specification
        SupportBracket.check_specification(specification)
        self.shape = specification[0]
        spec_dict = specification[1:].split(sep="*")
        self.height = float(spec_dict[0])
        self.dimension_B = float(spec_dict[1])
        self.dimension_C = float(spec_dict[2])
        self.thickness = float(spec_dict[3])
        self.length = float(spec_dict[4])
        self.specification = specification

    def init_target_dimensions(self):
        """目标尺寸：实际生产时要达到的尺寸"""
        self.height_t = self.height - 1
        self.dimension_B_t = self.dimension_B - 1
        self.dimension_C_t = self.dimension_C - 0.5
        self.thickness_t = self.thickness
        self.specification_t = (f"{self.shape}{self.height_t}*{self.dimension_B_t}*{self.dimension_C_t}"
                                f"*{self.thickness_t}*{self.length}")

    def update_target_dimensions(self, spec_t=None):
        """利用已有的目标规格计算其他属性"""
        if spec_t is not None:
            spec_t = spec_t.replace(" ", "")
        else:
            spec_t = self.specification_t
        SupportBracket.check_specification(spec_t)
        spec_dict = spec_t[1:].split(sep="*")
        self.height_t = float(spec_dict[0])
        self.dimension_B_t = float(spec_dict[1])
        self.dimension_C_t = float(spec_dict[2])
        self.thickness_t = float(spec_dict[3])
        self.length = float(spec_dict[4])
        self.specification_t = spec_t

    def to_dict(self):
        return {str(prop): getattr(self, prop, None) for prop in self.property_list}

    @property
    def unfolded_width(self):
        return self.height_t + self.dimension_B_t * 2 +self.dimension_C_t * 2 - self.thickness_t * 9



    @staticmethod
    def check_specification(specification):
        spec = specification.replace(" ", "")
        try:
            if spec.count("*") != 4:
                raise ValueError(r"*不是4个。")
            if not spec.startswith(("C")):
                raise ValueError("不是以C开头。")
        except Exception as e:
            print(f"请检查规格{spec}: {e}")
            st.warning(f"请检查规格{spec}: {e}")


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

    def prepare4solution(self):
        df = self.to_dataframe()[["unfolded_width"]].copy()
        df.rename(columns={"unfolded_width": "width"}, inplace=True)
        return df



def display_in_Chinese(df):
    return df.rename(columns=SupportBracket.English_Chinese_mapping)


def display_in_English(df):
    return df.rename(columns=SupportBracket.Chinese_English_mapping)



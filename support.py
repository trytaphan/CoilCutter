import pandas as pd

class SupportBracket:
    property_list = ["shape", "height", "dimension_B", "dimension_C", "thickness",
                     "length", "specification", "height_r", "dimension_B_r",
                     "dimension_C_r", "thickness_r", "specification_r", "count"]

    chinese_mapping = {
        "shape": "形状",
        "height": "高度",
        "dimension_B": "宽度B",
        "dimension_C": "宽度C",
        "thickness": "厚度",
        "length": "长度",
        "specification": "规格",
        "height_r": "实际高度",
        "dimension_B_r": "实际宽度B",
        "dimension_C_r": "实际宽度C",
        "thickness_r": "实际厚度",
        "specification_r": "实际规格",
        "count": "数量"
    }

    def __init__(self, is_empty=False, count=0, specification=None):
        """
        specification: 规格，如C100*35*10*2.5*9775
        """
        if is_empty:
            return

        # 解析规格
        specification = specification.replace(" ", "")
        self.shape = specification[0]
        spec_dict = specification[1:].split(sep="*")
        self.height = float(spec_dict[0])
        self.dimension_B = float(spec_dict[1])
        self.dimension_C = float(spec_dict[2])
        self.thickness = float(spec_dict[3])
        self.length = float(spec_dict[4])
        self.specification = specification

        # 其他属性
        self.count = count

    # 实际生产规格
    @property
    def height_r(self):
        return self.height - 1

    @property
    def dimension_B_r(self):
        return self.dimension_B - 1

    @property
    def dimension_C_r(self):
        return self.dimension_C - 0.5

    @property
    def thickness_r(self):
        return self.thickness

    @property
    def specification_r(self):
        """返回实际规格字符串"""
        return (f"{self.shape}{self.height_r}*{self.dimension_B_r}*{self.dimension_C_r}"
                f"*{self.thickness_r}*{self.length}")

    def to_dict(self):
        return {str(prop):getattr(self, prop) for prop in self.property_list}

    @staticmethod
    def display_in_CN(df):
        return df.rename(columns = SupportBracket.chinese_mapping)

    @staticmethod
    def prepare_products(brackets):
        pass

    @staticmethod
    def load_from_dataframe(df, idx):
        """"从具备全部属性的dataframe里加载"""
        inst = SupportBracket(empty=True)
        for prop in SupportBracket.property_list:
            setattr(inst, prop, df.loc[idx, str(prop)])
        return inst


class Brackets:
    def __init__(self):
        self.brackets = []

    def add_bracket(self, bracket:SupportBracket):
        """添加一个新的 bracket 到列表"""
        self.brackets.append(bracket)

    def remove_bracket(self, idx:int):
        """删除指定索引的bracket"""
        if 0 <= idx < len(self.brackets):
            del self.brackets[idx]

    def to_dataframe(self):
        """转换为 DataFrame"""
        data = [bracket.to_dict() for bracket in self.brackets]
        return pd.DataFrame(data, columns = SupportBracket.property_list)

    @staticmethod
    def load_from_dataframe(df):
        """从DataFrame加载"""
        return [SupportBracket.load_from_dataframe(df, idx) for idx in df.index]


if __name__ == '__main__':
    a = SupportBracket(" C 100*35*10*2.5*9775", 5)
    # b = SupportBracket("H200*150*3.2*4.5*2000")
    # d = SupportBracket("C100*35*10*2.5*9775")
    print(a.to_dict())
    df = pd.DataFrame(columns=SupportBracket.property_list)
    # print(len(df.index))
    # df.loc[len(df.index)] = a.to_dict()
    # df.loc[len(df.index)] = b.to_dict()

    print(df)
    print(a.specification)
    print(a.specification_r)
    print(SupportBracket.display_in_CN(df))

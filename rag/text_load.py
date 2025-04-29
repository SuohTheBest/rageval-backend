import json
import os
import sys
import re  # 将正则表达式模块移到顶部导入

# 添加opencc库导入
from opencc import OpenCC

sys.path.append("./")

import logging
from sqlalchemy.exc import SQLAlchemyError
from models.Text import RAGText
from models.database import Base, SessionLocal, engine

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def read_json_file(file_path):
    """读取JSON文件并返回解析后的数据"""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        logger.info(f"成功读取JSON文件: {file_path}")
        return data
    except Exception as e:
        logger.error(f"读取JSON文件失败: {str(e)}")
        return None


def clean_and_validate_content(content_str, cc):
    """
    清洗和验证内容文本

    执行以下操作:
    1. 删除空的中括号对[]和空的大括号对{}
    2. 删除不可渲染字符
    3. 检查内容长度是否至少为20
    4. 将繁体中文转换为简体中文

    参数:
    content_str - 要清洗的原始内容字符串
    cc - OpenCC转换器实例

    返回:
    清洗后的内容字符串，如果内容长度小于20则返回None
    """
    # 删除空的中括号对[]和空的大括号对{}
    content_str = re.sub(r"\[\s*\]", "", content_str)
    content_str = re.sub(r"\{\s*\}", "", content_str)

    # 删除不可渲染字符
    content_str = re.sub(r"\\x[0-9a-fA-F]{2}", "", content_str)
    content_str = re.sub(r"\\u[0-9a-fA-F]{4}", "", content_str)
    content_str = content_str.replace("\xa0", "").replace("\u2002", "")

    # 如果内容长度小于20，返回None
    if len(content_str) < 20:
        return None

    # 将内容从繁体转换为简体
    content_str = cc.convert(content_str)

    return content_str


def combine_text_contents(data):
    """
    组合文本内容，处理短内容合并逻辑

    执行以下操作:
    1. 清洗和验证每个内容
    2. 处理短内容(长度小于50)的合并逻辑
    3. 组合成最终文本格式

    参数:
    data - 原始JSON数据

    返回:
    组合后的文本列表，格式为"{item}\n---\n{title}:{content}"
    """
    text_list = []
    # 初始化繁体到简体的转换器
    cc = OpenCC("t2s")

    for item, content_dict in data.items():
        # 将字典转换为列表，以便我们可以按顺序访问并知道"下一个"元素
        titles_contents = list(content_dict.items())
        i = 0
        pending_content = ""  # 用于存储待合并的短内容

        while i < len(titles_contents):
            title, content = titles_contents[i]
            content_str = str(content)

            # 清洗和验证内容
            cleaned_content = clean_and_validate_content(content_str, cc)

            if cleaned_content is None:
                i += 1
                continue

            # 处理短内容合并逻辑
            if pending_content:
                cleaned_content = f"{pending_content}\n{cleaned_content}"
                pending_content = ""

            # 检查当前内容是否需要合并到下一个
            if len(cleaned_content) < 50 and i + 1 < len(titles_contents):
                pending_content = f"{title}:{cleaned_content}"
                i += 1
                continue

            # 将item也转换为简体
            item_simplified = cc.convert(item)
            text = f"{item_simplified}\n---\n{title}:{cleaned_content}"
            text_list.append(text)
            i += 1

        # 处理最后一个短内容（如果存在）
        if pending_content:
            text_list.append(f"{cc.convert(item)}\n---\n{pending_content}")

    return text_list


def convert_to_text_list(data):
    """
    将JSON数据转换为文本列表
    格式: "{item}\n---\n{title}:{str(content)}"

    特性:
    1. 过滤掉内容长度小于20的条目
    2. 将繁体中文转换为简体中文
    3. 当内容长度小于50时，合并到下一个title
    4. 删除空的中括号对[]和空的大括号对{}
    5. 删除形如"\xa0"或"\u2002"这样的不可渲染字符
    """
    return combine_text_contents(data)


def insert_texts_to_db(text_list):
    """将文本列表插入到数据库"""
    session = SessionLocal()
    try:
        count = 0
        for text in text_list:
            rag_text = RAGText(text=text)
            session.add(rag_text)
            count += 1

            # 每100条记录提交一次，避免事务过大
            if count % 100 == 0:
                session.commit()
                logger.info(f"已插入 {count} 条记录")

        # 提交剩余的记录
        session.commit()
        logger.info(f"成功插入总计 {count} 条记录到数据库")
        return count
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"插入数据库失败: {str(e)}")
        return 0
    finally:
        session.close()


def load_texts_from_json(json_path):
    """从JSON文件加载文本并插入数据库"""
    # 检查文件是否存在
    if not os.path.exists(json_path):
        logger.error(f"文件不存在: {json_path}")
        return False

    # 读取JSON文件
    data = read_json_file(json_path)
    if not data:
        return False

    # 转换为文本列表
    text_list = convert_to_text_list(data)
    logger.info(f"从JSON文件生成了 {len(text_list)} 条文本记录")

    # 插入数据库
    inserted_count = insert_texts_to_db(text_list)
    return inserted_count > 0


def main(json_path=None):
    """主函数，处理命令行参数"""
    if not json_path:
        json_path = "./data/result_tools.json"  # 默认路径

    success = load_texts_from_json(json_path)
    if success:
        logger.info("数据加载完成")
    else:
        logger.error("数据加载失败")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    json_path = sys.argv[1] if len(sys.argv) > 1 else None
    main(json_path)

from sqlalchemy import inspect
from models.database import Base, engine

# 导入所有模型类，确保它们被注册到元数据中
from models.Text import RAGText
from models.Task import Task, UploadFile, DownloadFile
from models.User import User


def init_db():
    """
    初始化数据库表。如果表不存在，则创建表。
    返回创建的表名列表。
    """
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # 获取所有模型定义的表
    tables_to_create = []
    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            tables_to_create.append(table_name)

    # 如果有需要创建的表，则创建
    if tables_to_create:
        # 仅创建不存在的表
        Base.metadata.create_all(
            bind=engine,
            tables=[
                Base.metadata.tables[table_name] for table_name in tables_to_create
            ],
        )
        print(f"已创建数据库表: {', '.join(tables_to_create)}")
    else:
        print("数据库表已存在，无需创建")

    return tables_to_create


# 在模块导入时自动检查并创建表
created_tables = init_db()

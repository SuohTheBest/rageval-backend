import asyncio
from PIL import Image
import os
print("当前工作目录是：", os.getcwd())


async def get_team_recommend_double(hero_name: str) -> str:
    return f"static\\recommend\\{hero_name}_双排.jpg"


async def get_team_recommend_triple(hero_name: str) -> str:
    return f"static\\recommend\\{hero_name}_三排.jpg"
# 定义打开图片的主函数


def open_image():
    pic_path = asyncio.run(get_team_recommend_double("芈月"))
    img = Image.open(pic_path)
    img.show()
    pic_path = asyncio.run(get_team_recommend_triple("芈月"))
    img = Image.open(pic_path)
    img.show()


open_image()

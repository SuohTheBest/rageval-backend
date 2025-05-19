import requests
import os
import json
from tqdm import tqdm
from multiprocessing import Pool

def download_image(item):
    try:
        name = item["name"]
        image_url = item["image"]
        response = requests.get(image_url)
        os.makedirs(f"dataset/train/{name}", exist_ok=True)
        with open(f"dataset/train/{name}/{image_url.split('/')[-1]}", "wb") as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"下载失败: {image_url}, 错误: {str(e)}")
        return False

if __name__ == '__main__':
    # 读取JSON数据
    with open("./crawler/enemy.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 创建进程池,设置进程数
    pool = Pool(processes=4)  # 可以根据CPU核心数调整进程数
    
    # 使用进程池进行并行下载
    results = list(tqdm(
        pool.imap_unordered(download_image, data),
        total=len(data),
        desc="下载图片中",
        unit="张"
    ))
    
    # 关闭进程池
    pool.close()
    pool.join()
    
    # 统计下载结果
    success = results.count(True)
    failed = results.count(False)
    print(f"\n下载完成! 成功: {success}张, 失败: {failed}张")
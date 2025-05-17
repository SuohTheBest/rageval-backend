import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin
# 工具网页 URL
base_url = "https://terraria.wiki.gg"
page_url = f"{base_url}/zh/wiki/工具"

# 发送请求获取网页内容
response = requests.get(page_url)
html_content = response.text

# 使用 BeautifulSoup 解析 HTML
soup = BeautifulSoup(html_content, 'html.parser')

# 定义一个列表来存储提取的名称和链接
items = []

# 找到所有的 itemlist 容器
for itemlist in soup.find_all('div', class_='itemlist'):
    # 查找所有的 li 标签
    for li in itemlist.find_all('li'):
        # 查找包含链接的 span 标签（注意工具页面使用 -w 类）
        span = li.find('span', class_='i -w')
        if not span:
            span = li.find('span', class_='i')  # 有些可能没有 -w 类
        
        if span:
            # 获取链接（a标签）
            a_tag = span.find('a')
            
            # 提取名称和链接
            if a_tag and a_tag.get('href') and a_tag.get('title'):
                # 获取URL
                item_url = a_tag.get('href')
                
                # 确保URL是中文wiki链接
                if not item_url.startswith("/zh/wiki/"):
                    # 如果不是中文链接，转换为中文路径
                    if item_url.startswith("/wiki/"):
                        item_url = "/zh" + item_url
                    else:
                        continue  # 跳过非wiki链接
                
                # 提取中文名称（从 title 属性中提取）
                name = a_tag.get('title', '').strip()
                # 提取图片URL
                img_tag = a_tag.find('img')
                image_url = None
                if img_tag and img_tag.get('src'):
                    image_url = urljoin(base_url, img_tag.get('src'))
                if name:
                    items.append({
                        "name": name,
                        "image": image_url,
                        "url": urljoin(base_url, item_url)
                    })
                else:
                    print(f"跳过空名称的条目: {a_tag}")

# 将数据写入 JSON 文件
with open('./crawler/tools.json', 'w', encoding='utf-8') as json_file:
    json.dump(items, json_file, ensure_ascii=False, indent=4)

print(f"成功抓取 {len(items)} 个工具数据，已写入 tools.json 文件")
import requests
from bs4 import BeautifulSoup
import json

# 示例网页 URL
url = "https://terraria.wiki.gg/zh/wiki/武器"

# 发送请求获取网页内容
response = requests.get(url)
html_content = response.text

# 使用 BeautifulSoup 解析 HTML
soup = BeautifulSoup(html_content, 'html.parser')

# 定义一个列表来存储提取的名称和链接
items = []

# 找到所有的 infocard 容器
for infocard in soup.find_all('div', class_='infocard'):
    # 在 infocard 中查找 itemlist
    itemlist = infocard.find('div', class_='itemlist')
    if itemlist:
        # 查找所有的 li 标签
        for li in itemlist.find_all('li'):
            # 查找包含链接的 span 标签
            span = li.find('span', class_='i')
            if span:
                # 获取链接（a标签）
                a_tag = span.find('a')
                
                # 提取名称和链接
                if a_tag and a_tag.get('href') and a_tag.get('title'):
                    # 获取URL
                    url = a_tag.get('href')
                    
                    # 确保URL是中文wiki链接
                    if not url.startswith("/zh/wiki/"):
                        # 如果不是中文链接，转换为中文路径
                        if url.startswith("/wiki/"):
                            url = "/zh" + url
                        else:
                            continue  # 跳过非wiki链接
                    
                    # 提取中文名称（从 title 属性中提取）
                    name = a_tag.get('title', '').strip()
                    
                    # 确保 name 不为空
                    if name:
                        # 将提取的数据以字典形式存入列表
                        items.append({
                            "name": name,
                            "url": url
                        })
                    else:
                        print(f"跳过空名称的条目: {a_tag}")

# 将数据写入 JSON 文件
with open('./crawler/tools.json', 'w', encoding='utf-8') as json_file:
    json.dump(items, json_file, ensure_ascii=False, indent=4)

print(f"成功抓取 {len(items)} 个武器数据，已写入 tools.json 文件")
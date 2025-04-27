import json
import os.path
import time
import traceback

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

import re
import bs4

from webdriver_manager.chrome import ChromeDriverManager

# 自动下载匹配的 ChromeDriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)


def extract_tr(tr: bs4.element.Tag):
    delimiter = ', '
    th = tr.find('th', recursive=False)
    td = tr.find('td', recursive=False)
    
    # 特殊处理稀有度
    if '稀有度' in th.text:
        rarity_img = td.find('img')
        if rarity_img and 'alt' in rarity_img.attrs:
            return f"稀有度:{rarity_img['alt']};"
        return "稀有度:未知;"
    
    # 特殊处理卖出价格
    if '卖出' in th.text:
        coins = td.find_all('span', class_='coin')
        coin_values = []
        for coin in coins:
            if 'title' in coin.attrs:
                coin_values.append(coin['title'].replace(' ', ''))
        return f"卖出:{'/'.join(coin_values)};"
    
    # 其他情况的通用处理
    if '类型' in th.text or '伤害' in th.text or '击退' in th.text or '暴击率' in th.text or '使用时间' in th.text or '射弹速度' in th.text or '研究' in th.text:
        delimiter = ""
    
    if '钱币' in th.text:
        inner_money = td.find('span', class_='npcstat prefix')
        content = []
        if not inner_money:
            return ""
        for item in inner_money.contents:
            coins = item.find_all('span', class_='coin')
            match = []
            for coin in coins:
                if not 'title' in coin.attrs:
                    continue
                match.append(coin.attrs['title'].replace(' ', ''))
            content.append('›'.join(match))
        delimiter = '/'
    elif '免疫' in th.text:
        content = []
        imgs = td.find_all('img')
        for img in imgs:
            if not 'alt' in img.attrs:
                continue
            content.append(img.attrs['alt'])
    else:
        content = list(td.stripped_strings)
    
    content = map(lambda s: s.strip(), content)
    return th.text + ':' + delimiter.join(content) + ';'


def extract_infobox(infobox: bs4.element.Tag):
    ans = []
    current_item = {"种类": "", "详细数据": {}}
    
    for tag in infobox.contents:
        if not isinstance(tag, bs4.element.Tag):
            continue
        tag_class = tag.get('class', [])
        
        if 'title' in tag_class:
            # 如果遇到新的title且current_item不为空，则添加到ans并新建一个item
            if current_item["种类"] or current_item["详细数据"]:
                ans.append(current_item)
                current_item = {"种类": "", "详细数据": {}}
            current_item["种类"] = tag.text
        elif any(cls in tag_class for cls in ['statistics', 'debuff', 'projectile', 'drop']) and 'section' in tag_class:
            title = tag.find('div', class_='title', recursive=False)
            if title is None or title.text == '声音':
                continue
            content = ""
            if 'projectile' in tag_class:
                content = []
                ul_tag = tag.find('ul', class_='infobox-inline')
                if ul_tag:
                    li_tags = ul_tag.find_all('li')
                    for li in li_tags:
                        name_tag = li.find('div', class_='name')
                        if name_tag:
                            content.append(name_tag.text)
            elif 'drop' in tag_class and 'infobox' in tag_class and 'modesbox' in tag_class:
                sources = []
                table = tag.find('table', class_='drop-noncustom')
                if table:
                    rows = table.find_all('tr')[1:]  # 跳过表头
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 3:
                            entity_img = cols[0].find('img')
                            entity_name = cols[0].get_text(strip=True)
                            quantity = cols[1].get_text(strip=True)
                            chance = cols[2].get_text(strip=True)
                            source = {
                                '名称': entity_name,
                                '数量': quantity,
                                '几率': chance
                            }
                            sources.append(source)
                if sources:
                    content = {
                        '模式': '经典',  # 可以从modetabs中获取实际模式
                        '掉落列表': sources
                    }
            else:
                trs = tag.find_all('tr')
                for tr in trs:
                    content += extract_tr(tr)
            
            current_item["详细数据"][title.text] = content
    
    # 添加最后一个item
    if current_item["种类"] or current_item["详细数据"]:
        ans.append(current_item)
    
    return ans


def extract_recipe_table(table: bs4.element.Tag):
    recipes = []
    current_recipe = None
    last_station = ""  # 用于保存上一个配方的制作站
    
    # 处理tbody中的所有行
    tbody = table.find('tbody')
    if not tbody:
        return recipes
    
    rows = tbody.find_all('tr')
    for row in rows:
        # 检查是否是新的配方（有result单元格）
        result_cell = row.find('td', class_='result')
        if result_cell:
            # 如果有正在处理的配方，先保存
            if current_recipe:
                recipes.append(current_recipe)
            
            # 开始新的配方
            version_note = result_cell.find('div', class_='version-note')
            version_info = ""
            
            # 处理版本信息
            if version_note and "仅限" in version_note.text:
                # 提取所有版本图标
                version_icons = version_note.find_all('img')
                versions = []
                for icon in version_icons:
                    if 'alt' in icon.attrs:
                        versions.append(icon['alt'])
                if versions:
                    version_info = f"仅限{', '.join(versions)}"
            
            # 获取产物名称
            product_name = result_cell.find('span', class_='i multi-line')
            if not product_name:
                product_name = result_cell.find('span', class_='i')
            
            if product_name:
                product_name_text = product_name.get_text(strip=True)
            else:
                product_name_text = result_cell.get_text(strip=True)
            
            # 如果有版本信息，组合版本和产品名
            if version_info:
                product_name = f"{version_info}：{product_name_text}"
            else:
                # 检查是否有eico元素（版本图标）
                eico = result_cell.find('span', class_='eico')
                if eico and 'title' in eico.attrs:
                    version_info = eico['title']
                    product_name = f"{product_name_text}({version_info})"
                else:
                    product_name = product_name_text
            
            current_recipe = {
                '产物': product_name,
                '材料': [],
                '制作站': ''
            }
            
            # 处理材料
            ingredients = row.find('td', class_='ingredients')
            if ingredients:
                items = ingredients.find_all('li')
                for item in items:
                    # 处理材料中的版本信息
                    item_text = item.get_text(strip=True)
                    eico = item.find('span', class_='eico')
                    if eico and 'title' in eico.attrs:
                        version_info = eico['title']
                        item_text = f"{item_text}({version_info})"
                    current_recipe['材料'].append(item_text)
            
            # 处理制作站
            station = row.find('td', class_='station')
            if station:
                # 处理"或"关系的制作站
                station_text = station.get_text(' ', strip=True)
                # 替换多余的换行和空格
                station_text = ' '.join(station_text.split())
                current_recipe['制作站'] = station_text
                last_station = station_text
            elif last_station:  # 如果没有制作站信息，使用上一个配方的制作站
                current_recipe['制作站'] = last_station
        else:
            # 处理同一配方的其他材料行
            if current_recipe:
                ingredients = row.find('td', class_='ingredients')
                if ingredients:
                    items = ingredients.find_all('li')
                    for item in items:
                        # 处理材料中的版本信息
                        item_text = item.get_text(strip=True)
                        eico = item.find('span', class_='eico')
                        if eico and 'title' in eico.attrs:
                            version_info = eico['title']
                            item_text = f"{item_text}({version_info})"
                        current_recipe['材料'].append(item_text)
    
    # 添加最后一个配方
    if current_recipe:
        recipes.append(current_recipe)
    
    return recipes


def extract_page(url):
    driver.get('https://terraria.wiki.gg' + url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "bodyContent"))
    )
    element = driver.find_element(By.ID, "bodyContent")
    element_html = element.get_attribute("outerHTML")

    soup = BeautifulSoup(element_html, 'html.parser')

    main_div = soup.find_all('div', class_='mw-content-ltr mw-parser-output')

    assert len(main_div) == 1

    main_div = main_div[0]

    # 处理主要文字
    curr_key = "简介"
    curr_content = []
    data = {}
    for tag in main_div.contents:
        if not isinstance(tag, bs4.element.Tag):
            continue
        if tag.name == 'div':
            continue
        if tag.name == 'h2':
            data[curr_key] = curr_content
            curr_content = []
            curr_key = tag.text
            if curr_key == '历史' or curr_key == '歷史':
                break
            continue
        refs = tag.find_all('sup', class_='reference')
        for ref in refs:
            ref.decompose()
        text = tag.text
        cleaned_text = re.sub(r'\s+', '', text)
        if curr_key != '制作' and curr_key != '製作' and curr_key != '转化':
            curr_content.append(cleaned_text)
    if len(curr_content) > 0:
        data[curr_key] = curr_content
    curr_content = []
    
    # 处理边上的infobox
    info_boxes = main_div.find_all('div', class_='infobox')
    all_infobox_data = []
    for box in info_boxes:
        extracted = extract_infobox(box)
        all_infobox_data.extend(extracted)

    # 添加所有infobox数据
    if all_infobox_data:
        data["数据"] = all_infobox_data

    # 处理配方表格
    recipe_tables = main_div.find_all('table', class_='terraria')
    all_recipes = []
    for table in recipe_tables:
        if 'recipes' in table.get('class', []):
            recipe_data = extract_recipe_table(table)
            if recipe_data:
                all_recipes.extend(recipe_data)

    if all_recipes:
        data['配方'] = all_recipes
    
    return data


with open('./crawler/tools.json', 'r', encoding='utf-8') as f:
    all_pages = json.load(f)
all_results = {}
if os.path.exists("./crawler/result_tools.json"):
    with open('./crawler/result_tools.json', 'r', encoding='utf-8') as f:
        all_results = json.load(f)
try:
    for page in all_pages:
        curr_name = page['name']
        curr_url = page['url']
        if curr_name in all_results:
            continue
        data = extract_page(curr_url)
        all_results[curr_name] = data
        print(data)
        time.sleep(2)
except Exception as e:
    traceback.print_exc()

with open('./crawler/result_tools.json', 'w', encoding='utf-8') as f:
    js = json.dumps(all_results, ensure_ascii=False, indent=4)
    f.write(js)
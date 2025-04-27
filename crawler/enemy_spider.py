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
    if '伤害' in th.text or '生命值' in th.text or '抗性' in th.text or 'AI' in th.text:
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


def extract_prob(li: bs4.element.Tag):
    divs = []
    for content in li.contents:
        if not isinstance(content, bs4.element.Tag):
            continue
        if content.name != 'div':
            return None
        divs.append(content)
    if len(divs) != 2:
        return None
    name = divs[0].text
    prob = list(divs[1].stripped_strings)
    prob = prob[0]
    return name + '(' + prob + ');'


def extract_infobox(infobox: bs4.element.Tag):
    ans = {}
    name = ""
    for tag in infobox.contents:
        if not isinstance(tag, bs4.element.Tag):
            continue
        tag_class = tag.get('class', [])
        if 'title' in tag_class:
            name = tag.text
        elif 'statistics' in tag_class and 'section' in tag_class:
            title = tag.find('div', class_='title', recursive=False)
            if title is None or title.text == '声音':
                continue
            content = ""
            trs = tag.find_all('tr')
            for tr in trs:
                content += extract_tr(tr)
            ans[title.text] = content
        elif 'drops' in tag_class and 'section' in tag_class:
            title = tag.find('div', class_='title', recursive=False)
            if title is None:
                continue
            content = ""
            money = tag.find('table', class_='drops money', recursive=False)
            item = tag.find('ul', class_='drops items', recursive=False)
            if money:
                trs = money.find_all('tr')
                for tr in trs:
                    content += extract_tr(tr)
            if item:
                lis = item.find_all('li')
                for li in lis:
                    extracted = extract_prob(li)
                    if extracted:
                        content += extracted
            ans[title.text] = content
    return {"种类": name, "详细数据": ans}


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
            if curr_key == '历史':
                break
            continue
        refs = tag.find_all('sup', class_='reference')
        for ref in refs:
            ref.decompose()
        text = tag.text
        cleaned_text = re.sub(r'\s+', '', text)
        curr_content.append(cleaned_text)
    if len(curr_content) > 0:
        data[curr_key] = curr_content
    curr_content = []
    # 处理边上的infobox
    info_boxes = main_div.find_all('div', class_='infobox')
    for box in info_boxes:
        extracted = extract_infobox(box)
        curr_content.append(extracted)
    data["数据"] = curr_content
    return data


with open('./crawler/enemy.json', 'r', encoding='utf-8') as f:
    all_pages = json.load(f)
all_results = {}
if os.path.exists("./crawler/result2.json"):
    with open('./crawler/result2.json', 'r', encoding='utf-8') as f:
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

with open('./crawler/result2.json', 'w', encoding='utf-8') as f:
    js = json.dumps(all_results, ensure_ascii=False, indent=4)
    f.write(js)

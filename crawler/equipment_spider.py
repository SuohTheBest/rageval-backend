from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import time
import json

def parse_multiline_text(element):
    """处理包含<br>标签的多行文本，返回按行分隔的列表"""
    if not element:
        return []
    # 获取所有内容，包括文本和<br>标签
    contents = element.contents
    lines = []
    current_line = []
    
    for content in contents:
        if content.name == 'br':
            if current_line:  # 如果有内容，则加入lines
                lines.append(''.join(current_line).strip())
                current_line = []
        else:
            current_line.append(str(content))
    
    if current_line:  # 添加最后一行
        lines.append(''.join(current_line).strip())
    
    return lines

# 初始化浏览器
driver = webdriver.Chrome()  # 或指定路径：webdriver.Chrome(service=Service("chromedriver路径"))
driver.get("https://pvp.qq.com/web201605/item.shtml")  # 替换为实际装备页面
time.sleep(3)  # 等待页面加载

# 获取所有装备图标的元素（根据实际页面调整选择器）
equipment_icons = driver.find_elements("css selector", "#Jlist-details li a")  

equipment_data = []

# 遍历每个装备图标
for icon in equipment_icons:
    try:
        # 模拟鼠标悬停
        ActionChains(driver).move_to_element(icon).perform()
        time.sleep(0.5)  # 等待弹窗出现
        
        # 获取动态生成的弹窗HTML
        popup_html = driver.find_element("id", "popPupItem").get_attribute("outerHTML")
        soup = BeautifulSoup(popup_html, "html.parser")
        
        # 解析数据
        name = soup.find("h4", id="Jname").text.strip()
        price = soup.find("p", id="Jprice").text.split("：")[1].strip()
        total_price = soup.find("p", id="Jtprice").text.split("：")[1].strip()
        
        # 处理stats的多行文本
        stats_div = soup.find("div", id="Jitem-desc1")
        stats = parse_multiline_text(stats_div.find("p")) if stats_div else []
        
        # 处理passive_skill的多行文本
        skill_div = soup.find("div", id="Jitem-desc2")
        skill = parse_multiline_text(skill_div.find("p")) if skill_div else []
        
        equipment_data.append({
            "装备": name,
            "售价": price,
            "总价": total_price,
            "加成": stats,
            "技能": skill
        })
        
    except Exception as e:
        print(f"处理 {icon.get_attribute('alt')} 时出错: {e}")

# 关闭浏览器
driver.quit()

# 保存数据
with open("./crawler/equipment_details.json", "w", encoding="utf-8") as f:
    json.dump(equipment_data, f, ensure_ascii=False, indent=2)

print(f"成功爬取 {len(equipment_data)} 件装备的详细信息！")
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import time
import os

def parse_skill_description(desc):
    """处理技能描述中的<br>标签，返回按行分隔的列表"""
    if not desc:
        return []
    contents = desc.contents
    lines = []
    current_line = []
    
    for content in contents:
        if content.name == 'br':
            if current_line:
                lines.append(''.join(current_line).strip())
                current_line = []
        else:
            current_line.append(str(content))
    
    if current_line:
        lines.append(''.join(current_line).strip())
    
    return lines

def scrape_hero_skills(hero_name, hero_url):
    """爬取单个英雄的技能数据"""
    driver = webdriver.Chrome()
    try:
        driver.get(hero_url)
        time.sleep(3)  # 等待页面加载

        # 等待技能区域加载完成
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "skill-show"))
            )
        except:
            print(f"英雄 {hero_name} 页面可能没有技能展示区域")
            return None

        # 获取技能区域的HTML
        try:
            skill_html = driver.find_element(By.CLASS_NAME, "skill-show").get_attribute("outerHTML")
        except:
            print(f"无法获取英雄 {hero_name} 的技能HTML")
            return None
            
        soup = BeautifulSoup(skill_html, "html.parser")

        skills = []
        
        # 提取所有技能
        for skill_div in soup.find_all("div", class_="show-list"):
            # 提取技能名称、冷却值和消耗
            name_tag = skill_div.find("p", class_="skill-name")
            if not name_tag:
                continue
                
            name = name_tag.find("b").text.strip()
            
            # 提取冷却值和消耗
            spans = name_tag.find_all("span")
            cooldown = spans[0].text.replace("冷却值：", "").strip() if len(spans) > 0 else ""
            cost = spans[1].text.replace("消耗：", "").strip() if len(spans) > 1 else ""
            
            # 提取技能描述并处理多行文本
            desc_tag = skill_div.find("p", class_="skill-desc")
            description = parse_skill_description(desc_tag) if desc_tag else []
            if name:
                skills.append({
                    "skill_name": name,
                    "cooldown": cooldown,
                    "cost": cost,
                    "description": description
                })
        
        return {
            "hero": hero_name,
            "skills": skills
        }
        
    except Exception as e:
        print(f"爬取英雄 {hero_name} 时发生错误: {str(e)}")
        return None
    finally:
        driver.quit()

def load_heroes_list(json_file):
    """从JSON文件加载英雄列表"""
    if not os.path.exists(json_file):
        print(f"错误: 文件 {json_file} 不存在")
        return []
    
    with open(json_file, 'r', encoding='utf-8') as f:
        try:
            heroes = json.load(f)
            return heroes
        except json.JSONDecodeError:
            print(f"错误: 文件 {json_file} 不是有效的JSON格式")
            return []

def scrape_all_heroes_skills(input_json, output_json):
    """爬取所有英雄的技能数据"""
    heroes = load_heroes_list(input_json)
    if not heroes:
        return
    
    all_hero_skills = []
    
    for hero in heroes:
        print(f"正在爬取英雄: {hero['hero']}...")
        hero_data = scrape_hero_skills(hero['hero'], hero['url'])
        if hero_data:
            all_hero_skills.append(hero_data)
            print(f"已成功爬取 {hero['hero']} 的 {len(hero_data['skills'])} 个技能")
        else:
            print(f"跳过英雄 {hero['hero']}，爬取失败")
        
        # 每个英雄爬取后暂停一下，避免请求过于频繁
        time.sleep(2)
    
    # 保存所有英雄的技能数据
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(all_hero_skills, f, ensure_ascii=False, indent=2)
    
    print(f"\n已完成! 共爬取 {len(all_hero_skills)} 个英雄的技能数据")
    print(f"数据已保存到 {output_json}")

if __name__ == "__main__":
    # 输入和输出文件路径
    INPUT_JSON = "./crawler/heroes_full.json"  # 包含英雄列表的JSON文件
    OUTPUT_JSON = "./crawler/heroes_skills.json"  # 输出技能数据的JSON文件
    
    # 开始爬取
    scrape_all_heroes_skills(INPUT_JSON, OUTPUT_JSON)
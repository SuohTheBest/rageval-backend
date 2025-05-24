import json

with open('./crawler/heroes_skills.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for hero in data:
    hero["skills"] = [
        skill for skill in hero["skills"]
        if skill["skill_name"].strip() != "" or skill["description"]
    ]

with open('./crawler/heroes_skills_clean.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
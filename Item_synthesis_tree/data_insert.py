from neo4j import GraphDatabase
import json
from tqdm import tqdm
from typing import Union, List, Dict, Tuple

URI = "neo4j+s://7c083033.databases.neo4j.io"
USER = "neo4j"
PASSWORD = "YhqctoPsXJz6PVobPXApV-IG8_vTfWKNkt5ilqBlMKo"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def validate_recipe_json(raw_data: dict) -> Tuple[bool, List[Dict[str, Union[str, int]]]]:
    """校验 JSON 结构是否符合预期格式，返回是否通过与错误列表"""
    errors = []
    if "合成站" not in raw_data or not isinstance(raw_data["合成站"], dict):
        return False, [{"error": "顶层缺少 '合成站' 或格式错误"}]

    for station, recipes in raw_data["合成站"].items():
        if not isinstance(recipes, list):
            errors.append({"station": station, "error": "recipes 应为 list"})
            continue
        for idx, recipe in enumerate(recipes):
            if "生成物" not in recipe or not isinstance(recipe["生成物"], str):
                errors.append({"station": station, "index": idx, "error": "缺少 '生成物' 或类型错误"})
            if "材料" not in recipe or not isinstance(recipe["材料"], list):
                errors.append({"station": station, "index": idx, "error": "缺少 '材料' 或类型错误"})
            else:
                for m_idx, mat in enumerate(recipe["材料"]):
                    if "名称" not in mat or "数量" not in mat:
                        errors.append({"station": station, "index": idx, "error": f"第 {m_idx} 个材料缺少字段"})
                    elif not isinstance(mat["名称"], str) or not isinstance(mat["数量"], int):
                        errors.append({"station": station, "index": idx, "error": f"第 {m_idx} 个材料字段类型错误"})

    return len(errors) == 0, errors

def insert_recipes_from_json(file_path: str) -> Union[str, List[Dict]]:
    """验证 JSON 并将数据批量插入 Neo4j"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        return [{"error": f"文件读取失败: {str(e)}"}]

    is_valid, errors = validate_recipe_json(raw_data)
    if not is_valid:
        return errors

    data = []
    for station, recipes in tqdm(raw_data["合成站"].items(), desc="解析合成数据"):
        for recipe in recipes:
            data.append({
                "station": station,
                "product": recipe["生成物"],
                "materials": [
                    {"name": m["名称"], "amount": m["数量"]}
                    for m in recipe["材料"]
                ]
            })

    cypher_query = """
    UNWIND $data AS row
    MERGE (p:Item {name: row.product})
    MERGE (s:Station {name: row.station})
    MERGE (p)-[:CRAFTED_AT]->(s)
    WITH p, row
    UNWIND row.materials AS mat
    MERGE (m:Item {name: mat.name})
    MERGE (p)-[:REQUIRES {amount: mat.amount}]->(m)
    """

    batch_size = 1000
    total = len(data)
    with driver.session() as session:
        for i in tqdm(range(0, total, batch_size), desc="批量导入"):
            batch = data[i:i+batch_size]
            session.run(cypher_query, data=batch)

    return "✅ 数据校验通过，已成功导入 Neo4j"

if __name__ == "__main__":

    # ✅ 使用示例
    result = insert_recipes_from_json("data/knowledge_library/terraria_recipes_merged.json")
    if isinstance(result, str):
        print(result)
    else:
        print("❌ 格式错误：")
        for err in result:
            print(err)
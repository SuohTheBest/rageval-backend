from neo4j import GraphDatabase

URI = "neo4j+s://7c083033.databases.neo4j.io"
USER = "neo4j"
PASSWORD = "YhqctoPsXJz6PVobPXApV-IG8_vTfWKNkt5ilqBlMKo"
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def get_crafting_info(item_name: str) -> dict:
    '''
    输入：
    item_name: "弱效生命药水"
    输出：
    {
        "station": "炼药台",
        "materials": [
            {"name": "玻璃瓶", "amount": 2},
            {"name": "凝胶", "amount": 2},
            {"name": "蘑菇", "amount": 1}
        ]
    }
    '''
    regex = f"^{item_name}(×.*)"
    query = """
    MATCH (p:Item)
    WHERE p.name =~ $regex
    OPTIONAL MATCH (p)-[:CRAFTED_AT]->(s:Station)
    OPTIONAL MATCH (p)-[r:REQUIRES]->(m:Item)
    RETURN s.name AS station, collect({name: m.name, amount: r.amount}) AS materials
    """
    with driver.session() as session:
        result = session.execute_read(_query_crafting_info, item_name)
        return result

def _query_crafting_info(tx, item_name):
    record = tx.run(query, regex=regex).single()
    if record:
        return {
            "station": record["station"],
            "materials": [
                {"name": m["name"], "amount": m["amount"]}
                for m in record["materials"] if m["name"] is not None
            ]
        }
    else:
        return {"station": None, "materials": []}
    
def build_crafting_tree(item_name: str, max_depth: int = 2) -> dict:
    '''
    输入：
    item_name: "黑曜石踏水靴"
    max_depth: 2
    输出：
    {
        "name": "黑曜石踏水靴",
        "station": "工匠作坊",
        "materials": [
            {
                "name": "黑曜石头骨",
                "station": "熔炉",
                "materials": [
                    {"name": "黑曜石", "station": None, "materials": [], "amount": 20}
                ],
                "amount": 1
            },
            {
                "name": "踏水靴",
                "station": None,
                "materials": [],
                "amount": 1
            }
        ]
    }
    '''
    def _recursive(tx, item_name, depth):
        if depth > max_depth:
            return {"name": item_name, "station": None, "materials": []}

        regex = f"^{item_name}(×.*)?"
        query = """
        MATCH (p:Item)
        WHERE p.name =~ $regex
        OPTIONAL MATCH (p)-[:CRAFTED_AT]->(s:Station)
        OPTIONAL MATCH (p)-[r:REQUIRES]->(m:Item)
        RETURN p.name AS name, s.name AS station, collect({name: m.name, amount: r.amount}) AS materials
        """
        record = tx.run(query, regex=regex).single()

        if not record:
            return {"name": item_name, "station": None, "materials": []}

        materials = []
        for m in record["materials"]:
            if m["name"] is not None:
                sub_info = _recursive(tx, m["name"], depth + 1)
                sub_info["amount"] = m["amount"]
                materials.append(sub_info)

        return {
            "name": record["name"],
            "station": record["station"],
            "materials": materials
        }

    with driver.session() as session:
        return session.execute_read(_recursive, item_name, 0)

if __name__ == "__main__":
    item_name = "黑曜石踏水靴"
    #api1
    tree = build_crafting_tree(item_name, max_depth=2)
    #api2
    info = get_crafting_info(item_name)
    print(crafting_info)
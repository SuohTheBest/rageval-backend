from neo4j import AsyncGraphDatabase

URI = "neo4j+s://7c083033.databases.neo4j.io"
USER = "neo4j"
PASSWORD = "YhqctoPsXJz6PVobPXApV-IG8_vTfWKNkt5ilqBlMKo"
driver = AsyncGraphDatabase.driver(URI, auth=(USER, PASSWORD))


async def get_crafting_info(item_name: str) -> dict:
    '''
    输入：
    item_name: "毒瓶"
    输出：
    {
        "station": "浸泡装置",
        "materials": [
            {"name": "瓶装水", "amount": 1},
            {"name": "毒刺", "amount": 5}
        ]
    }
    '''

    async def _query_crafting_info(tx, item_name):
        regex = f"^{item_name}(×.*)?"
        query = """
        MATCH (p:Item)
        WHERE p.name =~ $regex
        OPTIONAL MATCH (p)-[:CRAFTED_AT]->(s:Station)
        OPTIONAL MATCH (p)-[r:REQUIRES]->(m:Item)
        RETURN p.name AS name, s.name AS station, collect({name: m.name, amount: r.amount}) AS materials
        """
        record = await tx.run(query, regex=regex)
        record = await record.single()
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

    async with driver.session() as session:
        return await session.execute_read(_query_crafting_info, item_name)


async def build_crafting_tree(item_name: str, max_depth: int = 2) -> dict:
    '''
    输入：
    item_name: "毒瓶"
    max_depth: 2
    输出：
    {
        "name": "毒瓶",
        "station": "浸泡装置",
        "materials": [
            {
                "name": "瓶装水",
                "station": "水",
                "materials": [
                    {"name": "玻璃瓶", "station": None, "materials": [], "amount": 1}
                ],
                "amount": 1
            },
            {"name": "毒刺", "station": None, "materials": [], "amount": 5}
        ]
    }
    '''

    async def _recursive(tx, item_name, depth):
        if depth >= max_depth:
            return {"name": item_name, "station": None, "materials": []}

        regex = f"^{item_name}(×.*)?"
        query = """
        MATCH (p:Item)
        WHERE p.name =~ $regex
        OPTIONAL MATCH (p)-[:CRAFTED_AT]->(s:Station)
        OPTIONAL MATCH (p)-[r:REQUIRES]->(m:Item)
        RETURN p.name AS name, s.name AS station, collect({name: m.name, amount: r.amount}) AS materials
        """
        result = await tx.run(query, regex=regex)
        record = await result.single()

        if not record:
            return {"name": item_name, "station": None, "materials": []}

        materials = []
        for m in record["materials"]:
            if m["name"] is not None:
                sub_info = await _recursive(tx, m["name"], depth + 1)
                sub_info["amount"] = m["amount"]
                materials.append(sub_info)

        return {
            "name": record["name"],
            "station": record["station"],
            "materials": materials
        }

    async with driver.session() as session:
        return await session.execute_read(_recursive, item_name, 0)

# if __name__ == "__main__":
#     async def main():
#         item_name = "瓶装水"
#         tree = await build_crafting_tree(item_name, max_depth=2)
#         info = await get_crafting_info(item_name)
#         print("Crafting Tree:", tree)
#         print("Crafting Info:", info)
#
#     asyncio.run(main())

from neo4j import GraphDatabase
from pyvis.network import Network
import pandas as pd

# Neo4j 云数据库配置 (替换为你的实际信息)
URI = "neo4j+s://7c083033.databases.neo4j.io"
USER = "neo4j"
PASSWORD = "YhqctoPsXJz6PVobPXApV-IG8_vTfWKNkt5ilqBlMKo"
# 1. 连接数据库
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def fetch_graph_data():
    """从Neo4j获取所有节点和关系"""
    query = """
    MATCH (n)-[r]->(m)
    RETURN 
        id(n) as source_id,
        labels(n)[0] as source_label,
        properties(n) as source_properties,
        id(m) as target_id,
        labels(m)[0] as target_label,
        properties(m) as target_properties,
        type(r) as rel_type,
        properties(r) as rel_properties
    """
    with driver.session() as session:
        result = session.run(query)
        return pd.DataFrame([dict(record) for record in result])

# 2. 获取数据
df = fetch_graph_data()
print(f"获取到 {len(df)} 条关系数据")

# 3. 创建网络图
net = Network(
    height="800px",
    width="100%",
    bgcolor="#222222",
    font_color="white",
    notebook=True
)

# 4. 添加节点（避免重复添加）
nodes = set()
for _, row in df.iterrows():
    if row['source_id'] not in nodes:
        net.add_node(
            row['source_id'], 
            label=row['source_properties'].get('name', row['source_label']), 
            title=str(row['source_properties']),
            color={'background': '#4488cc', 'border': '#ffffff'}  # 添加默认颜色
        )
        nodes.add(row['source_id'])
    
    if row['target_id'] not in nodes:
        net.add_node(
            row['target_id'], 
            label=row['target_properties'].get('name', row['target_label']),
            title=str(row['target_properties']),
            color={'background': '#4488cc', 'border': '#ffffff'}  # 添加默认颜色
        )
        nodes.add(row['target_id'])

# 5. 添加关系
for _, row in df.iterrows():
    net.add_edge(
        row['source_id'],
        row['target_id'],
        title=f"{row['rel_type']}: {str(row['rel_properties'])}",
        label=row['rel_type'],
        color={'color': '#ffffff'}  # 添加默认颜色
    )

# 6. 优化大型图配置，添加交互事件
net.set_options("""
{
  "physics": {
    "barnesHut": {
      "gravitationalConstant": -30000,
      "centralGravity": 0.3,
      "springLength": 200
    },
    "minVelocity": 0.75
  },
  "nodes": {
    "scaling": {
      "min": 10,
      "max": 30
    }
  },
  "interaction": {
    "hover": true
  }
}
""")

# 添加点击高亮效果的JavaScript代码
net.html += """
<script>
  let network = document.getElementsByClassName('vis-network')[0];
  let selectedNode = null;
  
  network.addEventListener('click', function(e) {
    let params = e.detail;
    if (params.nodes.length > 0) {
      let nodeId = params.nodes[0];
      
      // 重置所有节点和边的颜色
      network.body.data.nodes.update(
        network.body.data.nodes.get().map(node => ({
          id: node.id,
          color: {background: '#4488cc', border: '#ffffff'}
        }))
      );
      network.body.data.edges.update(
        network.body.data.edges.get().map(edge => ({
          id: edge.id,
          color: {color: '#ffffff'}
        }))
      );
      
      // 高亮选中的节点及其相关边和节点
      if (selectedNode !== nodeId) {
        let connectedEdges = network.body.data.edges.get().filter(edge => 
          edge.from === nodeId || edge.to === nodeId
        );
        let connectedNodes = new Set();
        
        // 高亮相关边
        network.body.data.edges.update(
          connectedEdges.map(edge => {
            connectedNodes.add(edge.from);
            connectedNodes.add(edge.to);
            return {id: edge.id, color: {color: '#ff8800'}}
          })
        );
        
        // 高亮相关节点
        network.body.data.nodes.update(
          Array.from(connectedNodes).map(id => ({
            id: id,
            color: {background: '#ff8800', border: '#ffffff'}
          }))
        );
        
        selectedNode = nodeId;
      } else {
        selectedNode = null;
      }
    }
  });
</script>
"""

# 7. 保存并展示
net.show("neo4j_graph.html", notebook=False)
driver.close()
print("可视化完成！文件已保存为 neo4j_graph.html")
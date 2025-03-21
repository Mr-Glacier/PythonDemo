# Qdrant 向量库

> Thanks for [qdrant](https://github.com/qdrant/qdrant)

### 1. 安装 Qdrant
> linux 系统 (AMD | ARM)
```shell
docker pull qdrant/qdrant:latest
docker run -p 6333:6333 -p 6334:6334 -d --name qdrant qdrant/qdrant:latest
```
> windows 系统 (AMD | ARM)  
[qdrant release download](https://github.com/qdrant/qdrant/releases)  
> 选择 windows 系统下载对应版本的 进行安装 
> 进入文件夹 `qdrant` 下执行 cmd 运行 `qdrant.exe`

### 2. 向量库使用 ( python 示例)
> 向量库链接
```python
from qdrant_client import QdrantClient
client = QdrantClient(host="localhost", port=6333)
# or
client = QdrantClient(url="http://localhost:6333")
```
> 创建集合（Collection）
```python
# 创建集合的schema
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
client = QdrantClient(host="localhost", port=6333)
# 创建集合
client.create_collection(
    collection_name='my_collection',
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    on_disk_payload=True  # 设置为 True 表示将 payload 存储在磁盘上
)
# or
client.create_collection(collection_name='my_collection',vectors_config=VectorParams(size=768, distance=Distance.COSINE),on_disk_payload=True)
```
相关参数介绍:
1. collection_name: 集合名称
2. size : 向量维度
3. distance : 向量距离度量
4. on_disk_payload : 是否将 payload 存储在磁盘上, 默认是false。如果设置为true，可以减少内存使用但可能会稍微降低查询速度。

> 向集合中添加向量
```python
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

# 初始化客户端
client = QdrantClient("localhost", port=6333)

# 准备要插入的数据点
# 注意：这里的向量长度为712，根据实际需求调整
points = [
    PointStruct(id=1, vector=[0.0] * 712, payload={"field": "value1"}), # 示例使用0填充，实际应用中应替换为具体数值
    PointStruct(id=2, vector=[0.1] * 712, payload={"field": "value2"}), # 同上
    # 添加更多点...
]

# 使用upsert方法将向量添加到集合中
client.upsert(collection_name="my_collection", points=points)

print("712维度向量添加成功")
```
ps: 添加向量时，需要确保集合已经创建，并且集合的名称与实际集合名称匹配。  
    一次添加不要过多，避免性能问题。  
    同时元数据 payload 是可选的，如果不需要元数据，可以忽略该参数。
> 索引
存在索引功能，分为两种：向量索引和元数据索引。
```python
# 向量索引
# 在集合创建时候 , Qdrant会基于你在vector_size和distance参数中的配置自动为向量数据建立索引

# 元数据索引
from qdrant_client import QdrantClient
from qdrant_client.http.models import PayloadSchemaType, WriteOrdering

client = QdrantClient("localhost", port=6333)

# 假设我们有一个名为 'my_collection' 的集合，并且我们想对 payload 中的 'category' 字段进行索引
result = client.create_payload_index(
    collection_name="my_collection",
    field_name="category",
    field_schema=PayloadSchemaType.KEYWORD,  # 或者使用 field_type 参数
    wait=True, # 是否等待操作完成
    ordering=WriteOrdering.MEDIUM  # 根据需求选择合适的写入顺序策略
)

print("Index creation result:", result)
```
> 查询向量

相似向量检索
```python
from qdrant_client import QdrantClient
from qdrant_client.http.models import SearchRequest, Filter, FieldCondition, MatchValue

# 初始化客户端
client = QdrantClient("localhost", port=6333)

# 查询向量，假设维度为712
query_vector = [0.0] * 712  # 实际应用中应替换为具体的查询向量

# 定义搜索请求
search_request = SearchRequest(
    vector=query_vector,
    limit=5,  # 返回最相似的前5个结果
    with_payload=True,  # 是否返回payload数据
    with_vector=False,  # 是否返回匹配向量，默认False
    filter=None  # 可选过滤条件，这里设为None表示不过滤
)

# 执行搜索
results = client.search(
    collection_name="my_collection",  # 目标集合名称
    search_request=search_request
)

# 处理结果
for result in results:
    print(f"Score: {result.score}, ID: {result.id}")
    if result.payload is not None:
        print(f"Payload: {result.payload}")

# 增加过滤条件 !
# 假设我们希望只返回payload中'category'字段等于'science'的结果
filter_conditions = Filter(
    must=[FieldCondition(key="category", match=MatchValue(value="science"))]
)

search_request = SearchRequest(
    vector=query_vector,
    limit=5,
    with_payload=True,
    filter=filter_conditions
)

results = client.search(collection_name="my_collection", search_request=search_request)
```

> 删除集合
```python
from qdrant_client import QdrantClient
client = QdrantClient(host="localhost", port=6333)
client.delete_collection(collection_name="my_collection")
```
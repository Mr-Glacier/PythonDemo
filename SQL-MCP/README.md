# SQL-MCP
## 项目结构
```text
my_mcp_server/
│── server.py          # 入口，Transport + Server 启动
│── handlers/          # 协议层 -> Handler 实现
│   ├── db_handler.py  # 数据库相关 Handler
│   ├── file_handler.py# 文件系统 Handler
│   └── api_handler.py # 外部 API Handler
│── services/          # Service 层，具体业务逻辑
│   ├── db_service.py
│   ├── file_service.py
│   └── api_service.py
│── config/            
│   └── settings.py    # 配置管理
│── requirements.txt
```

## 运行流程

```textmate
用户 →（对话）→ Qwen-Agent（MCP 客户端/编排）
               └── 调用 → MySQL-mcp-server（执行 SQL）
结果 ←───────────────┘
Qwen-Agent（可选把表格数据传回 LLM 生成自然语言）
→ 返回用户

```
# 项目简介

课程智能体平台面向课程教学与学习场景，提供课程问答、课本伴读、视频伴读、习题推荐、错题分析和运维统计能力。

## 技术栈

- 后端服务：FastAPI + Python 3.12+
- 前端界面：Vue 3 + Vite + Ant Design Vue
- 数据库存储：PostgreSQL + MinIO
- 知识检索：Milvus + LightRAG
- 图数据库：Neo4j
- 智能体框架：LangGraph
- 文档与 OCR：RapidOCR、PaddleOCR、MinerU、PaddleX
- 容器编排：Docker Compose

## 核心功能

- 课程智能对话：围绕课程内容进行多轮问答与知识库检索。
- 课本伴读：支持 PDF 浏览、页码跳转、选区 OCR、翻译和侧边问答。
- 视频伴读：支持按章节组织课程视频、字幕读取和分段总结。
- 习题推荐：按章节、知识点和题型生成练习，并记录答题结果。
- 运维统计：集中查看用户、对话、做题和反馈数据。

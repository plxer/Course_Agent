<div align="center">

# 天津大学 · 计算机网络课程智能体网站

面向《计算机网络》课程的智能助学站点：课本伴读、视频学习、章节习题与对话答疑等能力；对话与检索由大模型与课程知识库驱动。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

## 项目说明

本仓库由开源项目 **[Yuxi-Know（语析）](https://github.com/xerrors/Yuxi-Know)** 二次开发而来，**定位与功能已与原版通用「智能体平台」不同**：此处专注于天津大学计算机网络课程的教学场景。

**从 Yuxi-Know 沿用的部分（底座）：**

- **Docker 与编排**：`docker-compose.yml`、`docker-compose.prod.yml` 及容器化运行方式（API、前端开发服务、PostgreSQL、Neo4j、Milvus、MinIO 等）。
- **底层 Web 架构**：后端 **FastAPI**，前端 **Vue 3 + Vite + Ant Design Vue**（`server/`、`web/` 目录层次与请求路由习惯延续上游）。
- **数据与中间件栈**：关系库 **PostgreSQL**、向量检索 **Milvus**、图数据库 **Neo4j**、对象存储 **MinIO**、鉴权与会话等与上游一致的部署假设（具体以 `.env` 与 Compose 为准）。

**在本仓库中扩展或替换的部分：** 课程路由、课本/视频/习题等业务页面与接口、`knowledgebase/` 下教材与媒体资源组织方式等。若需了解通用智能体、知识库管理、图谱上传等完整能力，请参阅 **[Yuxi-Know 文档中心](https://xerrors.github.io/Yuxi-Know/)**。

## 课程功能概览

| 模块 | 说明 |
|------|------|
| 课本伴读 | 基于课程 PDF 的划选、翻译与答疑 |
| 视频学习 | 章节视频与字幕、摘要等（资源位于 `knowledgebase/videos/`） |
| 习题练习 | 按章节 / 知识点组卷与作答 |
| 智能对话 | 绑定课程知识库的问答与智能体对话 |

实际启用范围取决于是否配置课本、视频与模型 API（见环境与 `.env`）。

## 技术底座（继承自 Yuxi-Know）

| 层级 | 说明 |
|------|------|
| 后端 | Python 3.12+，`uv` 管理依赖；FastAPI + Uvicorn；LangChain / LangGraph 用于智能体编排（详见 `pyproject.toml`） |
| 前端 | Vue 3、Vite、Pinia、`web/package.json` 所列依赖 |
| 容器 | 默认开发栈：`api`（5050）、`web`（5173）、PostgreSQL、Neo4j、Milvus 及相关依赖服务；可选 profile 含文档解析 / OCR 等 |

根目录亦可使用 **VitePress** 构建文档（`npm run docs:dev`），与课程站点主体相互独立。

## 课程资源目录（简要）

- `knowledgebase/books/`：课程 PDF 课本  
- `knowledgebase/videos/`：课程视频；字幕、摘要等多为 JSON；大体积视频默认仅示例入库策略见 `.gitignore` 说明  

## 快速开始

```bash
git clone <本仓库 URL>
cd <仓库目录>

# Linux / macOS
./scripts/init.sh

# Windows PowerShell
.\scripts\init.ps1
```

复制并编辑 `.env` 后启动：

```bash
docker compose up --build
```

- 前端开发地址：**http://localhost:5173**  
- API：**http://localhost:5050**  

生产环境可参考 `docker-compose.prod.yml` 与 `docker/nginx/`。仅在本地调试前端时，进入 `web/` 执行 `pnpm install`、`pnpm run dev`，并在 `vite.config.js` 中将 `/api` 代理到后端。

## 致谢

- 底座与工程范式来自 **[Yuxi-Know](https://github.com/xerrors/Yuxi-Know)**（MIT License）。  
- 若使用上游文档、Issue 或 Release，请以其仓库为准。

## 许可证

本项目继承上游开源许可，详见仓库根目录 **[LICENSE](LICENSE)** 文件。

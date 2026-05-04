<div align="center">

# 天津大学《计算机网络》课程数智化平台

面向《计算机网络》的智能助学站点：课本伴读、视频学习、章节习题与对话答疑等；对话与检索由大模型与课程知识库驱动。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

## 项目说明

本仓库由开源项目 **[Yuxi-Know（语析）](https://github.com/xerrors/Yuxi-Know)** 二次开发而来，**定位与功能已与原版通用「智能体平台」不同**：此处实现 **天津大学《计算机网络》课程数智化平台** 的教学场景。

**从 Yuxi-Know 沿用的部分（底座）：**

- **Docker 与编排**：`docker-compose.yml`、`docker-compose.prod.yml` 及容器化运行方式（API、前端开发服务、PostgreSQL、Neo4j、Milvus、MinIO 等）。
- **底层 Web 架构**：后端 **FastAPI**，前端 **Vue 3 + Vite + Ant Design Vue**（`server/`、`web/` 目录层次与请求路由习惯延续上游）。
- **数据与中间件栈**：关系库 **PostgreSQL**、向量检索 **Milvus**、图数据库 **Neo4j**、对象存储 **MinIO**、鉴权与会话等与上游一致的部署假设（具体以 `.env` 与 Compose 为准）。

**在本仓库中扩展或替换的部分（相对原版「通用智能体平台」主页与默认动线）：**

- **入口与路由**
  - 站点根路径 `/` 重定向到 **`/course`**，登录成功后默认进入课程区（原版默认首页多为 `/` → 平台工作台）。
  - 新增一组 **课程专用路由**，对应 `web/src/views/course/`：例如 **`/course`**、**`/conversation`**（课程对话）、**`/reading`**（课本伴读）、**`/videos`**（章节视频）、**`/exercises`**（习题与弱项练习）、**`/guide`**（使用指南）、**`/ops`**（运维页，管理员）、**`/feedback-admin`**（反馈管理，管理员）等。
  - 原语析中的 **知识库 / 图谱 / 智能体管理** 等能力仍保留在 **`/platform`**、**`/database`**、**`/graph`**、**`/agent`** 等路径下，供管理员使用，但不是学生日常默认路径。

- **后端 API**
  - 新增 **`server/routers/course_router.py`**，REST 前缀 **`/api/course`**：课本列表与 PDF 访问、章节目录（用于伴读/出题）、伴读侧 OCR/翻译与 **SSE 对话流**、视频列表与字幕/摘要、**习题生成 / 提交 / 错题分析**、对话标题生成等。
  - 与课程耦合的逻辑分布在 **`src/services/`**（如教材章节 **`textbook_service`**、习题 **`exercise_service`**）及 **`src/config`** 中课程伴读相关开关（如 OCR）等。
  - 业务数据扩展使用 PostgreSQL 中的课程相关表（例如伴读进度、习题作答记录等，具体见迁移与 `models_business`）。

- **前端**
  - **`web/src/apis/courseApi.js`**：封装上述 `/api/course/*`。
  - **`web/src/components/course/`**（顶栏、页面头等）、**`web/src/stores/courseConversation.js`** 等课程专用状态。
  - **登录 / 注册页**：文案与品牌偏向本校课程平台；默认登录成功跳转 **`/course`**；左侧背景图默认 **`web/public/login-bg.jpg`**（可用后台「组织信息」中的登录背景 URL 覆盖）。

- **课程资源与目录约定**
  -  **`knowledgebase/books/`**：课程 PDF 课本；可通过环境变量 **`KNOWLEDGEBASE_DIR`** 指向其它绝对或相对路径。
  - **`knowledgebase/videos/`**：视频文件及 **`caption/`**、**`summary/`** 等字幕与摘要 JSON；体积较大的视频可在 `.gitignore` 中配置为仅提交示例文件。

以上扩展与 Yuxi-Know 自带的通用 RAG、知识库管理、Neo4j 图谱、智能体编排 **共用同一套后端进程与中间件**；课程侧主要增加了「面向教材目录与章节」的读写接口与页面，而非替换底层向量库或鉴权框架。

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

底座与工程范式来自 **[Yuxi-Know](https://github.com/xerrors/Yuxi-Know)**（MIT License）。上游仓库的 Issue / Release 适用于底座行为说明；**本仓库课程业务以本 README 与源码为准**。

## 许可证

本项目继承上游开源许可，详见仓库根目录 **[LICENSE](LICENSE)** 文件。

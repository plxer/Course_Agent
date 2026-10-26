# 快速开始指南

## 环境准备

项目通过 Docker Compose 管理，默认服务无需 GPU。GPU 仅用于可选 OCR 推理。

## 1. 配置环境变量

复制环境变量模板：

```bash
cp .env.template .env
```

编辑 `.env`，填写模型服务密钥。常用项包括：

- `SILICONFLOW_API_KEY`：模型服务密钥
- `TAVILY_API_KEY`：可选，用于网络搜索
- `DEFAULT_AGENT_ID`：课程对话默认智能体

## 2. 启动服务

```bash
docker compose up --build -d
```

启动后等待后端完成初始化，通常需要 2-3 分钟。

## 3. 访问系统

- Web 界面：`http://localhost:5173`
- API 文档：`http://localhost:5050/docs`

## 4. 准备课程资源

课本和视频不放在仓库里。默认读取仓库同级目录 `yuxi-knowledgebase`：

- 课本：`yuxi-knowledgebase/books/*.pdf`
- 视频：`yuxi-knowledgebase/videos/**`

本机若仓库在 `/home/wjk/workplace/Yuxi-Know_v0.5.0-beta`，资源目录就是 `/home/wjk/workplace/yuxi-knowledgebase`。

可通过环境变量改成其它绝对路径（Docker 会按同一路径挂进容器）：

```bash
KNOWLEDGEBASE_DIR=/path/to/yuxi-knowledgebase
```

## 5. 停止服务

```bash
docker compose down
```

## 常用排查

```bash
# 查看容器状态
docker ps

# 查看后端日志
docker logs api-dev -f

# 查看前端日志
docker logs web-dev -f
```

如果 Docker 镜像拉取失败，可使用 `docker/pull_image.sh` 或 `docker/pull_image.ps1` 手动拉取基础镜像。

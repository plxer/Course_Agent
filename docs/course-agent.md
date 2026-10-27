# 课程智能体

本功能面向课程学习场景，提供课程问答、课本伴读（含 OCR）、视频伴读、习题推荐与运维统计入口。

## 前端入口

- `/course` 或 `/conversation`：课程对话（使用默认智能体 + 知识库）
- `/reading`：课本伴读（PDF 列表、分页、选区 OCR、侧边栏对话）
- `/videos`：视频伴读（按章节展示、弹窗播放）
- `/exercises`：习题推荐
- `/ops`：运维总览（管理员）
- `/feedback-admin`：反馈管理（管理员）

## 后端 API

- `POST /api/course/chat/stream`：课程对话流（需登录，使用默认智能体）
- `GET /api/course/books`：课本列表
- `GET /api/course/books/{book_id}/pages`：课本页数
- `GET /api/course/books/{book_id}/page/{page_num}`：课本某一页图片
- `POST /api/course/books/ocr`：选区取字（先 PDF 文字层，再 RapidOCR；设置 `COURSE_READING_ENABLE_PADDLE_OCR=1` 时可启用 Paddle 回退）
- `GET /api/course/reading-position?book_id=xxx`：获取当前用户某本书的阅读页码（需登录）
- `PUT /api/course/reading-position`：保存当前用户某本书的阅读页码（需登录，body: `{ book_id, page }`）
- `GET /api/course/videos`：视频列表（按章节）
- `GET /api/course/videos/{video_id}`：视频文件流

课本与视频接口已加入公开路径，未登录也可访问。若需改为需登录，可修改 `server/utils/auth_middleware.py` 的公开路径配置。

## 课本与视频资源目录

大文件不进 git。默认路径是仓库同级目录 `yuxi-knowledgebase`。

- 课本：`yuxi-knowledgebase/books/*.pdf`
- 视频：`yuxi-knowledgebase/videos/` 下任意子目录，文件名含 `Chapter数字` 会按章节归类

可通过环境变量改成其它绝对路径：

```bash
KNOWLEDGEBASE_DIR=/path/to/yuxi-knowledgebase
```

Docker 部署时，api 服务把该目录按同一路径挂进容器。未设置环境变量时，挂载仓库同级的 `yuxi-knowledgebase` 到容器内 `/yuxi-knowledgebase`。

## 课程对话说明

- 课程对话流复用 `stream_agent_chat`，使用默认智能体与当前用户的部门配置。
- 对话需要配置默认智能体，并为该智能体配置好课程相关知识库，才会带检索。
- 用户需已登录且已绑定部门，否则会提示未绑定部门。

## OCR 依赖

- 课本伴读选区：先 PDF 文字层，再 RapidOCR。PaddleOCR 默认不参与，以减少容器内存和预热成本。
- 需要高精度回退时在运行环境设置 `COURSE_READING_ENABLE_PADDLE_OCR=1`。
- 启用 Paddle 时可选：`PADDLEOCR_USE_GPU=true` 做 GPU 推理。
- 若需使用 Paddle 系文档解析（表格/版面），请启动 PaddleX 服务并在上传知识库时选择 PP-StructureV3。

## Docker 集成 PaddleOCR

```bash
docker compose build api
docker compose up -d api
```

首次运行课本伴读选区 OCR 时，PaddleOCR 会在容器内自动下载模型。可通过挂载卷缓存：

```yaml
volumes:
  - paddleocr-cache:/root/.paddleocr
```

在容器内查看 PaddleOCR 版本：

```bash
docker compose exec api python /app/scripts/check_paddleocr.py
```

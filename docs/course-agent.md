# 课程智能体（移植说明）

本功能从老版 Yuxi 课程智能体移植到 v0.5，提供《计算机网络》等课程的：**问答**、**课本伴读（含 OCR）**、**视频伴读**、**习题推荐** 入口。

## 前端入口

- `/course` 或 `/conversation`：课程对话（使用默认智能体 + 知识库）
- `/reading`：课本伴读（PDF 列表、分页、选区 OCR、侧边栏对话）
- `/videos`：视频伴读（按章节展示、弹窗播放）
- `/exercises`：习题推荐（当前为静态示例，可按需对接题目生成接口）

## 后端 API

- `POST /api/course/chat/stream`：课程对话流（需登录，使用默认智能体）
- `GET /api/course/books`：课本列表
- `GET /api/course/books/{book_id}/pages`：课本页数
- `GET /api/course/books/{book_id}/page/{page_num}`：课本某一页图片
- `POST /api/course/books/ocr`：选区 OCR（PaddleOCR + PDF 文本兜底）
- `GET /api/course/videos`：视频列表（按章节）
- `GET /api/course/videos/{video_id}`：视频文件流

课本与视频接口已加入公开路径，未登录也可访问（若需改为需登录，可修改 `server/utils/auth_middleware.py` 的 `PUBLIC_PATHS`）。

## 课本与视频资源目录

默认路径：项目根目录下的 `knowledgebase` 目录。

- **课本**：`knowledgebase/books/*.pdf`
- **视频**：`knowledgebase/videos/` 下任意子目录，文件名含 `Chapter数字` 会按章节归类

可通过环境变量覆盖：

```bash
# 自定义课本/视频根目录（可选）
export KNOWLEDGEBASE_DIR=/path/to/your/knowledgebase
```

Docker 部署时，可在 `docker-compose.yml` 的 api 服务中增加挂载：

```yaml
volumes:
  - ./knowledgebase:/app/knowledgebase
```

## 课程对话说明

- 课程对话流复用 v0.5 的 `stream_agent_chat`，使用 **默认智能体** 与当前用户的部门配置（含知识库权限）。
- 需在「系统设置」中配置**默认智能体**，并为该智能体配置好课程相关**知识库**，对话时才会带检索。
- 用户需**已登录且已绑定部门**，否则会提示「当前用户未绑定部门」。

## OCR 依赖

- 优先使用 **PaddleOCR**（需安装 `paddleocr`）；若不可用则使用 PDF 文本块提取。
- 可选环境变量：`PADDLEOCR_USE_GPU=true` 启用 GPU。

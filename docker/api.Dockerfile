# 使用轻量级Python基础镜像
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.7.2 /uv /uvx /bin/
COPY --from=node:20-slim /usr/local/bin /usr/local/bin
COPY --from=node:20-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node:20-slim /usr/local/include /usr/local/include
COPY --from=node:20-slim /usr/local/share /usr/local/share

# 设置工作目录
WORKDIR /app

# 环境变量设置
ENV TZ=Asia/Shanghai \
    UV_PROJECT_ENVIRONMENT="/usr/local" \
    UV_COMPILE_BYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    FLAGS_use_mkldnn=0 \
    FLAGS_use_onednn=0 \
    PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=0

# 跳过全局升级 npm：少数 Docker/内核环境下会触发 Node 线程创建断言失败；node:20-slim 自带 npm 已够用。

# 时区（不跑 apt：低配构建易 lzma OOM；OpenCV 见 pyproject 里 opencv-python 覆盖为 headless）
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 复制项目配置文件
COPY ../pyproject.toml /app/pyproject.toml
COPY ../.python-version /app/.python-version
COPY ../uv.lock /app/uv.lock

# 如果网络还是不好，可以在后面添加 --index-url https://pypi.tuna.tsinghua.edu.cn/simple
# 课本伴读 PaddleOCR：在下一行追加 `&& uv sync --no-dev --group paddle`（旧版 Docker 勿用 RUN --mount，需先 DOCKER_BUILDKIT=1）
RUN uv sync --no-dev --frozen

# 激活虚拟环境并添加到PATH
ENV PATH="/app/.venv/bin:$PATH"

# 复制代码到容器中
COPY ../src /app/src
COPY ../server /app/server
COPY ../scripts /app/scripts

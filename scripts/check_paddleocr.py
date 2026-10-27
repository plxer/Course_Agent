#!/usr/bin/env python3
"""在容器内验证 PaddleOCR 3.x 是否可用（会先注入 langchain 兼容层）。"""

import os
import sys
from pathlib import Path

# 保证能 import src（容器内 /app，本地为项目根）
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from src.plugins.paddle_ocr_processor import (  # noqa: E402
    _ensure_langchain_docstore_compat,
    _ensure_langchain_text_splitter_compat,
)

_ensure_langchain_docstore_compat()
_ensure_langchain_text_splitter_compat()

import paddleocr  # noqa: E402

if __name__ == "__main__":
    print(paddleocr.__version__)

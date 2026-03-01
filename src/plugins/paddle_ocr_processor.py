"""
PaddleOCR 处理器 - 课本伴读选区 OCR（高精度）

用于课本伴读选区文字识别，需安装依赖组：uv sync --group paddle
PaddleOCR 3.x 依赖的 paddlex 会 from langchain.docstore.document import Document，
当前 LangChain 已移除该路径，此处在导入 paddleocr 前注入兼容层。
"""

import os
import sys
import types


def _ensure_langchain_docstore_compat():
    """为 PaddleOCR 3.x / paddlex 提供 langchain.docstore.document，避免 ModuleNotFoundError。"""
    if "langchain.docstore.document" in sys.modules:
        return
    try:
        from langchain_core.documents import Document
    except ImportError:
        return
    docstore = types.ModuleType("langchain.docstore")
    docstore.document = types.ModuleType("langchain.docstore.document")
    docstore.document.Document = Document
    sys.modules["langchain.docstore"] = docstore
    sys.modules["langchain.docstore.document"] = docstore.document


def _ensure_langchain_text_splitter_compat():
    """为 paddlex 提供 langchain.text_splitter（RecursiveCharacterTextSplitter 等）。"""
    if "langchain.text_splitter" in sys.modules:
        return
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        return
    text_splitter_mod = types.ModuleType("langchain.text_splitter")
    text_splitter_mod.RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter
    sys.modules["langchain.text_splitter"] = text_splitter_mod


from src.plugins.document_processor_base import BaseDocumentProcessor, OCRException
from src.utils import logger


class PaddleOcrProcessor(BaseDocumentProcessor):
    """PaddleOCR 处理器 - 用于课本伴读选区等高精度 OCR"""

    def __init__(self, use_angle_cls: bool = True, lang: str = "ch", use_gpu: bool | None = None):
        self.use_angle_cls = use_angle_cls
        self.lang = lang
        self.use_gpu = use_gpu if use_gpu is not None else _parse_use_gpu_env()
        self._ocr = None

    def get_service_name(self) -> str:
        return "paddle_ocr"

    def get_supported_extensions(self) -> list[str]:
        return [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]

    def check_health(self) -> dict:
        """检查 PaddleOCR 是否可用（可 import 且能初始化）"""
        _ensure_langchain_docstore_compat()
        _ensure_langchain_text_splitter_compat()
        # 3.x 会检查模型源连通性，容器内可禁用以免卡住
        if os.environ.get("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK") is None:
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
        try:
            from paddleocr import PaddleOCR
        except ImportError as e:
            return {
                "status": "unavailable",
                "message": "未安装 PaddleOCR，请执行: uv sync --group paddle",
                "details": {"error": str(e)},
            }
        try:
            if self._ocr is None:
                self._ocr = PaddleOCR(
                    use_angle_cls=self.use_angle_cls,
                    lang=self.lang,
                    use_gpu=self.use_gpu,
                    show_log=False,
                )
            return {"status": "healthy", "message": "PaddleOCR 可用", "details": {}}
        except Exception as e:
            return {"status": "error", "message": f"PaddleOCR 初始化失败: {e}", "details": {"error": str(e)}}

    def _load_ocr(self):
        if self._ocr is not None:
            return
        health = self.check_health()
        if health["status"] != "healthy":
            raise OCRException(health["message"], self.get_service_name(), health["status"])
        # check_health 已初始化 self._ocr
        logger.info("PaddleOCR 模型加载成功")

    def process_file(self, file_path: str, params: dict | None = None) -> str:
        """对图片文件做 OCR，返回识别文本。"""
        self._load_ocr()
        if not os.path.isfile(file_path):
            raise OCRException(f"文件不存在: {file_path}", self.get_service_name(), "file_not_found")
        try:
            result = self._ocr.ocr(file_path, cls=self.use_angle_cls)
        except Exception as e:
            raise OCRException(f"OCR 执行失败: {e}", self.get_service_name(), "processing_failed") from e
        if not result or not result[0]:
            return ""
        # result[0] 为 [[box, (text, conf)], ...]，按行分组、同行按 x 排序后合并，改善空格与版式
        return _format_ocr_result(result[0]).strip()


def _format_ocr_result(lines: list) -> str:
    """将 PaddleOCR 的 box 结果按行分组，同行用空格连接，保留版式与空格。"""
    if not lines:
        return ""
    # 每个 item: [box, (text, conf)]，box 为 4 点 [[x1,y1],...]
    LINE_THRESHOLD = 20  # 同一行 y 中心差在此内视为同一行

    def box_center(box):
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        return (sum(xs) / 4, sum(ys) / 4)

    items = []
    for line in lines:
        box = line[0]
        text = line[1][0] if line[1] else ""
        if not text:
            continue
        cx, cy = box_center(box)
        items.append((cy, cx, text))

    if not items:
        return ""

    items.sort(key=lambda t: (t[0], t[1]))  # 先按 y 再按 x
    lines_out = []
    current_line = [items[0]]
    current_y = items[0][0]

    for i in range(1, len(items)):
        cy, cx, text = items[i]
        if abs(cy - current_y) <= LINE_THRESHOLD:
            current_line.append((cy, cx, text))
        else:
            # 当前行按 x 排序后合并
            current_line.sort(key=lambda t: t[1])
            lines_out.append(" ".join(t[2] for t in current_line))
            current_line = [(cy, cx, text)]
            current_y = cy

    current_line.sort(key=lambda t: t[1])
    lines_out.append(" ".join(t[2] for t in current_line))
    return "\n".join(lines_out)


def _parse_use_gpu_env() -> bool:
    val = os.getenv("PADDLEOCR_USE_GPU", "").strip().lower()
    return val in ("1", "true", "yes")

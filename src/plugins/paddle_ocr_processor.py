"""
PaddleOCR 处理器 - 课本伴读选区 OCR（高精度）

用于课本伴读选区文字识别，需安装依赖组：uv sync --group paddle
PaddleOCR 3.x 依赖的 paddlex 会 from langchain.docstore.document import Document，
当前 LangChain 已移除该路径，此处在导入 paddleocr 前注入兼容层。
"""

import os
import sys
import threading
import types


def _disable_paddle_onednn_unless_opt_in() -> None:
    """关闭 Paddle Inference 的 MKLDNN/oneDNN 默认路径（与 paddle.set_flags 无关）。

    PaddleX 在 CPU 上默认 PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=True，会走 mkldnn 推理并
    config.enable_mkldnn()，从而在 C++ PaddleInferPredictor 里触发 onednn_instruction.cc
    的 ConvertPirAttribute2RuntimeAttribute 未实现异常。须在首次 import paddlex 之前设 0。

    需要 Intel MKLDNN 加速时设 PADDLE_ENABLE_ONEDNN=1（并自行承担兼容性风险）。
    """
    if os.environ.get("PADDLE_ENABLE_ONEDNN", "").strip().lower() in ("1", "true", "yes"):
        return
    os.environ["FLAGS_use_mkldnn"] = "0"
    os.environ["FLAGS_use_onednn"] = "0"
    os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"


def _paddle_runtime_disable_onednn() -> None:
    """import paddle 后关闭 oneDNN，并关闭 PIR 新执行器（仅 set_flags 生效，环境变量无法关掉后者）。

    仅关 mkldnn/onednn 时 FLAGS_enable_pir_in_executor 仍为 True，仍会进入
    new_executor/instruction/onednn/onednn_instruction.cc 并触发
    ConvertPirAttribute2RuntimeAttribute 未实现异常。
    """
    if os.environ.get("PADDLE_ENABLE_ONEDNN", "").strip().lower() in ("1", "true", "yes"):
        return
    try:
        import paddle

        paddle.set_flags(
            {
                "FLAGS_use_mkldnn": False,
                "FLAGS_use_onednn": False,
                "FLAGS_enable_pir_in_executor": False,
                # 否则仍可能走 PIR + oneDNN 指令，触发 onednn_instruction.cc 未实现
                "FLAGS_enable_pir_api": False,
            }
        )
    except Exception as e:
        logger.warning("paddle.set_flags 关闭 oneDNN/PIR 执行器失败: {}", e)


_disable_paddle_onednn_unless_opt_in()


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


from src.plugins.document_processor_base import BaseDocumentProcessor, OCRException  # noqa: E402
from src.utils import logger  # noqa: E402

_SUPPORTED_OCR_VERSIONS = frozenset({"PP-OCRv3", "PP-OCRv4", "PP-OCRv5"})


def _paddle_ocr_version() -> str:
    """课本伴读默认 PP-OCRv4 mobile，模型更小、首启更快；高精度可设环境变量 PADDLEOCR_OCR_VERSION=PP-OCRv5。"""
    v = (os.getenv("PADDLEOCR_OCR_VERSION") or "PP-OCRv4").strip()
    return v if v in _SUPPORTED_OCR_VERSIONS else "PP-OCRv4"


def _use_textline_orientation_env() -> bool:
    """伴读选区默认关闭行方向分类（少加载一个子模型）；需要时设 PADDLEOCR_TEXTLINE_ORIENTATION=1。"""
    return os.getenv("PADDLEOCR_TEXTLINE_ORIENTATION", "").strip().lower() in ("1", "true", "yes")


def _ocr_result_get(item, key: str, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    try:
        return item[key]
    except (KeyError, TypeError, IndexError):
        return getattr(item, key, default)


def _poly_to_box_points(poly) -> list | None:
    """将检测框转为 [[x,y], ...] 四点列表；无法解析则返回 None。"""
    if poly is None:
        return None
    if hasattr(poly, "tolist") and callable(getattr(poly, "tolist", None)):
        try:
            poly = poly.tolist()
        except Exception:
            return None
    if not poly:
        return None
    out: list[list[float]] = []
    try:
        for p in poly:
            out.append([float(p[0]), float(p[1])])
    except (TypeError, ValueError, IndexError):
        return None
    if len(out) < 3:
        return None
    return out


def _paddlex_result_to_lines(item) -> list:
    """将 PaddleOCR 3.x predict 的单条结果转为 _format_ocr_result 所需的 [[box, (text, conf)], ...]。"""
    if item is None:
        return []
    texts = _ocr_result_get(item, "rec_texts")
    polys = _ocr_result_get(item, "rec_polys")
    if texts is not None and polys is not None:
        lines = []
        for poly, txt in zip(polys, texts, strict=False):
            if isinstance(txt, tuple):
                txt = txt[0]
            txt = (str(txt) if txt is not None else "").strip()
            if not txt:
                continue
            box = _poly_to_box_points(poly)
            if not box:
                continue
            lines.append([box, (txt, 1.0)])
        return lines
    # PaddleOCR 2.x：单页为 [[box, (text, conf)], ...]
    if isinstance(item, list):
        return item
    return []


def _rec_texts_fallback_plain(item) -> str:
    """仅有识别文本、无可用框时，直接拼接（避免 numpy 框解析失败导致整页丢字）。"""
    texts = _ocr_result_get(item, "rec_texts")
    if not texts:
        return ""
    parts: list[str] = []
    for t in texts:
        if isinstance(t, tuple):
            t = t[0]
        s = (str(t) if t is not None else "").strip()
        if s:
            parts.append(s)
    return "\n".join(parts)


def _apply_paddle_device(use_gpu: bool) -> None:
    """PaddleOCR 3.x 不再接受 use_gpu 参数，通过 Paddle 全局设备选择 CPU/GPU。"""
    try:
        import paddle

        if use_gpu:
            try:
                paddle.set_device("gpu")
            except Exception as e:
                logger.warning("Paddle 无法使用 GPU，已回退 CPU: %s", e)
                paddle.set_device("cpu")
        else:
            paddle.set_device("cpu")
    except Exception as e:
        logger.debug("paddle.set_device 跳过: %s", e)


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
        _disable_paddle_onednn_unless_opt_in()
        _ensure_langchain_docstore_compat()
        _ensure_langchain_text_splitter_compat()
        # 3.x 会检查模型源连通性，容器内可禁用以免卡住
        if os.environ.get("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK") is None:
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
        try:
            import paddle  # noqa: F401
        except ImportError as e:
            return {
                "status": "unavailable",
                "message": "未安装 PaddlePaddle，请执行: uv sync --group paddle",
                "details": {"error": str(e)},
            }
        _paddle_runtime_disable_onednn()
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
                _apply_paddle_device(self.use_gpu)
                # 3.x：伴读选区为小图块，关闭整页文档方向/矫正，避免拉取 UVDoc、doc_ori 等大模型；ocr_version 默认 v4 mobile
                self._ocr = PaddleOCR(
                    lang=self.lang,
                    ocr_version=_paddle_ocr_version(),
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=self.use_angle_cls,
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
            result = self._ocr.predict(
                file_path,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=self.use_angle_cls,
            )
        except Exception as e:
            raise OCRException(f"OCR 执行失败: {e}", self.get_service_name(), "processing_failed") from e
        if not result:
            return ""
        first = result[0]
        if isinstance(first, dict) and first.get("error"):
            raise OCRException(
                str(first.get("error")),
                self.get_service_name(),
                "invalid_settings",
            )
        lines = _paddlex_result_to_lines(first)
        if not lines:
            plain = _rec_texts_fallback_plain(first)
            if plain:
                return plain
            return ""
        try:
            return _format_ocr_result(lines).strip()
        except Exception as e:
            logger.exception("PaddleOCR 结果排版失败，改用纯文本拼接: %s", e)
            plain = _rec_texts_fallback_plain(first)
            if plain:
                return plain
            raise OCRException(
                f"OCR 结果解析失败: {e}",
                self.get_service_name(),
                "parse_failed",
            ) from e


def _format_ocr_result(lines: list) -> str:
    """将 PaddleOCR 的 box 结果按行分组，同行用空格连接，保留版式与空格。"""
    if not lines:
        return ""
    # 每个 item: [box, (text, conf)]，box 为 4 点 [[x1,y1],...]
    LINE_THRESHOLD = 20  # 同一行 y 中心差在此内视为同一行

    def box_center(box):
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        n = len(box)
        if not n:
            return (0.0, 0.0)
        return (sum(xs) / n, sum(ys) / n)

    items = []
    for line in lines:
        box = line[0]
        pair = line[1] if len(line) > 1 else None
        if isinstance(pair, tuple) and pair:
            text = str(pair[0] or "")
        else:
            text = str(pair or "")
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


# 课本伴读每次请求若 new PaddleOcrProcessor() 会重复初始化整套 PaddleX 管线（极慢、易超时），进程内复用单例。
_course_reading_ocr_lock = threading.Lock()
_course_reading_ocr_processor: PaddleOcrProcessor | None = None


def get_course_reading_ocr_processor() -> PaddleOcrProcessor:
    global _course_reading_ocr_processor
    if _course_reading_ocr_processor is not None:
        return _course_reading_ocr_processor
    with _course_reading_ocr_lock:
        if _course_reading_ocr_processor is None:
            _course_reading_ocr_processor = PaddleOcrProcessor(
                use_angle_cls=_use_textline_orientation_env(),
            )
        return _course_reading_ocr_processor

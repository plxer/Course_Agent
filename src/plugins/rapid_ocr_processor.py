"""
RapidOCR 处理器 - 纯OCR文字识别

使用 RapidOCR (PP-OCRv4) 进行文字识别
"""

import os
import tempfile
import threading
import time
from pathlib import Path

import fitz
import numpy as np
from PIL import Image
import rapidocr_onnxruntime as _rapidocr_pkg
from rapidocr_onnxruntime import RapidOCR

from src.plugins.document_processor_base import BaseDocumentProcessor, OCRException
from src.utils import logger


def _rapid_box_center_xy(box) -> tuple[float, float]:
    """检测框四角 [[x,y],...] → 中心点。"""
    if box is None:
        return (0.0, 0.0)
    pts = np.asarray(box, dtype=np.float64).reshape(-1, 2)
    return float(pts[:, 0].mean()), float(pts[:, 1].mean())


def _format_rapid_ocr_result(result: list, *, line_y_threshold: float = 20.0) -> str:
    """RapidOCR 每个框默认单独一行输出；按框中心 y 分组合并，同行按 x 用空格拼接。"""
    items: list[tuple[float, float, str]] = []
    for line in result:
        if not line or len(line) < 2:
            continue
        box, text = line[0], line[1]
        text = (text or "").strip() if isinstance(text, str) else str(text).strip()
        if not text:
            continue
        cx, cy = _rapid_box_center_xy(box)
        items.append((cy, cx, text))
    if not items:
        return ""

    items.sort(key=lambda t: (t[0], t[1]))
    lines_out: list[str] = []
    current_line = [items[0]]
    current_y = items[0][0]

    for cy, cx, text in items[1:]:
        if abs(cy - current_y) <= line_y_threshold:
            current_line.append((cy, cx, text))
        else:
            current_line.sort(key=lambda t: t[1])
            lines_out.append(" ".join(t[2] for t in current_line))
            current_line = [(cy, cx, text)]
            current_y = cy

    current_line.sort(key=lambda t: t[1])
    lines_out.append(" ".join(t[2] for t in current_line))
    return "\n".join(lines_out)


class RapidOCRProcessor(BaseDocumentProcessor):
    """RapidOCR 处理器 - 使用 ONNX 模型进行文字识别"""

    def __init__(self, det_box_thresh: float = 0.3):
        self.ocr = None
        self.det_box_thresh = det_box_thresh
        self.model_dir_root = (
            os.getenv("MODEL_DIR") if not os.getenv("RUNNING_IN_DOCKER") else os.getenv("MODEL_DIR_IN_DOCKER")
        )

    def get_service_name(self) -> str:
        return "rapid_ocr"

    def get_supported_extensions(self) -> list[str]:
        return [".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]

    def _bundled_model_paths(self) -> tuple[str, str]:
        """rapidocr_onnxruntime 自带的 PP-OCRv4 ONNX（未挂载 MODEL_DIR 时可用）。"""
        base = os.path.join(os.path.dirname(_rapidocr_pkg.__file__), "models")
        return (
            os.path.join(base, "ch_PP-OCRv4_det_infer.onnx"),
            os.path.join(base, "ch_PP-OCRv4_rec_infer.onnx"),
        )

    def _get_model_paths(self) -> tuple[str, str]:
        """优先 MODEL_DIR/SWHL/RapidOCR 布局；不存在则用 pip 包内置模型。"""
        root = (self.model_dir_root or "").strip()
        if root:
            model_dir = os.path.join(root, "SWHL", "RapidOCR")
            det_model_path = os.path.join(model_dir, "PP-OCRv4", "ch_PP-OCRv4_det_infer.onnx")
            rec_model_path = os.path.join(model_dir, "PP-OCRv4", "ch_PP-OCRv4_rec_infer.onnx")
            if os.path.isfile(det_model_path) and os.path.isfile(rec_model_path):
                return det_model_path, rec_model_path
        return self._bundled_model_paths()

    def check_health(self) -> dict:
        """检查 RapidOCR 模型是否可用"""
        try:
            det_model_path, rec_model_path = self._get_model_paths()

            if not os.path.isfile(det_model_path) or not os.path.isfile(rec_model_path):
                return {
                    "status": "unavailable",
                    "message": "模型文件缺失（请检查 MODEL_DIR 下 SWHL/RapidOCR，或重装 rapidocr-onnxruntime）",
                    "details": {"det_model": det_model_path, "rec_model": rec_model_path},
                }

            # 尝试加载模型
            try:
                test_ocr = RapidOCR(
                    det_box_thresh=self.det_box_thresh, det_model_path=det_model_path, rec_model_path=rec_model_path
                )
                del test_ocr  # 释放资源
                bundled = self._bundled_model_paths()
                using_bundled = det_model_path == bundled[0] and rec_model_path == bundled[1]
                return {
                    "status": "healthy",
                    "message": "RapidOCR模型可用",
                    "details": {
                        "det_model": det_model_path,
                        "rec_model": rec_model_path,
                        "source": "bundled" if using_bundled else "MODEL_DIR",
                    },
                }
            except Exception as e:
                return {"status": "error", "message": f"模型加载失败: {str(e)}", "details": {"error": str(e)}}

        except Exception as e:
            return {"status": "error", "message": f"健康检查失败: {str(e)}", "details": {"error": str(e)}}

    def _load_model(self):
        """延迟加载 OCR 模型"""
        if self.ocr is not None:
            return

        logger.info("加载 RapidOCR 模型...")

        # 先检查健康状态
        health = self.check_health()
        if health["status"] != "healthy":
            raise OCRException(health["message"], self.get_service_name(), health["status"])

        try:
            det_model_path, rec_model_path = self._get_model_paths()
            self.ocr = RapidOCR(
                det_box_thresh=self.det_box_thresh, det_model_path=det_model_path, rec_model_path=rec_model_path
            )
            bdet, brec = self._bundled_model_paths()
            src = "内置" if det_model_path == bdet else "MODEL_DIR"
            logger.info("RapidOCR 模型加载成功 (det_box_thresh={}, 来源={})", self.det_box_thresh, src)
        except Exception as e:
            raise OCRException(f"RapidOCR模型加载失败: {str(e)}", self.get_service_name(), "load_failed")

    def process_image(self, image, params: dict | None = None) -> str:
        """
        处理单张图像并提取文本

        Args:
            image: 图像数据,支持:
                  - str: 图像文件路径
                  - PIL.Image: PIL图像对象
                  - numpy.ndarray: numpy图像数组
            params: 处理参数 (当前未使用)

        Returns:
            str: 提取的文本内容
        """
        self._load_model()

        try:
            # 处理不同类型的输入
            if isinstance(image, str):
                image_path = image
                cleanup_needed = False
            else:
                # 创建临时文件
                image_path = self._create_temp_image_file(image)
                cleanup_needed = True

            try:
                # 执行 OCR
                start_time = time.time()
                result, _ = self.ocr(image_path)
                processing_time = time.time() - start_time

                # 提取文本（按 y 合并同行，避免检测框过细导致一词一换行）
                if result:
                    text = _format_rapid_ocr_result(result)
                    logger.info(
                        f"RapidOCR 成功: {os.path.basename(image_path) if isinstance(image, str) else 'temp_image'}"
                        f" ({processing_time:.2f}s)"
                    )
                    return text
                else:
                    logger.warning(f"RapidOCR 未识别到文本: {image_path}")
                    return ""

            finally:
                # 清理临时文件
                if cleanup_needed and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        logger.warning(f"临时文件清理失败: {image_path} - {e}")

        except Exception as e:
            error_msg = f"图像OCR处理失败: {str(e)}"
            logger.error(error_msg)
            raise OCRException(error_msg, self.get_service_name(), "processing_failed")

    def _create_temp_image_file(self, image) -> str:
        """将图像数据保存为临时文件"""
        try:
            # 使用系统临时目录
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".png", delete=False) as tmp_file:
                temp_path = tmp_file.name

                if isinstance(image, Image.Image):
                    image.save(temp_path)
                elif isinstance(image, np.ndarray):
                    Image.fromarray(image).save(temp_path)
                else:
                    raise ValueError("不支持的图像类型,必须是 PIL.Image 或 numpy.ndarray")

                return temp_path

        except Exception as e:
            raise OCRException(f"临时图像文件创建失败: {str(e)}", self.get_service_name(), "temp_file_error")

    def process_pdf(self, pdf_path: str, params: dict | None = None) -> str:
        """
        处理 PDF 文件并提取文本 (流式处理,避免内存占用)

        Args:
            pdf_path: PDF 文件路径
            params: 处理参数
                - zoom_x: 横向缩放 (默认 2)
                - zoom_y: 纵向缩放 (默认 2)

        Returns:
            str: 提取的文本
        """
        if not os.path.exists(pdf_path):
            raise OCRException(f"PDF 文件不存在: {pdf_path}", self.get_service_name(), "file_not_found")

        params = params or {}
        zoom_x = params.get("zoom_x", 2)
        zoom_y = params.get("zoom_y", 2)

        try:
            all_text = []
            pdf_doc = fitz.open(pdf_path)
            total_pages = pdf_doc.page_count

            logger.info(f"开始处理 PDF: {os.path.basename(pdf_path)} ({total_pages} 页)")

            # 流式处理每一页,避免一次性加载所有图片到内存
            for page_num in range(total_pages):
                page = pdf_doc[page_num]

                # 转换为图像
                mat = fitz.Matrix(zoom_x, zoom_y)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # 立即处理,不保存到列表
                text = self.process_image(img_pil)
                all_text.append(text)

                if (page_num + 1) % 10 == 0:
                    logger.info(f"已处理 {page_num + 1}/{total_pages} 页")

            pdf_doc.close()

            result_text = "\n\n".join(all_text)
            logger.info(f"PDF OCR 完成: {os.path.basename(pdf_path)} - {len(result_text)} 字符")
            return result_text

        except OCRException:
            raise
        except Exception as e:
            error_msg = f"PDF OCR 处理失败: {str(e)}"
            logger.error(error_msg)
            raise OCRException(error_msg, self.get_service_name(), "pdf_processing_failed")

    def process_file(self, file_path: str, params: dict | None = None) -> str:
        """
        处理文件 (PDF 或图像)

        Args:
            file_path: 文件路径
            params: 处理参数

        Returns:
            str: 提取的文本
        """
        file_ext = Path(file_path).suffix.lower()

        if not self.supports_file_type(file_ext):
            raise OCRException(f"不支持的文件类型: {file_ext}", self.get_service_name(), "unsupported_file_type")

        if file_ext == ".pdf":
            return self.process_pdf(file_path, params)
        else:
            return self.process_image(file_path, params)


# 课本伴读选区 OCR：进程内复用单例，避免每次请求重复加载 ONNX。
_course_reading_rapid_lock = threading.Lock()
_course_reading_rapid_processor: RapidOCRProcessor | None = None


def get_course_reading_rapid_ocr_processor() -> RapidOCRProcessor:
    global _course_reading_rapid_processor
    if _course_reading_rapid_processor is not None:
        return _course_reading_rapid_processor
    with _course_reading_rapid_lock:
        if _course_reading_rapid_processor is None:
            _course_reading_rapid_processor = RapidOCRProcessor()
        return _course_reading_rapid_processor

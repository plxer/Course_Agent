import re
import traceback

from fastapi import APIRouter, HTTPException, Depends, File, Form, Body, UploadFile
from src.storage.postgres.models_business import User
from server.utils.auth_middleware import get_admin_user
from src.utils import logger

# 创建路由器
evaluation = APIRouter(prefix="/evaluation", tags=["evaluation"])

_EVAL_TASK_ID_RE = re.compile(r"^eval_[a-f0-9]{8}$")


# 主路径使用 databases/{db_id}/...；文末另有兼容前端的旧路径
# ============================================================================
# 评估基准
# ============================================================================


@evaluation.get("/databases/{db_id}/benchmarks/{benchmark_id}")
async def get_evaluation_benchmark_by_db(
    db_id: str, benchmark_id: str, page: int = 1, page_size: int = 10, current_user: User = Depends(get_admin_user)
):
    """根据 db_id 获取评估基准详情（支持分页）"""
    from src.services.evaluation_service import EvaluationService

    try:
        # 验证分页参数
        if page < 1:
            raise HTTPException(status_code=400, detail="页码必须大于0")
        if page_size < 1 or page_size > 100:
            raise HTTPException(status_code=400, detail="每页大小必须在1-100之间")

        service = EvaluationService()
        benchmark = await service.get_benchmark_detail_by_db(db_id, benchmark_id, page, page_size)
        return {"message": "success", "data": benchmark}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取评估基准详情失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取评估基准详情失败: {str(e)}")


@evaluation.delete("/benchmarks/{benchmark_id}")
async def delete_evaluation_benchmark(benchmark_id: str, current_user: User = Depends(get_admin_user)):
    """删除评估基准"""
    from src.services.evaluation_service import EvaluationService

    try:
        service = EvaluationService()
        await service.delete_benchmark(benchmark_id)
        return {"message": "success", "data": None}
    except Exception as e:
        logger.error(f"删除评估基准失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"删除评估基准失败: {str(e)}")


@evaluation.get("/databases/{db_id}/results/{task_id}")
async def get_evaluation_results_by_db(
    db_id: str,
    task_id: str,
    page: int = 1,
    page_size: int = 20,
    error_only: bool = False,
    current_user: User = Depends(get_admin_user),
):
    """获取评估结果（带 db_id，支持分页）"""
    from src.services.evaluation_service import EvaluationService

    try:
        # 验证分页参数
        if page < 1:
            raise HTTPException(status_code=400, detail="页码必须大于0")
        if page_size < 1 or page_size > 100:
            raise HTTPException(status_code=400, detail="每页大小必须在1-100之间")

        service = EvaluationService()
        results = await service.get_evaluation_results_by_db(
            db_id, task_id, page=page, page_size=page_size, error_only=error_only
        )
        return {"message": "success", "data": results}
    except Exception as e:
        logger.error(f"获取评估结果失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取评估结果失败: {str(e)}")


@evaluation.delete("/databases/{db_id}/results/{task_id}")
async def delete_evaluation_result_by_db(db_id: str, task_id: str, current_user: User = Depends(get_admin_user)):
    """删除评估结果（带 db_id）"""
    from src.services.evaluation_service import EvaluationService

    try:
        service = EvaluationService()
        await service.delete_evaluation_result_by_db(db_id, task_id)
        return {"message": "success", "data": None}
    except Exception as e:
        logger.error(f"删除评估结果失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"删除评估结果失败: {str(e)}")


# ============================================================================
# RAG评估
# ============================================================================


@evaluation.post("/databases/{db_id}/benchmarks/upload")
async def upload_evaluation_benchmark(
    db_id: str,
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    current_user: User = Depends(get_admin_user),
):
    """上传评估基准文件"""
    from src.services.evaluation_service import EvaluationService

    try:
        # 验证文件格式
        if not file.filename.endswith(".jsonl"):
            raise HTTPException(status_code=400, detail="仅支持JSONL格式文件")

        # 读取文件内容
        content = await file.read()

        # 调用评估服务处理上传
        service = EvaluationService()
        result = await service.upload_benchmark(
            db_id=db_id,
            file_content=content,
            filename=file.filename,
            name=name,
            description=description,
            created_by=current_user.user_id,
        )

        return {"message": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传评估基准失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"上传评估基准失败: {str(e)}")


@evaluation.get("/databases/{db_id}/benchmarks")
async def get_evaluation_benchmarks(db_id: str, current_user: User = Depends(get_admin_user)):
    """获取知识库的评估基准列表"""
    from src.services.evaluation_service import EvaluationService

    try:
        service = EvaluationService()
        benchmarks = await service.get_benchmarks(db_id)
        return {"message": "success", "data": benchmarks}
    except Exception as e:
        logger.error(f"获取评估基准列表失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取评估基准列表失败: {str(e)}")


@evaluation.post("/databases/{db_id}/benchmarks/generate")
async def generate_evaluation_benchmark(
    db_id: str, params: dict = Body(...), current_user: User = Depends(get_admin_user)
):
    """自动生成评估基准"""
    from src.services.evaluation_service import EvaluationService

    try:
        service = EvaluationService()
        result = await service.generate_benchmark(db_id=db_id, params=params, created_by=current_user.user_id)
        return {"message": "success", "data": result}
    except Exception as e:
        logger.error(f"生成评估基准失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"生成评估基准失败: {str(e)}")


@evaluation.post("/databases/{db_id}/run")
async def run_evaluation(db_id: str, params: dict = Body(...), current_user: User = Depends(get_admin_user)):
    """运行RAG评估"""
    from src.services.evaluation_service import EvaluationService

    try:
        service = EvaluationService()
        task_id = await service.run_evaluation(
            db_id=db_id,
            benchmark_id=params.get("benchmark_id"),
            model_config=params.get("model_config", {}),
            created_by=current_user.user_id,
        )
        return {"message": "success", "data": {"task_id": task_id}}
    except Exception as e:
        logger.error(f"启动评估失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"启动评估失败: {str(e)}")


@evaluation.get("/databases/{db_id}/history")
async def get_evaluation_history(db_id: str, current_user: User = Depends(get_admin_user)):
    """获取知识库的评估历史记录"""
    from src.services.evaluation_service import EvaluationService

    try:
        service = EvaluationService()
        history = await service.get_evaluation_history(db_id)
        return {"message": "success", "data": history}
    except Exception as e:
        logger.error(f"获取评估历史失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取评估历史失败: {str(e)}")


# =============================================================================
# 兼容前端 knowledge_api 中的旧路径（与带 db_id 的新接口并存）
# =============================================================================


@evaluation.get("/benchmarks/{benchmark_id}")
async def get_evaluation_benchmark_by_id_only(
    benchmark_id: str,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_admin_user),
):
    """仅按 benchmark_id 拉取详情（库表中含 db_id，等价于 databases/{db_id}/benchmarks/{id}）。"""
    from src.services.evaluation_service import EvaluationService

    try:
        if page < 1:
            raise HTTPException(status_code=400, detail="页码必须大于0")
        if page_size < 1 or page_size > 100:
            raise HTTPException(status_code=400, detail="每页大小必须在1-100之间")

        service = EvaluationService()
        row = await service.eval_repo.get_benchmark(benchmark_id)
        if row is None:
            raise HTTPException(status_code=404, detail="基准不存在")
        detail = await service.get_benchmark_detail_by_db(row.db_id, benchmark_id, page, page_size)
        return {"message": "success", "data": detail}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取评估基准详情失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取评估基准详情失败: {str(e)}")


@evaluation.get("/{task_id}/results")
async def get_evaluation_results_legacy_path(
    task_id: str,
    page: int = 1,
    page_size: int = 20,
    error_only: bool = False,
    current_user: User = Depends(get_admin_user),
):
    """兼容 GET /api/evaluation/{task_id}/results（evaluationApi.getEvaluationResults）。"""
    from src.services.evaluation_service import EvaluationService

    if not _EVAL_TASK_ID_RE.match(task_id):
        raise HTTPException(status_code=404, detail="Not found")
    try:
        if page < 1:
            raise HTTPException(status_code=400, detail="页码必须大于0")
        if page_size < 1 or page_size > 100:
            raise HTTPException(status_code=400, detail="每页大小必须在1-100之间")

        service = EvaluationService()
        row = await service.eval_repo.get_result(task_id)
        db_id = row.db_id if row else ""
        results = await service.get_evaluation_results_by_db(
            db_id, task_id, page=page, page_size=page_size, error_only=error_only
        )
        return {"message": "success", "data": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取评估结果失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取评估结果失败: {str(e)}")


@evaluation.delete("/{task_id}")
async def delete_evaluation_result_legacy_path(task_id: str, current_user: User = Depends(get_admin_user)):
    """兼容 DELETE /api/evaluation/{task_id}（evaluationApi.deleteEvaluationResult）。"""
    from src.services.evaluation_service import EvaluationService

    if not _EVAL_TASK_ID_RE.match(task_id):
        raise HTTPException(status_code=404, detail="Not found")
    try:
        service = EvaluationService()
        row = await service.eval_repo.get_result(task_id)
        if row is None:
            raise HTTPException(status_code=404, detail="评估结果不存在")
        await service.delete_evaluation_result_by_db(row.db_id, task_id)
        return {"message": "success", "data": None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除评估结果失败: {e}, {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"删除评估结果失败: {str(e)}")

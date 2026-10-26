"""ChromaDB 向量知识库实现，与 Milvus 共用同一套解析/索引流程与嵌入模型。"""

import asyncio
import os
import traceback
from functools import partial
from typing import Any

from src.knowledge.base import FileStatus, KnowledgeBase
from src.knowledge.indexing import process_file_to_markdown
from src.knowledge.utils.kb_utils import (
    get_embedding_config,
    split_text_into_chunks,
)
from src.models.embed import OtherEmbedding
from src.utils import logger
from src.utils.datetime_utils import utc_isoformat

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None
    Settings = None

CHROMA_AVAILABLE = chromadb is not None


class ChromaKB(KnowledgeBase):
    """基于 ChromaDB 的向量知识库，与 Milvus 共用解析/索引流程与嵌入配置。"""

    def __init__(self, work_dir: str, **kwargs):
        super().__init__(work_dir)

        if not CHROMA_AVAILABLE:
            raise ImportError("chromadb is not installed. Please install it with: pip install chromadb")

        self.chroma_db_path = os.path.join(work_dir, "chromadb")
        os.makedirs(self.chroma_db_path, exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(
            path=self.chroma_db_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collections: dict[str, Any] = {}
        self._metadata_lock = asyncio.Lock()
        logger.info("ChromaKB initialized")

    @property
    def kb_type(self) -> str:
        return "chroma"

    def _get_embed_info_model_name(self, embed_info: dict | None) -> str:
        if not embed_info:
            return "default"
        if isinstance(embed_info, dict) and "name" in embed_info:
            return embed_info.get("name", "default")
        if hasattr(embed_info, "get"):
            return embed_info.get("name", "default")
        return "default"

    async def _create_kb_instance(self, db_id: str, kb_config: dict) -> Any:
        if db_id not in self.databases_meta:
            raise ValueError(f"Database {db_id} not found")

        embed_info = self.databases_meta[db_id].get("embed_info", {})
        model_name = self._get_embed_info_model_name(embed_info)
        collection_name = db_id

        try:
            existing = self.chroma_client.get_collection(name=collection_name)
            meta = existing.metadata or {}
            if meta.get("embedding_model") != model_name:
                logger.warning(
                    f"Collection {collection_name} model mismatch: "
                    f"expected={model_name}, found={meta.get('embedding_model')}. Recreating."
                )
                self.chroma_client.delete_collection(name=collection_name)
                raise ValueError("Model mismatch, recreating collection")
            logger.info(f"Retrieved existing Chroma collection: {collection_name}")
            return existing
        except Exception:
            pass

        collection = self.chroma_client.create_collection(
            name=collection_name,
            metadata={
                "db_id": db_id,
                "embedding_model": model_name,
                "created_at": utc_isoformat(),
            },
        )
        logger.info(f"Created Chroma collection: {collection_name} (embedding_model={model_name})")
        return collection

    async def _initialize_kb_instance(self, instance: Any) -> None:
        pass

    def _get_async_embedding(self, embed_info: dict):
        if embed_info and isinstance(embed_info, dict) and embed_info.get("model_id"):
            from src.models.embed import select_embedding_model

            return select_embedding_model(embed_info["model_id"])
        config_dict = get_embedding_config(embed_info)
        return OtherEmbedding(
            model=config_dict.get("model"),
            base_url=config_dict.get("base_url"),
            api_key=config_dict.get("api_key"),
        )

    def _get_async_embedding_function(self, embed_info: dict):
        embedding_model = self._get_async_embedding(embed_info)
        return partial(embedding_model.abatch_encode, batch_size=40)

    def _get_embedding_function(self, embed_info: dict):
        embedding_model = self._get_async_embedding(embed_info)
        return partial(embedding_model.batch_encode, batch_size=40)

    async def _get_chroma_collection(self, db_id: str):
        if db_id in self.collections:
            return self.collections[db_id]
        if db_id not in self.databases_meta:
            return None
        try:
            collection = await self._create_kb_instance(db_id, {})
            await self._initialize_kb_instance(collection)
            self.collections[db_id] = collection
            return collection
        except Exception as e:
            logger.error(f"Failed to create Chroma collection for {db_id}: {e}")
            logger.error(traceback.format_exc())
            return None

    def _split_text_into_chunks(self, text: str, file_id: str, filename: str, params: dict) -> list[dict]:
        chunks = split_text_into_chunks(text, file_id, filename, params)
        for chunk in chunks:
            chunk["metadata"] = {
                "source": chunk["source"],
                "chunk_id": chunk["chunk_id"],
                "file_id": chunk["file_id"],
                "chunk_index": chunk["chunk_index"],
                "book_page": int(chunk.get("book_page", -1)),
            }
        return chunks

    async def index_file(self, db_id: str, file_id: str, operator_id: str | None = None) -> dict:
        if db_id not in self.databases_meta:
            raise ValueError(f"Database {db_id} not found")

        collection = await self._get_chroma_collection(db_id)
        if not collection:
            raise ValueError(f"Failed to get Chroma collection for {db_id}")

        embed_info = self.databases_meta[db_id].get("embed_info", {})
        embedding_function = self._get_async_embedding_function(embed_info)

        async with self._metadata_lock:
            if file_id not in self.files_meta:
                raise ValueError(f"File {file_id} not found")
            file_meta = self.files_meta[file_id]
            current_status = file_meta.get("status")
            allowed = {
                FileStatus.PARSED,
                FileStatus.ERROR_INDEXING,
                FileStatus.INDEXED,
                "done",
            }
            if current_status not in allowed:
                raise ValueError(
                    f"Cannot index file with status '{current_status}'. "
                    f"File must be parsed first (one of: {', '.join(allowed)})"
                )
            if not file_meta.get("markdown_file"):
                raise ValueError("File has not been parsed yet (no markdown_file)")
            if "error" in file_meta:
                self.files_meta[file_id].pop("error", None)
            self.files_meta[file_id]["status"] = FileStatus.INDEXING
            self.files_meta[file_id]["updated_at"] = utc_isoformat()
            if operator_id:
                self.files_meta[file_id]["updated_by"] = operator_id
            await self._save_metadata()
            params = file_meta.get("processing_params", {}) or {}
            filename = file_meta.get("filename")

        self._add_to_processing_queue(file_id)
        try:
            markdown_content = await self._read_markdown_from_minio(file_meta["markdown_file"])
            chunks = self._split_text_into_chunks(markdown_content, file_id, filename, params)
            logger.info(
                f"Split {filename} into {len(chunks)} chunks "
                f"(chunk_size={params.get('chunk_size')}, chunk_overlap={params.get('chunk_overlap')})"
            )

            if chunks:
                texts = [c["content"] for c in chunks]
                embeddings = await embedding_function(texts)
                ids = [c["id"] for c in chunks]
                documents = [c["content"] for c in chunks]
                metadatas = [c["metadata"] for c in chunks]

                await self.delete_file_chunks_only(db_id, file_id)

                batch_size = 64
                for i in range(0, len(chunks), batch_size):
                    await asyncio.to_thread(
                        collection.add,
                        ids=ids[i : i + batch_size],
                        embeddings=embeddings[i : i + batch_size],
                        documents=documents[i : i + batch_size],
                        metadatas=metadatas[i : i + batch_size],
                    )

            async with self._metadata_lock:
                self.files_meta[file_id]["status"] = FileStatus.INDEXED
                self.files_meta[file_id]["updated_at"] = utc_isoformat()
                if operator_id:
                    self.files_meta[file_id]["updated_by"] = operator_id
                await self._save_metadata()
            return self.files_meta[file_id]

        except Exception as e:
            logger.error(f"Indexing failed for {file_id}: {e}")
            async with self._metadata_lock:
                self.files_meta[file_id]["status"] = FileStatus.ERROR_INDEXING
                self.files_meta[file_id]["error"] = str(e)
                self.files_meta[file_id]["updated_at"] = utc_isoformat()
                if operator_id:
                    self.files_meta[file_id]["updated_by"] = operator_id
                await self._save_metadata()
            raise
        finally:
            self._remove_from_processing_queue(file_id)

    async def update_content(self, db_id: str, file_ids: list[str], params: dict | None = None) -> list[dict]:
        if db_id not in self.databases_meta:
            raise ValueError(f"Database {db_id} not found")

        collection = await self._get_chroma_collection(db_id)
        if not collection:
            raise ValueError(f"Failed to get Chroma collection for {db_id}")

        embed_info = self.databases_meta[db_id].get("embed_info", {})
        embedding_function = self._get_async_embedding_function(embed_info)
        params = params or {}
        content_type = params.get("content_type", "file")
        processed_items_info = []

        for file_id in file_ids:
            async with self._metadata_lock:
                if file_id not in self.files_meta:
                    logger.warning(f"File {file_id} not found in metadata, skipping")
                    continue
                file_meta = self.files_meta[file_id]
                file_path = file_meta.get("path")
                filename = file_meta.get("filename")
                if not file_path:
                    logger.warning(f"File path not found for {file_id}, skipping")
                    continue

            self._add_to_processing_queue(file_id)
            try:
                async with self._metadata_lock:
                    self.files_meta[file_id]["processing_params"] = params.copy()
                    self.files_meta[file_id]["status"] = "processing"
                    await self._save_metadata()

                if content_type != "file":
                    raise ValueError("URL 内容解析已禁用")
                markdown_content = await process_file_to_markdown(file_path, params=params)
                await self.delete_file_chunks_only(db_id, file_id)

                chunks = self._split_text_into_chunks(markdown_content, file_id, filename, params)
                if chunks:
                    texts = [c["content"] for c in chunks]
                    embeddings = await embedding_function(texts)
                    ids = [c["id"] for c in chunks]
                    documents = [c["content"] for c in chunks]
                    metadatas = [c["metadata"] for c in chunks]
                    batch_size = 64
                    for i in range(0, len(chunks), batch_size):
                        await asyncio.to_thread(
                            collection.add,
                            ids=ids[i : i + batch_size],
                            embeddings=embeddings[i : i + batch_size],
                            documents=documents[i : i + batch_size],
                            metadatas=metadatas[i : i + batch_size],
                        )

                async with self._metadata_lock:
                    self.files_meta[file_id]["status"] = "done"
                    await self._save_metadata()

                processed_items_info.append({**file_meta, "file_id": file_id, "status": "done"})
            except Exception as e:
                logger.error(f"更新 {file_path} 失败: {e}, {traceback.format_exc()}")
                async with self._metadata_lock:
                    self.files_meta[file_id]["status"] = "failed"
                    await self._save_metadata()
                processed_items_info.append({**file_meta, "file_id": file_id, "status": "failed"})
            finally:
                self._remove_from_processing_queue(file_id)

        return processed_items_info

    async def aquery(self, query_text: str, db_id: str, agent_call: bool = False, **kwargs) -> list[dict]:
        collection = await self._get_chroma_collection(db_id)
        if not collection:
            raise ValueError(f"Database {db_id} not found")

        query_params = self._get_query_params(db_id)
        merged = {**query_params, **kwargs}

        final_top_k = max(int(merged.get("final_top_k", 10)), 1)
        similarity_threshold = float(merged.get("similarity_threshold", 0.2))
        use_reranker = bool(merged.get("use_reranker", False))
        if use_reranker:
            recall_top_k = max(int(merged.get("recall_top_k", 50)), final_top_k)
        else:
            recall_top_k = final_top_k

        embed_info = self.databases_meta[db_id].get("embed_info", {})
        embed_fn = self._get_embedding_function(embed_info)
        query_embedding = embed_fn([query_text])

        try:
            result = collection.query(
                query_embeddings=query_embedding,
                n_results=recall_top_k,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error(f"Chroma query error: {e}, {traceback.format_exc()}")
            return []

        if not result or not result.get("ids") or not result["ids"][0]:
            return []

        documents = result["documents"][0]
        metadatas = result.get("metadatas") or [[]]
        distances = result.get("distances") or [[]]
        meta_list = metadatas[0] if metadatas else []
        dist_list = distances[0] if distances else []

        file_name = merged.get("file_name")

        retrieved = []
        for i, doc in enumerate(documents):
            dist = dist_list[i] if i < len(dist_list) else 1.0
            similarity = 1.0 - dist
            if similarity < similarity_threshold:
                continue
            meta = meta_list[i] if i < len(meta_list) else {}
            if file_name and file_name not in (meta.get("source") or ""):
                continue
            retrieved.append(
                {
                    "content": doc,
                    "metadata": {
                        "source": meta.get("source", ""),
                        "chunk_id": meta.get("chunk_id"),
                        "file_id": meta.get("file_id"),
                        "chunk_index": meta.get("chunk_index"),
                    },
                    "score": similarity,
                    "distance": dist,
                }
            )

        if not retrieved:
            return []

        if not use_reranker:
            return retrieved[:final_top_k]

        reranker_model = merged.get("reranker_model")
        if not reranker_model:
            raise ValueError("use_reranker=True 时必须在查询参数中提供 reranker_model")

        try:
            from src.models.rerank import get_reranker

            reranker = get_reranker(reranker_model)
            try:
                docs = [c["content"] for c in retrieved]
                rerank_scores = await reranker.acompute_score([query_text, docs], normalize=True)
                for c, s in zip(retrieved, rerank_scores):
                    c["rerank_score"] = float(s)
                retrieved.sort(key=lambda x: x.get("rerank_score", x.get("score", 0.0)), reverse=True)
                logger.info(f"Reranking completed for {db_id} with model {reranker_model}")
            finally:
                await reranker.aclose()
        except Exception as exc:
            logger.error(f"Reranking failed: {exc}, falling back to vector scores")

        return retrieved[:final_top_k]

    async def delete_file_chunks_only(self, db_id: str, file_id: str) -> None:
        collection = await self._get_chroma_collection(db_id)
        if not collection:
            return
        try:
            got = collection.get(where={"file_id": file_id}, include=[])
            ids_to_delete = got.get("ids") or []
            if not ids_to_delete:
                logger.info(f"File {file_id} not found in Chroma, skipping delete")
                return
            await asyncio.to_thread(collection.delete, ids=ids_to_delete)
            logger.info(f"Deleted {len(ids_to_delete)} chunks for file {file_id} from Chroma")
        except Exception as e:
            logger.error(f"Error deleting file {file_id} from Chroma: {e}")

    async def delete_file(self, db_id: str, file_id: str) -> None:
        await self.delete_file_chunks_only(db_id, file_id)
        async with self._metadata_lock:
            if file_id in self.files_meta:
                del self.files_meta[file_id]
                from src.repositories.knowledge_file_repository import KnowledgeFileRepository

                await KnowledgeFileRepository().delete(file_id)
                await self._save_metadata()

    async def get_file_basic_info(self, db_id: str, file_id: str) -> dict:
        if file_id not in self.files_meta:
            raise Exception(f"File not found: {file_id}")
        return {"meta": self.files_meta[file_id]}

    async def get_file_content(self, db_id: str, file_id: str) -> dict:
        if file_id not in self.files_meta:
            raise Exception(f"File not found: {file_id}")

        content_info: dict[str, Any] = {"lines": []}
        collection = await self._get_chroma_collection(db_id)
        if collection:
            try:
                got = collection.get(
                    where={"file_id": file_id},
                    include=["documents", "metadatas"],
                )
                ids = got.get("ids") or []
                docs = got.get("documents") or []
                metas = got.get("metadatas") or []
                doc_chunks = []
                for i, doc in enumerate(docs):
                    meta = metas[i] if i < len(metas) else {}
                    doc_chunks.append(
                        {
                            "id": meta.get("chunk_id", ids[i] if i < len(ids) else ""),
                            "content": doc,
                            "chunk_order_index": meta.get("chunk_index", i),
                        }
                    )
                doc_chunks.sort(key=lambda x: x.get("chunk_order_index", 0))
                content_info["lines"] = doc_chunks
            except Exception as e:
                logger.error(f"Failed to get file content from Chroma: {e}")

        file_meta = self.files_meta[file_id]
        if file_meta.get("markdown_file"):
            try:
                content_info["content"] = await self._read_markdown_from_minio(file_meta["markdown_file"])
            except Exception as e:
                logger.error(f"Failed to read markdown for {file_id}: {e}")

        return content_info

    async def get_file_info(self, db_id: str, file_id: str) -> dict:
        if file_id not in self.files_meta:
            raise Exception(f"File not found: {file_id}")
        basic = await self.get_file_basic_info(db_id, file_id)
        content = await self.get_file_content(db_id, file_id)
        return {**basic, **content}

    async def delete_database(self, db_id: str) -> dict:
        try:
            if db_id in self.collections:
                del self.collections[db_id]
            self.chroma_client.delete_collection(name=db_id)
            logger.info(f"Deleted Chroma collection for {db_id}")
        except Exception as e:
            logger.error(f"Failed to delete Chroma collection {db_id}: {e}")
        return await super().delete_database(db_id)

    def get_query_params_config(self, db_id: str, **kwargs) -> dict:
        options = [
            {
                "key": "final_top_k",
                "label": "返回 Chunk 数",
                "type": "number",
                "default": 10,
                "min": 1,
                "max": 100,
                "description": "返回的文档数量",
            },
            {
                "key": "similarity_threshold",
                "label": "相似度阈值（0-1）",
                "type": "number",
                "default": 0.2,
                "min": 0.0,
                "max": 1.0,
                "step": 0.1,
                "description": "过滤相似度低于此值的结果",
            },
            {
                "key": "include_distances",
                "label": "显示相似度",
                "type": "boolean",
                "default": True,
                "description": "在结果中显示相似度分数",
            },
            {
                "key": "use_reranker",
                "label": "启用重排序",
                "type": "boolean",
                "default": False,
                "description": "是否使用精排模型对检索结果进行重排序",
            },
            {
                "key": "reranker_model",
                "label": "重排序模型",
                "type": "select",
                "default": "",
                "options": [
                    {"label": info.name, "value": model_id}
                    for model_id, info in kwargs.get("reranker_names", {}).items()
                ],
                "description": "选择用于本次查询的重排序模型",
            },
            {
                "key": "recall_top_k",
                "label": "召回数量",
                "type": "number",
                "default": 50,
                "min": 10,
                "max": 200,
                "description": "向量检索时保留的候选数量（启用重排序时有效）",
            },
        ]
        return {"type": "chroma", "options": options}

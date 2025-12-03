"""Tool for interacting with the RAG Pipeline API.

This module provides callable tools that agents can use to interact with
the RAG Pipeline API for document ingestion, querying, and management.
The RAG Pipeline integrates Qdrant vector database with Redis caching
for production-grade retrieval-augmented generation.

Usage in agent workflows:
    - ingest_file: Upload documents to RAG collection
    - query_rag: Retrieve relevant documents and generate answers
    - list_files: List documents in collection
    - delete_file: Remove documents from collection
    - get_stats: Get collection statistics
"""

import json
from pathlib import Path
from typing import Any, Optional

import httpx
import structlog

from src.config.settings import get_settings

logger = structlog.get_logger(__name__)


async def ingest_file(
    collection: str,
    file_path: str,
) -> dict[str, Any]:
    """
    Ingest a file (PDF or text) into the RAG pipeline.

    Args:
        collection: Collection name to ingest into
        file_path: Path to the file to ingest

    Returns:
        dict with:
            - success: Boolean indicating success
            - message: Status message
            - documents_processed: Number of documents processed
            - error: Error message if request failed

    Example:
        result = await ingest_file(
            collection="knowledge_base",
            file_path="/path/to/document.pdf"
        )
    """
    settings = get_settings()

    if not settings.external_services.rag_pipeline_enabled:
        logger.warning("rag_pipeline_disabled")
        return {
            "success": False,
            "message": "RAG Pipeline is not enabled",
            "documents_processed": 0,
            "error": "RAG Pipeline is not enabled",
        }

    # Validate file exists
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        logger.error("file_not_found", file_path=file_path)
        return {
            "success": False,
            "message": f"File not found: {file_path}",
            "documents_processed": 0,
            "error": f"File not found: {file_path}",
        }

    # Build URL
    base_url = settings.external_services.rag_pipeline_base_url.rstrip("/")
    url = f"{base_url}/collections/{collection}/ingest/file"

    # Build headers
    headers = {}
    if settings.external_services.rag_pipeline_api_key:
        headers["Authorization"] = f"Bearer {settings.external_services.rag_pipeline_api_key}"

    logger.info(
        "ingesting_file_to_rag",
        collection=collection,
        file_path=file_path,
        url=url,
    )

    try:
        async with httpx.AsyncClient(
            timeout=settings.external_services.rag_pipeline_timeout
        ) as client:
            with open(file_path_obj, "rb") as f:
                files = {"file": (file_path_obj.name, f, "application/octet-stream")}
                response = await client.post(
                    url,
                    files=files,
                    headers=headers,
                )

            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"message": response.text}

            success = 200 <= response.status_code < 300

            logger.info(
                "rag_ingest_response",
                status_code=response.status_code,
                success=success,
                documents_processed=response_data.get("documents_processed", 0),
            )

            if success:
                return {
                    "success": response_data.get("success", True),
                    "message": response_data.get("message", "File ingested successfully"),
                    "documents_processed": response_data.get("documents_processed", 0),
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "message": response_data.get("message", "Failed to ingest file"),
                    "documents_processed": 0,
                    "error": response_data.get("detail", response_data.get("message")),
                }

    except httpx.TimeoutException:
        logger.error("rag_ingest_timeout", url=url, file_path=file_path)
        return {
            "success": False,
            "message": "RAG Pipeline request timed out",
            "documents_processed": 0,
            "error": "Request timed out",
        }
    except httpx.HTTPError as e:
        logger.error("rag_ingest_http_error", url=url, error=str(e))
        return {
            "success": False,
            "message": f"RAG Pipeline request failed: {str(e)}",
            "documents_processed": 0,
            "error": str(e),
        }
    except Exception as e:
        logger.error("rag_ingest_error", url=url, error=str(e), exc_info=True)
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "documents_processed": 0,
            "error": str(e),
        }


async def ingest_batch(
    collection: str,
    file_paths: list[str],
) -> dict[str, Any]:
    """
    Ingest multiple files into the RAG pipeline.

    Args:
        collection: Collection name to ingest into
        file_paths: List of file paths to ingest

    Returns:
        dict with:
            - success: Boolean indicating success
            - message: Status message
            - documents_processed: Total number of documents processed
            - error: Error message if request failed

    Example:
        result = await ingest_batch(
            collection="knowledge_base",
            file_paths=["/path/to/doc1.pdf", "/path/to/doc2.txt"]
        )
    """
    settings = get_settings()

    if not settings.external_services.rag_pipeline_enabled:
        logger.warning("rag_pipeline_disabled")
        return {
            "success": False,
            "message": "RAG Pipeline is not enabled",
            "documents_processed": 0,
            "error": "RAG Pipeline is not enabled",
        }

    # Validate files exist
    file_objs = []
    for fp in file_paths:
        file_path_obj = Path(fp)
        if not file_path_obj.exists():
            logger.warning("file_not_found_in_batch", file_path=fp)
            continue
        file_objs.append(file_path_obj)

    if not file_objs:
        return {
            "success": False,
            "message": "No valid files found",
            "documents_processed": 0,
            "error": "No valid files found",
        }

    # Build URL
    base_url = settings.external_services.rag_pipeline_base_url.rstrip("/")
    url = f"{base_url}/collections/{collection}/ingest/batch"

    # Build headers
    headers = {}
    if settings.external_services.rag_pipeline_api_key:
        headers["Authorization"] = f"Bearer {settings.external_services.rag_pipeline_api_key}"

    logger.info(
        "ingesting_batch_to_rag",
        collection=collection,
        file_count=len(file_objs),
        url=url,
    )

    try:
        async with httpx.AsyncClient(
            timeout=settings.external_services.rag_pipeline_timeout * 2  # Longer timeout for batch
        ) as client:
            files = [
                ("files", (fp.name, open(fp, "rb"), "application/octet-stream"))
                for fp in file_objs
            ]
            
            response = await client.post(
                url,
                files=files,
                headers=headers,
            )

            # Close file handles
            for _, (_, f, _) in files:
                f.close()

            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"message": response.text}

            success = 200 <= response.status_code < 300

            logger.info(
                "rag_batch_ingest_response",
                status_code=response.status_code,
                success=success,
                documents_processed=response_data.get("documents_processed", 0),
            )

            if success:
                return {
                    "success": response_data.get("success", True),
                    "message": response_data.get("message", "Files ingested successfully"),
                    "documents_processed": response_data.get("documents_processed", 0),
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "message": response_data.get("message", "Failed to ingest files"),
                    "documents_processed": 0,
                    "error": response_data.get("detail", response_data.get("message")),
                }

    except httpx.TimeoutException:
        logger.error("rag_batch_ingest_timeout", url=url)
        return {
            "success": False,
            "message": "RAG Pipeline batch request timed out",
            "documents_processed": 0,
            "error": "Request timed out",
        }
    except httpx.HTTPError as e:
        logger.error("rag_batch_ingest_http_error", url=url, error=str(e))
        return {
            "success": False,
            "message": f"RAG Pipeline request failed: {str(e)}",
            "documents_processed": 0,
            "error": str(e),
        }
    except Exception as e:
        logger.error("rag_batch_ingest_error", url=url, error=str(e), exc_info=True)
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "documents_processed": 0,
            "error": str(e),
        }


async def query_rag(
    query: str,
    collection: Optional[str] = None,
    top_k: int = 5,
    rerank: bool = True,
    rerank_top_k: Optional[int] = None,
) -> dict[str, Any]:
    """
    Query the RAG pipeline to retrieve relevant documents.

    Args:
        query: Query text
        collection: Collection name (defaults to configured default)
        top_k: Number of results to retrieve
        rerank: Whether to rerank results
        rerank_top_k: Number of results after reranking

    Returns:
        dict with:
            - query: Original query
            - results: List of search results with id, text, score, metadata
            - total_results: Number of results returned
            - success: Boolean indicating success
            - error: Error message if request failed

    Example:
        result = await query_rag(
            query="What is the capital of France?",
            collection="knowledge_base",
            top_k=5
        )
    """
    settings = get_settings()

    if not settings.external_services.rag_pipeline_enabled:
        logger.warning("rag_pipeline_disabled")
        return {
            "query": query,
            "results": [],
            "total_results": 0,
            "success": False,
            "error": "RAG Pipeline is not enabled",
        }

    # Use default collection if not provided
    if not collection:
        collection = settings.external_services.rag_pipeline_default_collection

    # Build URL
    base_url = settings.external_services.rag_pipeline_base_url.rstrip("/")
    url = f"{base_url}/collections/{collection}/query"

    # Build headers
    headers = {"Content-Type": "application/json"}
    if settings.external_services.rag_pipeline_api_key:
        headers["Authorization"] = f"Bearer {settings.external_services.rag_pipeline_api_key}"

    # Build request body
    payload = {
        "query": query,
        "top_k": top_k,
        "rerank": rerank,
    }
    if rerank_top_k is not None:
        payload["rerank_top_k"] = rerank_top_k

    logger.info(
        "querying_rag",
        collection=collection,
        query_length=len(query),
        top_k=top_k,
        rerank=rerank,
        url=url,
    )

    try:
        async with httpx.AsyncClient(
            timeout=settings.external_services.rag_pipeline_timeout
        ) as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
            )

            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"error": response.text}

            success = 200 <= response.status_code < 300

            logger.info(
                "rag_query_response",
                status_code=response.status_code,
                success=success,
                total_results=response_data.get("total_results", 0),
            )

            if success:
                return {
                    "query": response_data.get("query", query),
                    "results": response_data.get("results", []),
                    "total_results": response_data.get("total_results", 0),
                    "success": True,
                    "error": None,
                }
            else:
                return {
                    "query": query,
                    "results": [],
                    "total_results": 0,
                    "success": False,
                    "error": response_data.get("detail", response_data.get("error", "Query failed")),
                }

    except httpx.TimeoutException:
        logger.error("rag_query_timeout", url=url)
        return {
            "query": query,
            "results": [],
            "total_results": 0,
            "success": False,
            "error": "Query timed out",
        }
    except httpx.HTTPError as e:
        logger.error("rag_query_http_error", url=url, error=str(e))
        return {
            "query": query,
            "results": [],
            "total_results": 0,
            "success": False,
            "error": str(e),
        }
    except Exception as e:
        logger.error("rag_query_error", url=url, error=str(e), exc_info=True)
        return {
            "query": query,
            "results": [],
            "total_results": 0,
            "success": False,
            "error": str(e),
        }


async def list_files(
    collection: Optional[str] = None,
) -> dict[str, Any]:
    """
    List all files in a RAG collection.

    Args:
        collection: Collection name (defaults to configured default)

    Returns:
        dict with:
            - collection: Collection name
            - files: List of file names
            - total_files: Number of files
            - success: Boolean indicating success
            - error: Error message if request failed

    Example:
        result = await list_files(collection="knowledge_base")
    """
    settings = get_settings()

    if not settings.external_services.rag_pipeline_enabled:
        logger.warning("rag_pipeline_disabled")
        return {
            "collection": collection or "",
            "files": [],
            "total_files": 0,
            "success": False,
            "error": "RAG Pipeline is not enabled",
        }

    # Use default collection if not provided
    if not collection:
        collection = settings.external_services.rag_pipeline_default_collection

    # Build URL
    base_url = settings.external_services.rag_pipeline_base_url.rstrip("/")
    url = f"{base_url}/collections/{collection}/files"

    # Build headers
    headers = {}
    if settings.external_services.rag_pipeline_api_key:
        headers["Authorization"] = f"Bearer {settings.external_services.rag_pipeline_api_key}"

    logger.info("listing_rag_files", collection=collection, url=url)

    try:
        async with httpx.AsyncClient(
            timeout=settings.external_services.rag_pipeline_timeout
        ) as client:
            response = await client.get(url, headers=headers)

            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"error": response.text}

            success = 200 <= response.status_code < 300

            if success:
                files = response_data.get("files", [])
                return {
                    "collection": collection,
                    "files": files,
                    "total_files": len(files),
                    "success": True,
                    "error": None,
                }
            else:
                return {
                    "collection": collection,
                    "files": [],
                    "total_files": 0,
                    "success": False,
                    "error": response_data.get("detail", "Failed to list files"),
                }

    except httpx.TimeoutException:
        logger.error("rag_list_files_timeout", url=url)
        return {
            "collection": collection,
            "files": [],
            "total_files": 0,
            "success": False,
            "error": "Request timed out",
        }
    except Exception as e:
        logger.error("rag_list_files_error", url=url, error=str(e), exc_info=True)
        return {
            "collection": collection,
            "files": [],
            "total_files": 0,
            "success": False,
            "error": str(e),
        }


async def delete_file(
    filename: str,
    collection: Optional[str] = None,
) -> dict[str, Any]:
    """
    Delete a file and all its chunks from a RAG collection.

    Args:
        filename: Name of the file to delete
        collection: Collection name (defaults to configured default)

    Returns:
        dict with:
            - success: Boolean indicating success
            - message: Status message
            - error: Error message if request failed

    Example:
        result = await delete_file(
            filename="document.pdf",
            collection="knowledge_base"
        )
    """
    settings = get_settings()

    if not settings.external_services.rag_pipeline_enabled:
        logger.warning("rag_pipeline_disabled")
        return {
            "success": False,
            "message": "RAG Pipeline is not enabled",
            "error": "RAG Pipeline is not enabled",
        }

    # Use default collection if not provided
    if not collection:
        collection = settings.external_services.rag_pipeline_default_collection

    # Build URL
    base_url = settings.external_services.rag_pipeline_base_url.rstrip("/")
    url = f"{base_url}/collections/{collection}/files/{filename}"

    # Build headers
    headers = {}
    if settings.external_services.rag_pipeline_api_key:
        headers["Authorization"] = f"Bearer {settings.external_services.rag_pipeline_api_key}"

    logger.info("deleting_rag_file", collection=collection, filename=filename, url=url)

    try:
        async with httpx.AsyncClient(
            timeout=settings.external_services.rag_pipeline_timeout
        ) as client:
            response = await client.delete(url, headers=headers)

            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"message": response.text}

            success = 200 <= response.status_code < 300

            if success:
                return {
                    "success": True,
                    "message": response_data.get("message", f"File '{filename}' deleted successfully"),
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "message": response_data.get("message", "Failed to delete file"),
                    "error": response_data.get("detail", "Failed to delete file"),
                }

    except httpx.TimeoutException:
        logger.error("rag_delete_file_timeout", url=url)
        return {
            "success": False,
            "message": "Request timed out",
            "error": "Request timed out",
        }
    except Exception as e:
        logger.error("rag_delete_file_error", url=url, error=str(e), exc_info=True)
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "error": str(e),
        }


async def get_stats(
    collection: Optional[str] = None,
) -> dict[str, Any]:
    """
    Get detailed statistics about a RAG collection.

    Args:
        collection: Collection name (defaults to configured default)

    Returns:
        dict with collection statistics and metadata

    Example:
        result = await get_stats(collection="knowledge_base")
    """
    settings = get_settings()

    if not settings.external_services.rag_pipeline_enabled:
        logger.warning("rag_pipeline_disabled")
        return {
            "success": False,
            "error": "RAG Pipeline is not enabled",
        }

    # Use default collection if not provided
    if not collection:
        collection = settings.external_services.rag_pipeline_default_collection

    # Build URL
    base_url = settings.external_services.rag_pipeline_base_url.rstrip("/")
    url = f"{base_url}/collections/{collection}/stats"

    # Build headers
    headers = {}
    if settings.external_services.rag_pipeline_api_key:
        headers["Authorization"] = f"Bearer {settings.external_services.rag_pipeline_api_key}"

    logger.info("getting_rag_stats", collection=collection, url=url)

    try:
        async with httpx.AsyncClient(
            timeout=settings.external_services.rag_pipeline_timeout
        ) as client:
            response = await client.get(url, headers=headers)

            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"error": response.text}

            success = 200 <= response.status_code < 300

            if success:
                response_data["success"] = True
                response_data["error"] = None
                return response_data
            else:
                return {
                    "success": False,
                    "error": response_data.get("detail", "Failed to get stats"),
                }

    except httpx.TimeoutException:
        logger.error("rag_stats_timeout", url=url)
        return {
            "success": False,
            "error": "Request timed out",
        }
    except Exception as e:
        logger.error("rag_stats_error", url=url, error=str(e), exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }

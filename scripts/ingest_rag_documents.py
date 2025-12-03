#!/usr/bin/env python3
"""
RAG Document Ingestion Script

This script uploads documents to the RAG Pipeline API for processing and indexing
in Qdrant vector database. It supports single file ingestion, batch ingestion,
and directory scanning.

**Remote RAG Pipeline Service**
The RAG Pipeline is hosted at http://10.42.65.199:8000
API Documentation: http://10.42.65.199:8000/docs

**Required Environment Variables**
- RAG_PIPELINE_BASE_URL: URL of the RAG Pipeline service (default: http://10.42.65.199:8000)
- RAG_PIPELINE_API_KEY: API key for authentication (optional, if service requires auth)
- RAG_PIPELINE_ENABLED: Set to 'true' to enable RAG features (default: true)
- RAG_PIPELINE_DEFAULT_COLLECTION: Default collection name (default: knowledge_base)

**Prerequisites**
1. Ensure the RAG Pipeline service is accessible at the configured URL
2. Qdrant vector database should be running (local or remote)
3. Configure environment variables in .env file

Usage:
    # Ingest a single file
    python scripts/ingest_rag_documents.py --file document.pdf --collection knowledge_base
    
    # Ingest all files in a directory
    python scripts/ingest_rag_documents.py --directory ./docs --collection knowledge_base
    
    # Ingest multiple specific files
    python scripts/ingest_rag_documents.py --files doc1.pdf doc2.txt doc3.md --collection kb
    
    # Use custom RAG Pipeline URL
    python scripts/ingest_rag_documents.py --file doc.pdf --url http://10.42.65.199:8000

For more information, see: docs/RAG_SETUP.md
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def ingest_file(
    file_path: Path,
    collection: str,
    base_url: str,
    api_key: Optional[str] = None,
    timeout: int = 60,
) -> dict:
    """
    Ingest a single file into the RAG pipeline.
    
    Args:
        file_path: Path to the file to ingest
        collection: Collection name
        base_url: RAG Pipeline base URL
        api_key: Optional API key for authentication
        timeout: Request timeout in seconds
        
    Returns:
        Response dictionary with success status and details
    """
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return {
            "success": False,
            "message": f"File not found: {file_path}",
            "documents_processed": 0,
        }
    
    url = f"{base_url.rstrip('/')}/collections/{collection}/ingest/file"
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    logger.info(f"Ingesting file: {file_path.name} -> {collection}")
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "application/octet-stream")}
                response = await client.post(url, files=files, headers=headers)
            
            response_data = response.json() if response.status_code < 400 else {"error": response.text}
            
            if 200 <= response.status_code < 300:
                logger.info(
                    f"✅ Successfully ingested {file_path.name} "
                    f"({response_data.get('documents_processed', 0)} chunks)"
                )
                return response_data
            else:
                logger.error(
                    f"❌ Failed to ingest {file_path.name}: "
                    f"{response_data.get('detail', response_data.get('message', 'Unknown error'))}"
                )
                return {
                    "success": False,
                    "message": response_data.get("detail", response_data.get("message", "Ingestion failed")),
                    "documents_processed": 0,
                }
    
    except httpx.TimeoutException:
        logger.error(f"❌ Timeout while ingesting {file_path.name}")
        return {
            "success": False,
            "message": "Request timed out",
            "documents_processed": 0,
        }
    except Exception as e:
        logger.error(f"❌ Error ingesting {file_path.name}: {e}")
        return {
            "success": False,
            "message": str(e),
            "documents_processed": 0,
        }


async def ingest_batch(
    file_paths: list[Path],
    collection: str,
    base_url: str,
    api_key: Optional[str] = None,
    timeout: int = 120,
) -> dict:
    """
    Ingest multiple files in a single batch request.
    
    Args:
        file_paths: List of file paths to ingest
        collection: Collection name
        base_url: RAG Pipeline base URL
        api_key: Optional API key for authentication
        timeout: Request timeout in seconds
        
    Returns:
        Response dictionary with success status and details
    """
    # Filter out non-existent files
    valid_files = [fp for fp in file_paths if fp.exists()]
    
    if not valid_files:
        logger.error("No valid files found for batch ingestion")
        return {
            "success": False,
            "message": "No valid files found",
            "documents_processed": 0,
        }
    
    url = f"{base_url.rstrip('/')}/collections/{collection}/ingest/batch"
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    logger.info(f"Ingesting batch of {len(valid_files)} files -> {collection}")
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            files = [
                ("files", (fp.name, open(fp, "rb"), "application/octet-stream"))
                for fp in valid_files
            ]
            
            response = await client.post(url, files=files, headers=headers)
            
            # Close file handles
            for _, (_, f, _) in files:
                f.close()
            
            response_data = response.json() if response.status_code < 400 else {"error": response.text}
            
            if 200 <= response.status_code < 300:
                logger.info(
                    f"✅ Successfully ingested {len(valid_files)} files "
                    f"({response_data.get('documents_processed', 0)} chunks)"
                )
                return response_data
            else:
                logger.error(
                    f"❌ Batch ingestion failed: "
                    f"{response_data.get('detail', response_data.get('message', 'Unknown error'))}"
                )
                return {
                    "success": False,
                    "message": response_data.get("detail", response_data.get("message", "Batch ingestion failed")),
                    "documents_processed": 0,
                }
    
    except httpx.TimeoutException:
        logger.error("❌ Timeout during batch ingestion")
        return {
            "success": False,
            "message": "Request timed out",
            "documents_processed": 0,
        }
    except Exception as e:
        logger.error(f"❌ Error during batch ingestion: {e}")
        return {
            "success": False,
            "message": str(e),
            "documents_processed": 0,
        }


async def list_collection_stats(
    collection: str,
    base_url: str,
    api_key: Optional[str] = None,
) -> None:
    """
    Display statistics for a collection.
    
    Args:
        collection: Collection name
        base_url: RAG Pipeline base URL
        api_key: Optional API key for authentication
    """
    url = f"{base_url.rstrip('/')}/collections/{collection}/stats"
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers)
            
            if 200 <= response.status_code < 300:
                stats = response.json()
                logger.info("\n📊 Collection Statistics:")
                logger.info(f"   Collection: {collection}")
                
                if "total_documents" in stats:
                    logger.info(f"   Total Documents: {stats['total_documents']}")
                if "total_chunks" in stats:
                    logger.info(f"   Total Chunks: {stats['total_chunks']}")
                if "total_files" in stats:
                    logger.info(f"   Total Files: {stats['total_files']}")
                
                # Display other stats
                for key, value in stats.items():
                    if key not in ["total_documents", "total_chunks", "total_files", "success", "error"]:
                        logger.info(f"   {key.replace('_', ' ').title()}: {value}")
            else:
                logger.warning(f"Could not retrieve stats: {response.status_code}")
    
    except Exception as e:
        logger.warning(f"Could not retrieve stats: {e}")


def find_documents_in_directory(
    directory: Path,
    extensions: tuple[str, ...] = (".pdf", ".txt", ".md", ".doc", ".docx"),
    recursive: bool = True,
) -> list[Path]:
    """
    Find all documents in a directory.
    
    Args:
        directory: Directory to search
        extensions: File extensions to include
        recursive: Whether to search recursively
        
    Returns:
        List of file paths
    """
    files = []
    
    if recursive:
        for ext in extensions:
            files.extend(directory.rglob(f"*{ext}"))
    else:
        for ext in extensions:
            files.extend(directory.glob(f"*{ext}"))
    
    return sorted(files)


async def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Ingest documents into RAG Pipeline for vector indexing"
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--file",
        type=Path,
        help="Single file to ingest"
    )
    input_group.add_argument(
        "--files",
        type=Path,
        nargs="+",
        help="Multiple files to ingest"
    )
    input_group.add_argument(
        "--directory",
        type=Path,
        help="Directory containing documents to ingest"
    )
    
    # Configuration options
    parser.add_argument(
        "--collection",
        default="knowledge_base",
        help="Collection name (default: knowledge_base)"
    )
    parser.add_argument(
        "--url",
        help="RAG Pipeline base URL (default: from settings)"
    )
    parser.add_argument(
        "--api-key",
        help="API key for authentication (default: from settings)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Request timeout in seconds (default: 60)"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Use batch ingestion for multiple files"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Search directories recursively (default: true)"
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".pdf", ".txt", ".md", ".doc", ".docx"],
        help="File extensions to include (default: .pdf .txt .md .doc .docx)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show collection statistics after ingestion"
    )
    
    args = parser.parse_args()
    
    # Load settings
    settings = get_settings()
    
    # Resolve configuration
    base_url = args.url or settings.external_services.rag_pipeline_base_url
    api_key = args.api_key or settings.external_services.rag_pipeline_api_key
    
    if not settings.external_services.rag_pipeline_enabled and not args.url:
        logger.error("RAG Pipeline is not enabled. Set RAG_PIPELINE_ENABLED=true or use --url")
        sys.exit(1)
    
    logger.info(f"🚀 RAG Document Ingestion")
    logger.info(f"   Pipeline URL: {base_url}")
    logger.info(f"   Collection: {args.collection}")
    
    # Collect files to ingest
    files_to_ingest: list[Path] = []
    
    if args.file:
        files_to_ingest = [args.file]
    elif args.files:
        files_to_ingest = args.files
    elif args.directory:
        if not args.directory.exists() or not args.directory.is_dir():
            logger.error(f"Directory not found: {args.directory}")
            sys.exit(1)
        
        logger.info(f"Scanning directory: {args.directory}")
        files_to_ingest = find_documents_in_directory(
            args.directory,
            extensions=tuple(args.extensions),
            recursive=args.recursive,
        )
        logger.info(f"Found {len(files_to_ingest)} documents")
    
    if not files_to_ingest:
        logger.error("No files to ingest")
        sys.exit(1)
    
    # Perform ingestion
    total_docs_processed = 0
    successful_files = 0
    failed_files = 0
    
    if args.batch and len(files_to_ingest) > 1:
        # Batch ingestion
        result = await ingest_batch(
            files_to_ingest,
            args.collection,
            base_url,
            api_key,
            args.timeout * 2,  # Longer timeout for batch
        )
        
        if result.get("success"):
            successful_files = len(files_to_ingest)
            total_docs_processed = result.get("documents_processed", 0)
        else:
            failed_files = len(files_to_ingest)
    
    else:
        # Sequential ingestion
        for file_path in files_to_ingest:
            result = await ingest_file(
                file_path,
                args.collection,
                base_url,
                api_key,
                args.timeout,
            )
            
            if result.get("success"):
                successful_files += 1
                total_docs_processed += result.get("documents_processed", 0)
            else:
                failed_files += 1
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 Ingestion Summary:")
    logger.info(f"   Total Files: {len(files_to_ingest)}")
    logger.info(f"   ✅ Successful: {successful_files}")
    logger.info(f"   ❌ Failed: {failed_files}")
    logger.info(f"   📄 Total Chunks Processed: {total_docs_processed}")
    logger.info("=" * 60)
    
    # Show stats if requested
    if args.stats:
        await list_collection_stats(args.collection, base_url, api_key)
    
    sys.exit(0 if failed_files == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())

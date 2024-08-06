# api/endpoints.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime, timedelta
import asyncio
from config import MAX_DEPTH, MAX_URLS, DB_NAME
from license.license import is_valid_license, create_license
from crawler.crawler import crawl
from database.db import get_results

router = APIRouter()

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CrawlRequest(BaseModel):
    license_key: str
    url: str
    max_depth: Optional[int] = MAX_DEPTH
    max_urls: Optional[int] = MAX_URLS

@router.post('/crawl')
async def start_crawl(request: CrawlRequest):
    logger.debug(f"Received crawl request: {request}")

    if not await is_valid_license(request.license_key):
        logger.warning(f"Invalid or expired license key: {request.license_key}")
        raise HTTPException(status_code=403, detail="Invalid or expired license key")

    asyncio.create_task(crawl(request.url, request.max_depth, request.max_urls))
    return {"message": "Crawl started successfully"}

@router.get('/results')
async def get_crawl_results(license_key: str, page: int = 1, per_page: int = 20):
    logger.debug(f"Received request for crawl results. License key: {license_key}")

    if not await is_valid_license(license_key):
        logger.warning(f"Invalid or expired license key: {license_key}")
        raise HTTPException(status_code=403, detail="Invalid or expired license key")

    results, total_results = await get_results(page, per_page)
    return {
        "results": results,
        "page": page,
        "per_page": per_page,
        "total_results": total_results
    }

class LicenseRequest(BaseModel):
    key: str
    type: str

@router.post('/license')
async def create_license_endpoint(request: LicenseRequest):
    logger.debug(f"Received license creation request: {request}")

    expiration = None
    if request.type == 'subscription':
        expiration = (datetime.now() + timedelta(days=30)).isoformat()

    success = await create_license(request.key, request.type, expiration)
    if success:
        return {"message": "License created successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to create license")
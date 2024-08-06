# crawler.py
import logging
import json
from urllib.parse import urljoin, urlparse
from datetime import datetime
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import aiosqlite
from config import DB_NAME, MAX_URLS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def is_internal_link(base_url, link):
    return urlparse(link).netloc == urlparse(base_url).netloc or not urlparse(link).netloc

async def fetch_with_playwright(url, semaphore):
    async with semaphore:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context()
                page = await context.new_page()
                await page.goto(url, timeout=60000, wait_until='networkidle')
                content = await page.content()
                return content
            except Exception as e:
                logger.error(f"Error fetching {url} with Playwright: {str(e)}")
                return None
            finally:
                await browser.close()

async def crawl_page(url, base_url, depth, max_depth, semaphore):
    if depth > max_depth:
        return []

    content = await fetch_with_playwright(url, semaphore)
    if content is None:
        return []

    soup = BeautifulSoup(content, 'html.parser')
    internal_links = []
    external_links = []

    for a_tag in soup.find_all('a', href=True):
        link = urljoin(url, a_tag['href'])
        if await is_internal_link(base_url, link):
            internal_links.append(link)
        else:
            external_links.append(link)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO crawls (url, depth, internal_links, external_links, title, crawled_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (url, depth, json.dumps(internal_links), json.dumps(external_links),
              soup.title.string if soup.title else None, datetime.now().isoformat()))
        await db.commit()

    logger.info(f"Crawled: {url} (Depth: {depth})")
    logger.info(f"Found {len(internal_links)} internal and {len(external_links)} external links")

    return internal_links

async def crawl(base_url, max_depth, max_urls=MAX_URLS):
    queue = [(base_url, 0)]
    visited = set()
    semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

    while queue and len(visited) < max_urls:
        url, depth = queue.pop(0)
        if url not in visited:
            visited.add(url)
            new_links = await crawl_page(url, base_url, depth, max_depth, semaphore)
            for link in new_links:
                if link not in visited:
                    queue.append((link, depth + 1))

    logger.info(f"Crawl completed. Visited {len(visited)} URLs.")
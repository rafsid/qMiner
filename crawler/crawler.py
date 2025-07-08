import logging
import json
from urllib.parse import urljoin, urlparse
from datetime import datetime
import asyncio
import re
from bs4 import BeautifulSoup
import aiohttp
import aiosqlite
from config import DB_NAME, MAX_URLS, API_KEY

logger = logging.getLogger(__name__)


async def call_api(url):
    api_url = f'https://r.jina.ai/{url}'
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API call failed for {url}. Status: {response.status}")
    except Exception as e:
        logger.error(f"API call error for {url}: {str(e)}")
    return None

async def is_internal_link(base_url, link):
    return urlparse(link).netloc == urlparse(base_url).netloc or not urlparse(link).netloc

async def fetch_url(url, session):
    try:
        async with session.get(url, timeout=30) as response:
            return await response.text()
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
        return None

async def crawl_page(url, base_url, depth, max_depth, session):
    if depth > max_depth:
        return []

    logger.info(f"Crawling: {url} (Depth: {depth})")

    # First, try to get data from API
    api_data = await call_api(url)

    if api_data:
        # Process API data
        title = api_data.get('title', '')
        body_text = api_data.get('body', '')
        internal_links = api_data.get('internal_links', [])
        external_links = api_data.get('external_links', [])
    else:
        # If API doesn't provide data, proceed with regular crawling
        content = await fetch_url(url, session)
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

        title = soup.title.string if soup.title else ''
        body_text = soup.body.get_text(separator=' ', strip=True) if soup.body else ''

    body_text = re.sub(r'\s+', ' ', body_text).strip()

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO crawls (url, depth, internal_links, external_links, title, body_text, crawled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (url, depth, json.dumps(internal_links), json.dumps(external_links),
              title, body_text, datetime.now().isoformat()))
        await db.commit()

    logger.info(f"Crawled: {url} (Depth: {depth})")
    logger.info(f"Found {len(internal_links)} internal and {len(external_links)} external links")

    return internal_links

async def crawl(base_url, max_depth, max_urls=MAX_URLS):
    queue = [(base_url, 0)]
    visited = set()

    async with aiohttp.ClientSession() as session:
        while queue and len(visited) < max_urls:
            url, depth = queue.pop(0)
            if url not in visited:
                visited.add(url)
                new_links = await crawl_page(url, base_url, depth, max_depth, session)
                for link in new_links:
                    if link not in visited:
                        queue.append((link, depth + 1))

            logger.info(f"Progress: Crawled {len(visited)} URLs")

    logger.info(f"Crawl completed. Visited {len(visited)} URLs.")
    return len(visited)
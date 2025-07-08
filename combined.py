# ./database/db.py
# db.py
import aiosqlite
from config import DB_NAME
import logging

logger = logging.getLogger(__name__)

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS crawls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                depth INTEGER NOT NULL,
                internal_links TEXT,
                external_links TEXT,
                title TEXT,
                body_text TEXT,
                crawled_at TIMESTAMP
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_crawls_url ON crawls(url)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_crawls_crawled_at ON crawls(crawled_at)")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                expiration TIMESTAMP
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses(key)")
        await db.commit()
    logger.info("Database initialized successfully")

async def get_db():
    db = await aiosqlite.connect(DB_NAME)
    try:
        yield db
    finally:
        await db.close()

async def get_results(page, per_page):
    offset = (page - 1) * per_page
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT COUNT(*) as count FROM crawls") as cursor:
            total_results = (await cursor.fetchone())['count']
        query = """
            SELECT id, url, depth, title, body_text, crawled_at
            FROM crawls
            ORDER BY crawled_at DESC
            LIMIT ? OFFSET ?
        """
        async with db.execute(query, (per_page, offset)) as cursor:
            results = [dict(row) for row in await cursor.fetchall()]
    return results, total_results

async def insert_crawl_result(url, depth, internal_links, external_links, title, body_text, crawled_at):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO crawls (url, depth, internal_links, external_links, title, body_text, crawled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (url, depth, internal_links, external_links, title, body_text, crawled_at))
        await db.commit()
    logger.info(f"Inserted crawl result for URL: {url}")

# ./database/__init__.py


# ./run.py
# run.py
import os
import sys
import socket
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from termcolor import colored
import uvicorn
import asyncio
from qminer import app
from database.db import init_db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def find_available_port(start_port=5000, max_port=6000):
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    raise IOError("No free ports found in range")

class SourceCodeChangeHandler(FileSystemEventHandler):
    def __init__(self, restart_function):
        self.restart_function = restart_function
        self.last_modified = time.time()

    def on_modified(self, event):
        if event.src_path.endswith('.py') and time.time() - self.last_modified > 1:
            self.last_modified = time.time()
            print(colored(f"\n🔄 File {event.src_path} has been modified.", 'yellow'))
            print(colored(" Restarting the server...\n", 'yellow'))
            self.restart_function()

async def init_application():
    print(colored("Initializing database...", 'cyan'))
    await init_db()
    print(colored("Database initialized.", 'green'))

def run_server(port):
    uvicorn.run("qminer:app", host="0.0.0.0", port=port, reload=True)

def main():
    asyncio.run(init_application())

    try:
        port = find_available_port()
        print(colored(f"\n🚀 Starting qMiner on port {port}", 'green'))
        print(colored(f" http://0.0.0.0:{port}\n", 'cyan'))

        event_handler = SourceCodeChangeHandler(lambda: run_server(port))
        observer = Observer()
        observer.schedule(event_handler, path='.', recursive=True)
        observer.start()

        run_server(port)

    except Exception as e:
        print(colored(f"Error starting qMiner: {str(e)}", 'red'), file=sys.stderr)
        sys.exit(1)
    finally:
        observer.stop()
        observer.join()

    print(colored("\n✨✨✨ qMiner task completed! ✨✨✨", 'magenta'))

if __name__ == "__main__":
    main()

# ./config.py
# config.py
import os
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables from .env file
load_dotenv()

@lru_cache()
def get_config():
    return {
        'DB_NAME': os.getenv('DB_NAME', 'crawler.db'),
        'MAX_DEPTH': int(os.getenv('MAX_DEPTH', 5)),
        'MAX_URLS': int(os.getenv('MAX_URLS', 1000)),
        'SECRET_KEY': os.getenv('SECRET_KEY', 'your_secret_key_here'),
        'ALLOWED_HOSTS': os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(','),
        'DEBUG': os.getenv('DEBUG', 'False').lower() in ('true', '1', 't'),
        'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
        'CRAWLER_TIMEOUT': int(os.getenv('CRAWLER_TIMEOUT', 60)),
        'MAX_CONCURRENT_CRAWLS': int(os.getenv('MAX_CONCURRENT_CRAWLS', 10)),
        'API_RATE_LIMIT': os.getenv('API_RATE_LIMIT', '100/minute'),
        'DATABASE_URL': os.getenv('DATABASE_URL', f"sqlite:///{os.getenv('DB_NAME', 'crawler.db')}"),
    }

# Use the cached config
config = get_config()

# Export individual settings for easier imports
DB_NAME = config['DB_NAME']
MAX_DEPTH = config['MAX_DEPTH']
MAX_URLS = config['MAX_URLS']
SECRET_KEY = config['SECRET_KEY']
ALLOWED_HOSTS = config['ALLOWED_HOSTS']
DEBUG = config['DEBUG']
LOG_LEVEL = config['LOG_LEVEL']
CRAWLER_TIMEOUT = config['CRAWLER_TIMEOUT']
MAX_CONCURRENT_CRAWLS = config['MAX_CONCURRENT_CRAWLS']
API_RATE_LIMIT = config['API_RATE_LIMIT']
DATABASE_URL = config['DATABASE_URL']

# ./license/__init__.py


# ./license/license.py
# license.py
import logging
from datetime import datetime, timedelta
import aiosqlite
import secrets
from config import DB_NAME

logger = logging.getLogger(__name__)

async def is_valid_license(key):
    logger.debug(f"Checking license key: {key}")
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM licenses WHERE key = ?", (key,)) as cursor:
            license = await cursor.fetchone()
            
    if not license:
        logger.warning(f"License key not found: {key}")
        return False
    
    if license[2] == 'subscription':
        is_valid = datetime.now() < datetime.fromisoformat(license[3])
        logger.debug(f"Subscription license valid: {is_valid}")
        return is_valid
    
    logger.debug("One-time license, always valid")
    return True

async def create_license(key, license_type, expiration=None):
    if not key:
        key = secrets.token_urlsafe(16)  # Generate a secure random key if not provided
    
    if license_type == 'subscription' and not expiration:
        expiration = (datetime.now() + timedelta(days=30)).isoformat()
    
    logger.debug(f"Creating license: key={key}, type={license_type}, expiration={expiration}")
    
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("INSERT INTO licenses (key, type, expiration) VALUES (?, ?, ?)",
                             (key, license_type, expiration))
            await db.commit()
        logger.info(f"License created successfully: {key}")
        return key
    except aiosqlite.IntegrityError:
        logger.warning(f"Attempt to create duplicate license key: {key}")
        return None
    except Exception as e:
        logger.error(f"Error creating license: {str(e)}")
        return None

async def revoke_license(key):
    logger.debug(f"Revoking license: {key}")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM licenses WHERE key = ?", (key,))
        changes = db.total_changes
        await db.commit()
    
    if changes:
        logger.info(f"License revoked successfully: {key}")
        return True
    else:
        logger.warning(f"License not found for revocation: {key}")
        return False

async def update_license_expiration(key, new_expiration):
    logger.debug(f"Updating license expiration: key={key}, new_expiration={new_expiration}")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE licenses SET expiration = ? WHERE key = ?", (new_expiration, key))
        changes = db.total_changes
        await db.commit()
    
    if changes:
        logger.info(f"License expiration updated successfully: {key}")
        return True
    else:
        logger.warning(f"License not found for update: {key}")
        return False

# ./qminer.py
# qminer.py
import os
import sys
import socket
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from termcolor import colored
from config import SECRET_KEY, ALLOWED_HOSTS, DEBUG
from database.db import init_db
from api.endpoints import router as api_router
import asyncio
import uvicorn
import signal
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    logger.info(colored("🕷️ qMiner web crawler initializing...", 'green'))
    await init_db()
    logger.info(colored("🕷️ qMiner web crawler initialized", 'green'))

@app.on_event("shutdown")
async def shutdown_event():
    logger.info(colored("🕷️ qMiner web crawler shutting down...", 'yellow'))
    # Add any cleanup tasks here

def signal_handler(sig, frame):
    logger.info(colored("\n🛑 Stopping qMiner...", 'red'))
    sys.exit(0)

def find_available_port(start_port=5000, max_attempts=100):
    """Recursively find an available port."""
    if max_attempts == 0:
        logger.error(colored("Exhausted all port options. Cannot start the server.", 'red'))
        sys.exit(1)
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', start_port))
        logger.info(colored(f"Found available port: {start_port}", 'green'))
        return start_port
    except OSError:
        logger.warning(colored(f"Port {start_port} is in use, trying next port...", 'yellow'))
        return find_available_port(start_port + 1, max_attempts - 1)

if __name__ == '__main__':
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    initial_port = int(os.getenv('PORT', 5000))
    port = find_available_port(initial_port)

    logger.info(colored(f"\n🚀 Starting qMiner on port {port}", 'green'))
    logger.info(colored(f" http://0.0.0.0:{port}\n", 'cyan'))

    uvicorn.run(
        "qminer:app",
        host="0.0.0.0",
        port=port,
        log_level="info" if DEBUG else "error",
        reload=DEBUG
    )

# ./crawler/__init__.py


# ./crawler/crawler.py
import logging
import json
from urllib.parse import urljoin, urlparse
from datetime import datetime
import asyncio
import re
from bs4 import BeautifulSoup
import aiohttp
import aiosqlite
from config import DB_NAME, MAX_URLS

logger = logging.getLogger(__name__)

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

    body_text = soup.body.get_text(separator=' ', strip=True) if soup.body else ''
    body_text = re.sub(r'\s+', ' ', body_text).strip()

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO crawls (url, depth, internal_links, external_links, title, body_text, crawled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (url, depth, json.dumps(internal_links), json.dumps(external_links),
              soup.title.string if soup.title else None, body_text, datetime.now().isoformat()))
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

# ./__init__.py


# ./utils/__init__.py


# ./utils/helpers.py


# ./api/__init__.py


# ./api/endpoints.py
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
    logger.info(f"Received crawl request: {request}")

    if not await is_valid_license(request.license_key):
        logger.warning(f"Invalid or expired license key: {request.license_key}")
        raise HTTPException(status_code=403, detail="Invalid or expired license key")

    # Start the crawl task
    task = asyncio.create_task(crawl(request.url, request.max_depth, request.max_urls))
    
    # Wait for the crawl to complete
    try:
        crawled_urls = await task
        logger.info(f"Crawl completed for {request.url}. Total URLs crawled: {crawled_urls}")
        return {"message": f"Crawl completed successfully. Total URLs crawled: {crawled_urls}"}
    except Exception as e:
        logger.error(f"Error during crawl: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during the crawl")

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


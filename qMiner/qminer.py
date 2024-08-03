# File: app.py
import os
import asyncio
import aiohttp
import aiosqlite
import json
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from asgiref.wsgi import WsgiToAsgi

load_dotenv()

app = Flask(__name__)

# Configuration
DB_NAME = os.getenv('DB_NAME', 'crawler.db')
MAX_DEPTH = int(os.getenv('MAX_DEPTH', 5))
MAX_URLS = int(os.getenv('MAX_URLS', 1000))
SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key_here')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

app.config['SECRET_KEY'] = SECRET_KEY

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import socket

def find_available_port(start_port=5000, max_port=5100):
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    raise IOError("No free ports found in range")

# Database setup
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
            crawled_at TIMESTAMP
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            expiration TIMESTAMP
        )
        """)
        await db.commit()

# Crawler logic
async def is_internal_link(base_url, link):
    return urlparse(link).netloc == urlparse(base_url).netloc or not urlparse(link).netloc

async def crawl_page(session, url, base_url, depth, max_depth):
    if depth > max_depth:
        return

    try:
        async with session.get(url) as response:
            if response.status != 200:
                logging.warning(f"Failed to fetch {url}: HTTP {response.status}")
                return

            content = await response.text()
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

            logging.info(f"Crawled: {url} (Depth: {depth})")
            logging.info(f"Found {len(internal_links)} internal and {len(external_links)} external links")

            return internal_links

    except Exception as e:
        logging.error(f"Error crawling {url}: {str(e)}")
        return []

async def crawl(base_url, max_depth, max_urls=MAX_URLS):
    async with aiohttp.ClientSession() as session:
        queue = [(base_url, 0)]
        visited = set()

        while queue and len(visited) < max_urls:
            url, depth = queue.pop(0)

            if url not in visited:
                visited.add(url)
                new_links = await crawl_page(session, url, base_url, depth, max_depth)

                if new_links:
                    for link in new_links:
                        if link not in visited:
                            queue.append((link, depth + 1))

# API routes
@app.route('/crawl', methods=['POST'])
async def start_crawl():
    license_key = request.json.get('license_key')
    if not await is_valid_license(license_key):
        return jsonify({"error": "Invalid or expired license key"}), 403

    base_url = request.json.get('url')
    max_depth = request.json.get('max_depth', MAX_DEPTH)
    max_urls = request.json.get('max_urls', MAX_URLS)

    asyncio.create_task(crawl(base_url, max_depth, max_urls))
    return jsonify({"message": "Crawl started successfully"}), 202

@app.route('/results', methods=['GET'])
async def get_results():
    license_key = request.args.get('license_key')
    if not await is_valid_license(license_key):
        return jsonify({"error": "Invalid or expired license key"}), 403

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    offset = (page - 1) * per_page

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM crawls") as cursor:
            total_results = (await cursor.fetchone())[0]

        async with db.execute("SELECT * FROM crawls LIMIT ? OFFSET ?", (per_page, offset)) as cursor:
            results = await cursor.fetchall()

    return jsonify({
        "results": results,
        "page": page,
        "per_page": per_page,
        "total_results": total_results
    }), 200

# License management
async def is_valid_license(key):
    logging.info(f"Checking license key: {key}")
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM licenses WHERE key = ?", (key,)) as cursor:
            license = await cursor.fetchone()
        if not license:
            logging.warning(f"License key not found: {key}")
            return False
        logging.info(f"Found license: {license}")
        if license[2] == 'subscription':
            is_valid = datetime.now() < datetime.fromisoformat(license[3])
            logging.info(f"Subscription license valid: {is_valid}")
            return is_valid
        logging.info("One-time license, always valid")
        return True

@app.route('/license', methods=['POST'])
async def create_license():
    key = request.json.get('key')
    license_type = request.json.get('type')
    expiration = None
    if license_type == 'subscription':
        expiration = (datetime.now() + timedelta(days=30)).isoformat()

    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("INSERT INTO licenses (key, type, expiration) VALUES (?, ?, ?)",
                             (key, license_type, expiration))
            await db.commit()
        logging.info(f"License created successfully: {key}")
        return jsonify({"message": "License created successfully"}), 201
    except aiosqlite.IntegrityError:
        logging.warning(f"Attempt to create duplicate license key: {key}")
        return jsonify({"error": "License key already exists"}), 400
    except Exception as e:
        logging.error(f"Error creating license: {str(e)}")
        return jsonify({"error": "An error occurred while creating the license"}), 500



asgi_app = WsgiToAsgi(app)

if __name__ == '__main__':
    debug = os.environ.get('DEBUG', 'False') == 'True'
    
    # Initialize the database
    asyncio.run(init_db())
    
    # In Docker, we should always use port 5000
    port = 5000
    print(f"Starting server on port {port}")
    
    # We don't need this line anymore:
    # app.run(host='0.0.0.0', port=port, debug=debug)
    
    # Instead, if you want to run the app directly (not through Docker):
    import uvicorn
    uvicorn.run(asgi_app, host="0.0.0.0", port=port, debug=debug)
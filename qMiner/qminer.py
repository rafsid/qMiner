# File: qminer.py
from flask import Flask, request, jsonify
import sqlite3 
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database setup
DB_NAME = "crawler.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
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
        conn.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            expiration TIMESTAMP
        )
        """)

init_db()

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

            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("""
                INSERT INTO crawls (url, depth, internal_links, external_links, title, crawled_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (url, depth, json.dumps(internal_links), json.dumps(external_links),
                      soup.title.string if soup.title else None, datetime.now()))

            logging.info(f"Crawled: {url} (Depth: {depth})")
            logging.info(f"Found {len(internal_links)} internal and {len(external_links)} external links")

            return internal_links

    except Exception as e:
        logging.error(f"Error crawling {url}: {str(e)}")
        return []

async def crawl(base_url, max_depth, max_urls=1000):
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
def start_crawl():
    license_key = request.json.get('license_key')
    if not is_valid_license(license_key):
        return jsonify({"error": "Invalid or expired license key"}), 403

    base_url = request.json.get('url')
    max_depth = request.json.get('max_depth', 5)
    max_urls = request.json.get('max_urls', 1000)

    asyncio.run(crawl(base_url, max_depth, max_urls))
    return jsonify({"message": "Crawl started successfully"}), 202

@app.route('/results', methods=['GET'])
def get_results():
    license_key = request.args.get('license_key')
    if not is_valid_license(license_key):
        return jsonify({"error": "Invalid or expired license key"}), 403

    with sqlite3.connect(DB_NAME) as conn:
        results = conn.execute("SELECT * FROM crawls").fetchall()
    return jsonify(results), 200

# License management
def is_valid_license(key):
    logging.info(f"Checking license key: {key}")
    with sqlite3.connect(DB_NAME) as conn:
        license = conn.execute("SELECT * FROM licenses WHERE key = ?", (key,)).fetchone()
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
def create_license():
    key = request.json.get('key')
    license_type = request.json.get('type')
    expiration = None
    if license_type == 'subscription':
        expiration = (datetime.now() + timedelta(days=30)).isoformat()

    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("INSERT INTO licenses (key, type, expiration) VALUES (?, ?, ?)",
                         (key, license_type, expiration))
        logging.info(f"License created successfully: {key}")
        return jsonify({"message": "License created successfully"}), 201
    except sqlite3.IntegrityError:
        logging.warning(f"Attempt to create duplicate license key: {key}")
        return jsonify({"error": "License key already exists"}), 400
    except Exception as e:
        logging.error(f"Error creating license: {str(e)}")
        return jsonify({"error": "An error occurred while creating the license"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
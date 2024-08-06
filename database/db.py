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
            SELECT id, url, depth, title, crawled_at 
            FROM crawls 
            ORDER BY crawled_at DESC 
            LIMIT ? OFFSET ?
        """
        async with db.execute(query, (per_page, offset)) as cursor:
            results = [dict(row) for row in await cursor.fetchall()]
    
    return results, total_results

async def insert_crawl_result(url, depth, internal_links, external_links, title, crawled_at):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO crawls (url, depth, internal_links, external_links, title, crawled_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (url, depth, internal_links, external_links, title, crawled_at))
        await db.commit()
    logger.info(f"Inserted crawl result for URL: {url}")
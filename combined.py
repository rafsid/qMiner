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
DATABASE_URL = config['DATABASE_URL']# qminer.py
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
    )# run.py
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
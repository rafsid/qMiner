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
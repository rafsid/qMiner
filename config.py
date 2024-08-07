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
API_KEY = "jina_9abd8639b5e34626b175ac3de9ec30bcSOTpRFqDDtQ0ekJ45auo6MqRzo4M"
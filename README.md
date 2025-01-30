# Async Web Crawler with Licensing System

## Overview
A high-performance asynchronous web crawler built with Python, featuring a licensing system, Playwright-based rendering, and a RESTful API interface. The crawler efficiently handles JavaScript-rendered content and manages both internal and external links while respecting crawl depth limits.

## Features
- Asynchronous crawling with aiohttp and Playwright
- Built-in licensing system (subscription and one-time)
- SQLite database for storing crawl results
- RESTful API endpoints for control and monitoring
- Docker support
- Configurable crawl depth and URL limits
- JavaScript rendering support
- Detailed logging system

## Requirements
- Python 3.8+
- Playwright
- Flask
- aiohttp
- aiosqlite
- Beautiful Soup 4
- uvicorn
- Other dependencies in requirements.txt

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/async-web-crawler.git
cd async-web-crawler
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install
```

5. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your settings:
```
DB_NAME=crawler.db
MAX_DEPTH=5
MAX_URLS=1000
SECRET_KEY=your_secret_key_here
ALLOWED_HOSTS=localhost,127.0.0.1
DEBUG=False
```

## Usage

### Running the Server

```bash
python app.py
```

Or with Docker:
```bash
docker build -t web-crawler .
docker run -p 5000:5000 web-crawler
```

### API Endpoints

1. Start a Crawl
```bash
POST /crawl
{
    "url": "https://example.com",
    "max_depth": 3,
    "max_urls": 100,
    "license_key": "your_license_key"
}
```

2. Get Results
```bash
GET /results?license_key=your_license_key&page=1&per_page=20
```

3. Create License
```bash
POST /license
{
    "key": "license_key",
    "type": "subscription"  # or "one-time"
}
```

## Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| DB_NAME | SQLite database name | crawler.db |
| MAX_DEPTH | Maximum crawl depth | 5 |
| MAX_URLS | Maximum URLs to crawl | 1000 |
| SECRET_KEY | Flask secret key | your_secret_key_here |
| ALLOWED_HOSTS | Allowed host list | localhost,127.0.0.1 |
| DEBUG | Debug mode | False |

## Database Schema

### Crawls Table
```sql
CREATE TABLE crawls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    depth INTEGER NOT NULL,
    internal_links TEXT,
    external_links TEXT,
    title TEXT,
    crawled_at TIMESTAMP
)
```

### Licenses Table
```sql
CREATE TABLE licenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,
    expiration TIMESTAMP
)
```

## License Management

Two types of licenses are supported:
- One-time: Never expires
- Subscription: 30-day validity

## Error Handling
- Comprehensive error logging
- Graceful handling of network issues
- Timeout management for slow responses
- Invalid license handling

## Security Features
- License key validation
- Configurable allowed hosts
- Rate limiting (configurable)
- Input validation

## Contributing
Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- Playwright team for the browser automation
- Flask team for the web framework
- Beautiful Soup team for HTML parsing

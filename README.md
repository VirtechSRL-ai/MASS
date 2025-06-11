# Multi-Source Scraper API

A backend service that provides multi-source scraping capabilities with AI integration. The service uses Playwright and Firecrawl for scraping, with configurable logging and containerized deployment.

## Features

- Multi-source scraping (Google, Bing, and custom domains)
- Playwright-based web scraping with pagination support
- Firecrawl integration for enhanced content extraction
- Configurable logging system
- Docker containerization
- FastAPI-based REST API
- Concurrent scraping execution
- Deduplication of results
- Structured JSON output

## Prerequisites

- Python 3.11+
- Docker (optional)
- Firecrawl API key
- OpenAI API key (for AI integration)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create a virtual environment (optional):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
export FIRECRAWL_API_KEY=your_firecrawl_api_key
export OPENAI_API_KEY=your_openai_api_key
```

## Running the Service

### Local Development

```bash
uvicorn app.main:app --reload
```

### Using Docker

1. Build the Docker image:
```bash
docker build -t multi-source-scraper .
```

2. Run the container:
```bash
docker run -p 8000:8000 \
  -e FIRECRAWL_API_KEY=your_firecrawl_api_key \
  -e OPENAI_API_KEY=your_openai_api_key \
  multi-source-scraper
```

## API Usage

### Scrape Endpoint

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": "example search",
    "target_domain": "example.com",
    "max_pages": 3
  }'
```

Response format:
```json
{
  "results": [
    {
      "title": "Example Title",
      "link": "https://example.com/page",
      "thumbnail": "https://example.com/image.jpg",
      "source": "google",
      "content": "Optional content from Firecrawl"
    }
  ],
  "metadata": {
    "total_results": 1,
    "keywords": "example search",
    "target_domain": "example.com"
  }
}
```

### Health Check

```bash
curl "http://localhost:8000/health"
```

## Configuration

The service can be configured through environment variables and the `config.py` file:

- `FIRECRAWL_API_KEY`: Your Firecrawl API key
- `OPENAI_API_KEY`: Your OpenAI API key
- Logging configuration in `config.py`
- Scraping sources configuration in `config.py`

## Logging

Logs are written to:
- Console (INFO level and above)
- `logs/error.log` (ERROR level and above, with rotation)

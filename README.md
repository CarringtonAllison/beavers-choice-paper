# Beaver's Choice Paper Company — Multi-Agent System

A multi-agent AI system that automates inventory management, price quoting, and order fulfillment for a paper supply company. Built with [smolagents](https://github.com/huggingface/smolagents) and SQLite.

## Overview

The system processes customer paper supply requests end-to-end through a pipeline of four coordinated agents:

1. **Orchestrator** — receives requests and coordinates the other agents
2. **Inventory Agent** — checks stock levels and delivery estimates
3. **Quoting Agent** — generates prices using historical data and bulk discounts
4. **Sales Agent** — records completed transactions and confirms cash balance

## Project Structure

```
├── project_starter.py       # Main implementation file
├── quote_requests.csv       # Historical quote request data (seeds the database)
├── quote_requests_sample.csv # Test scenarios run against the agent system
├── quotes.csv               # Historical quote responses (seeds the database)
├── requirements.txt         # Python dependencies
└── .env                     # API key (not committed)
```

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
pip install smolagents
```

**2. Create a `.env` file** in the project root:
```
UDACITY_OPENAI_API_KEY=your_api_key_here
```

**3. Run the system**
```bash
python project_starter.py
```

This will process all requests in `quote_requests_sample.csv` and write results to `test_results.csv`.

## Bulk Discount Tiers

| Order Total | Discount |
|---|---|
| Under $50 | 0% |
| $50 – $199 | 5% |
| $200 – $999 | 10% |
| $1,000+ | 15% |

## API

This project uses an OpenAI-compatible API endpoint with the `gpt-4o-mini` model. The base URL is configured in `project_starter.py` and the key is loaded from `.env`.

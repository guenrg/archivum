# Archivum

Tools and site to assist in moving auction catalogs to cloud storage.

## Repository Structure

```
archivum/
├── shared/          Shared Python package (core logic, DB, DTOs)
├── functions/       Azure Functions app (PDF parsing, enrichment, etc.)
├── web/             FastAPI web app (HTML/CSS/Bootstrap + HTMX)
├── scripts/         Local dev utilities (batch parse, etc.)
└── .github/         CI/CD workflows
```

## Getting Started

### Prerequisites
- Python 3.12+
- Azure Functions Core Tools (for local function development)

### Setup

```bash
# Create and activate a virtual environment at the repo root
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# Install the shared package in editable mode
pip install -e ./shared

# Install function app dependencies
pip install -r functions/requirements.txt

# Install web app dependencies
pip install -r web/requirements.txt
```

### Running Locally

**Azure Functions:**
```bash
cd functions
func start
```

**Web App:**
```bash
cd web
fastapi dev main.py
```

**Batch Parse Script:**
```bash
cd scripts
python parse.py
```


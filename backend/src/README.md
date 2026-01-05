# Speaking Test System - Backend

## Quick Start

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn src.infrastructure.main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
src/
├── domain/           # Core business entities & interfaces
├── use_cases/        # Application logic
├── adapters/         # External implementations
│   ├── repositories/ # Database access
│   ├── gateways/     # External APIs (Xunfei, Qwen)
│   └── controllers/  # FastAPI routers
└── infrastructure/   # App config & framework setup
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

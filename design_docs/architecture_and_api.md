# Architecture & API Design (V1.0 Production)

## 1. System Architecture (Clean Architecture)

We will adopt a **Clean Architecture** (also known as Hexagonal Architecture) to decouple business logic from external dependencies (Xunfei, Qwen, Database).

### 1.1 Directory Structure

We will strictly follow the **Clean Architecture** pattern defined in the workflow:

```
src/
├── domain/                 # [Inner Layer] Entities & Business Rules (Pure Python)
│   ├── entities/           # Core Business Objects
│   │   ├── student.py
│   │   ├── test.py
│   │   └── score.py
│   └── ports/              # [Ports] Abstract Interfaces (Repositories/Gateways)
│       ├── repository.py   # IStudentRepository, ITestRepository
│       └── ai_gateway.py   # IXunfeiGateway, IQwenGateway
│
├── use_cases/              # [Application Layer] Orchestration Logic
│   ├── submit_test.py      # SubmitTestUseCase
│   ├── get_report.py       # GetReportUseCase
│   └── auth_student.py     # StudentLoginUseCase
│
├── adapters/               # [Interface Adapters] Implementations
│   ├── repositories/       # Database Implementations (SQLAlchemy)
│   │   ├── mysql_student_repo.py
│   │   └── mysql_test_repo.py
│   ├── gateways/           # External Service Implementations
│   │   ├── xunfei_client.py
│   │   ├── qwen_client.py
│   │   └── oss_client.py
│   └── controllers/        # Web Controllers (FastAPI Routers)
│       ├── auth_controller.py
│       ├── test_controller.py
│       └── report_controller.py
│
└── infrastructure/         # [Frameworks & Drivers] Configuration
    ├── database.py         # DB Connection & Session
    ├── config.py           # Environment Variables
    ├── logging.py          # Logger Config
    └── main.py             # App Entry Point
```

---

## 2. API Design (RESTful)

We will strictly follow the **RESTful Design Principles** defined in the workflow.

### 2.1 Standard Response Models

**Pagination (Pattern 2)**
All list endpoints must support pagination.
```python
class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int
    pages: int
```

**Error Handling (Pattern 3)**
All errors must return a consistent structure.
```python
class ErrorResponse(BaseModel):
    error: str      # Error Code (e.g., "ResourceNotFound")
    message: str    # Human readable message
    details: Optional[dict] = None
    timestamp: str
    path: str
```

### 2.2 Endpoints (Resource-Oriented)

**Auth & Entry**
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/tokens` | Create session token (Login) |

**Students**
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/students` | List students (Teacher only, Paginated) |
| `POST` | `/api/v1/students/{id}/entry` | Exchange Entry Token for Session |

**Tests (Assessments)**
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/tests` | Create a new test |
| `GET` | `/api/v1/tests/{id}` | Get test details/result |
| `WS` | `/api/v1/ws/tests/{id}/part1` | **WebSocket**: Stream Audio for Part 1 |
| `POST` | `/api/v1/tests/{id}/part2` | Submit Part 2 Audio (Async) |

**Reports**
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/reports/share-tokens` | Create share token for parent |
| `GET` | `/api/v1/reports/shared/{token}` | View shared report (Public) |

---

## 3. Key Design Decisions

1.  **Async First**: Use `FastAPI` + `asyncio` to handle high-concurrency WebSocket connections (Part 1) and async HTTP requests (Qwen).
2.  **Queue-Based**: Part 2 submission pushes to a Queue; a separate Worker process consumes tasks to respect the **60 RPM** rate limit.
3.  **Dependency Injection**: Use FastAPI's DI system to inject `DBSession`, `XunfeiClient`, etc., making testing easier.

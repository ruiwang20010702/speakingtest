# Architecture & API Design (V1.0 Production)

## 1. System Architecture (Clean Architecture)

We will adopt a **Clean Architecture** (also known as Hexagonal Architecture) to decouple business logic from external dependencies (Qwen, Database, OSS).

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
│       └── ai_gateway.py   # IQwenGateway
│
├── use_cases/              # [Application Layer] Orchestration Logic
│   ├── evaluate_part1.py   # SubmitPart1UseCase, ProcessPart1TaskUseCase
│   ├── evaluate_part2.py   # SubmitPart2UseCase, ProcessPart2TaskUseCase
│   ├── parent_report.py    # ParentReportService
│   └── auth_student.py     # StudentLoginUseCase
│
├── adapters/               # [Interface Adapters] Implementations
│   ├── repositories/       # Database Implementations (SQLAlchemy)
│   │   ├── models.py       # SQLAlchemy Models
│   ├── gateways/           # External Service Implementations
│   │   ├── qwen_client.py  # Qwen Omni API Client
│   │   ├── oss_client.py   # Aliyun OSS Client
│   │   └── email_service.py
│   └── controllers/        # Web Controllers (FastAPI Routers)
│       ├── auth_controller.py
│       ├── test_controller.py
│       └── report_controller.py
│
└── infrastructure/         # [Frameworks & Drivers] Configuration
    ├── database.py         # DB Connection & Session
    ├── queue_service.py    # RabbitMQ Producer/Consumer
    ├── config.py           # Environment Variables
    ├── logging.py          # Logger Config
    └── main.py             # App Entry Point
```

---

## 2. API Design (RESTful)

We will strictly follow the **RESTful Design Principles**.

### 2.1 Standard Response Models

**Standard Error Handling**
All errors must return a consistent structure.
```python
class ErrorResponse(BaseModel):
    error: str      # Error Code (e.g., "ResourceNotFound")
    message: str    # Human readable message
    details: Optional[dict] = None
```

### 2.2 Endpoints (Resource-Oriented)

**Auth & Entry**
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/tokens` | Create session token (Login) |

**Students**
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/students` | List students (Paginated) |
| `POST` | `/api/v1/students/{id}/entry` | Exchange Entry Token for Session |

**Tests (Assessments)**
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/tests` | Create a new test |
| `GET` | `/api/v1/tests/{id}` | Get test details/result (status polling) |
| `POST` | `/api/v1/tests/{id}/part1` | **Async**: Upload & Submit Part 1 Audio |
| `POST` | `/api/v1/tests/{id}/part2` | **Async**: Upload & Submit Part 2 Audio |

**Reports & Interpretation**
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/tests/{id}/report` | Get full report details (Part 1 + Part 2 + Analysis) |
| `POST` | `/api/v1/reports/share-tokens` | Create share token for parent |
| `GET` | `/api/v1/reports/shared/{token}` | View shared report (Public) |
| `GET` | `/api/v1/tests/{id}/interpretation` | Get AI-generated speech script for teachers |

**Admin & Management**
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/admin/stats/overview` | System overview stats (Students, Tests, Shares) |
| `GET` | `/api/v1/admin/stats/funnel` | Conversion funnel data |
| `GET` | `/api/v1/admin/stats/cost` | Real-time API cost tracking (RMB) |
| `GET` | `/api/v1/admin/teachers` | List teachers with summary stats |
| `GET` | `/api/v1/admin/failed-tasks` | List failed/stuck tasks |
| `POST` | `/api/v1/admin/failed-tasks/{id}/retry` | Retry a failed task |
| `GET` | `/api/v1/admin/audit-logs` | Query system audit logs |

---

## 3. Key Design Decisions

1.  **Async & Queue-Based Architecture**:
    *   **Part 1, Part 2, and Interpretation** evaluations are handled asynchronously.
    *   API endpoints upload audio to OSS and push tasks to **RabbitMQ**.
    *   Dedicated **Worker Processes** consume tasks:
        *   `part1_worker.py`: Handles word/sentence reading evaluation.
        *   `part2_worker.py`: Handles 12-question dialogue evaluation and summary analysis.
        *   `interpretation_worker.py`: Handles AI speech script generation for teachers.
    
2.  **AI Provider**:
    *   **Qwen-Omni (Flash)**: Used for both Part 1 (Reading) and Part 2 (Q&A) audio evaluation due to its multimodal capabilities and cost-effectiveness.
    *   **Qwen-Plus**: Used for generating structured summary analysis and report interpretations (speech scripts).

3.  **Cost Tracking**:
    *   The system records the exact token usage for every AI call.
    *   Costs are calculated in real-time based on current model pricing (Input Text, Input Audio, Output Text).
    *   Total cost is aggregated at the `Test` level and can be queried via Admin APIs.

4.  **Dependency Injection**: 
    *   Use FastAPI's DI system to inject `DBSession`, `OSSClient`, and `QwenGateway`, ensuring testability and modularity.

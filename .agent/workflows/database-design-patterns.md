---
description: Best practices for database schema design, naming conventions, indexing, and SQL standards.
---

# Database Design Patterns

Establish robust database standards to ensure data integrity, performance, and maintainability.

## When to Use This Skill

- Designing new database schemas
- Reviewing SQL migration scripts
- Optimizing query performance
- Establishing team-wide SQL standards
- Refactoring legacy database structures

## Core Principles

### 1. Naming Conventions (Snake Case)

- **Tables**: Plural nouns (e.g., `users`, `student_profiles`, `test_results`).
- **Columns**: Singular, descriptive (e.g., `first_name`, `is_active`, `created_at`).
- **Primary Keys**: `id` (simple) or `user_id` (explicit).
- **Foreign Keys**: `[table_singular]_id` (e.g., `student_id`, `teacher_id`).
- **Indexes**: `idx_[table]_[column]` or `uk_[table]_[column]` (unique).

### 2. Standard Columns (The "Golden Four")

Every table MUST include these audit columns:

```sql
-- PostgreSQL Syntax
id          BIGSERIAL PRIMARY KEY,
created_at  TIMESTAMPTZ DEFAULT NOW(),
updated_at  TIMESTAMPTZ DEFAULT NOW(),
is_deleted  BOOLEAN DEFAULT FALSE -- Soft delete (Optional but recommended)
```

> **Note**: PostgreSQL does not support `ON UPDATE CURRENT_TIMESTAMP`. Use a trigger (see Pattern 5).

### 3. Data Types Best Practices (PostgreSQL)

- **IDs**: Use `BIGSERIAL` (auto-increment) or `UUID` (`gen_random_uuid()`).
- **Booleans**: Use `BOOLEAN` (TRUE/FALSE).
- **Strings**: Use `VARCHAR(N)` or `TEXT` (no performance difference in PG).
- **Money**: Use `NUMERIC(10, 2)` or store as cents (`BIGINT`). NEVER use `REAL/DOUBLE PRECISION`.
- **JSON**: Use `JSONB` (binary, indexable) for structured data.
- **Timestamps**: Use `TIMESTAMPTZ` (with timezone) for all time fields.

### 4. Critical Configuration Standards

- **Character Set**: PostgreSQL uses UTF-8 by default. Ensure database is created with `ENCODING 'UTF8'`.
- **Timezone**: Store all times in **UTC** (`TIMESTAMPTZ`). Set `timezone = 'UTC'` in postgresql.conf.
- **Foreign Keys**:
  - Default: `ON DELETE RESTRICT` (Prevent deleting parent if children exist).
  - Exception: `ON DELETE CASCADE` (Only for strict composition).

## Schema Design Patterns (PostgreSQL)

### Pattern 1: User & Profile Separation

```sql
-- Auth & Core Identity
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255),
    role            VARCHAR(20) NOT NULL, -- 'student', 'teacher'
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Extended Profile Data
CREATE TABLE student_profiles (
    user_id         BIGINT PRIMARY KEY REFERENCES users(id),
    full_name       VARCHAR(100),
    grade_level     INT,
    avatar_url      VARCHAR(500)
);
```

### Pattern 2: Status & State Machines

Use `VARCHAR` or PostgreSQL `ENUM` for status.

```sql
CREATE TYPE test_status AS ENUM ('pending', 'processing', 'completed', 'failed');

CREATE TABLE tests (
    id      BIGSERIAL PRIMARY KEY,
    status  test_status NOT NULL DEFAULT 'pending'
);
CREATE INDEX idx_tests_status ON tests(status);
```

### Pattern 3: High-Performance Indexing

Same principles apply. Use `CREATE INDEX` statements separately.

### Pattern 4: Audit Logging

```sql
CREATE TABLE audit_logs (
    id          BIGSERIAL PRIMARY KEY,
    table_name  VARCHAR(50),
    record_id   BIGINT,
    action      VARCHAR(20), -- 'INSERT', 'UPDATE', 'DELETE'
    old_value   JSONB,
    new_value   JSONB,
    changed_by  BIGINT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### Pattern 5: Auto-Update Timestamps (Trigger)

PostgreSQL requires a trigger to auto-update `updated_at`:

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to a table
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

## Migration Workflow (Alembic/Flyway)

1.  **Never modify existing migrations**: Always create a NEW migration file.
2.  **Down revisions**: Always implement the `down()` (rollback) method.
3.  **Transactional DDL**: Ensure migrations run inside a transaction (where supported).

## Checklist for Review

- [ ] Are table names plural and column names snake_case?
- [ ] Does every table have `created_at` and `updated_at`?
- [ ] Are Foreign Keys properly defined with constraints?
- [ ] Are suitable indexes added for common query patterns?
- [ ] Is `DECIMAL` used for currency?
- [ ] Are `NOT NULL` constraints applied where appropriate?

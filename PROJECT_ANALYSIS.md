# DB2API-Exposure: Project Analysis & Manifesto

## 1. Executive Summary

**Project Name:** DB2API-Exposure
**Goal:** Provide a self-hosted platform that enables users to expose local database data through dynamically generated RESTful API endpoints, using a wizard-driven UI for configuration.

**Core Value Proposition:** Organizations with Oracle (and later other) databases need a lightweight, self-hosted tool to expose specific query results as secure REST APIs — without requiring developers to hand-code each endpoint. DB2API-Exposure bridges the gap between database-stored data and modern API consumers.

---

## 2. Open-Source Alternatives Assessment

Before building from scratch, the following existing open-source and free tools were evaluated against the project's MVP requirements.

### 2.1 Requirements Checklist (MVP)

| # | Requirement | Weight |
|---|-------------|--------|
| R1 | Oracle Database connectivity | Must-have |
| R2 | Custom SQL queries as API endpoints (not just table CRUD) | Must-have |
| R3 | Dynamic parameters in SQL queries | Must-have |
| R4 | Web UI / wizard for API creation | Must-have |
| R5 | Authentication (Bearer token, Basic Auth) | Must-have |
| R6 | Task scheduling for periodic data refresh | Must-have |
| R7 | JSON output from query results | Must-have |
| R8 | Configurable API URL and port | Must-have |
| R9 | Store generated JSON to file/database | Must-have |
| R10 | Python backend (FastAPI) | Preferred |
| R11 | Next.js frontend | Preferred |
| R12 | Self-hosted / fully open-source | Must-have |

### 2.2 Evaluated Tools

#### A. Oracle REST Data Services (ORDS)
- **URL:** https://www.oracle.com/database/technologies/appdev/rest.html
- **License:** Free (proprietary, not open-source)
- **Oracle Support:** Native — built by Oracle
- **Custom SQL Endpoints:** Yes — RESTful service modules with SQL/PL/SQL
- **Web UI:** Oracle APEX integration (separate product)
- **Auth:** OAuth2, Basic Auth, custom privilege/role system
- **Scheduling:** No native scheduling — requires DBMS_SCHEDULER or external cron
- **JSON Caching/Storage:** No — live queries only
- **Tech Stack:** Java

| Requirement | Met? | Notes |
|-------------|------|-------|
| R1 Oracle | YES | Native |
| R2 Custom SQL | YES | Full SQL/PL/SQL support |
| R3 Dynamic params | YES | Bind variables in templates |
| R4 Web UI wizard | PARTIAL | Requires Oracle APEX or SQL Developer |
| R5 Auth | YES | OAuth2, Basic Auth, role-based |
| R6 Scheduling | NO | External only (DBMS_SCHEDULER) |
| R7 JSON output | YES | Native JSON responses |
| R8 Configurable URL/port | YES | Standalone deployment |
| R9 Store JSON | NO | No caching/storage mechanism |
| R10 Python/FastAPI | NO | Java-based |
| R11 Next.js frontend | NO | No standalone frontend |
| R12 Open-source | NO | Free but proprietary |

**Verdict:** Closest Oracle-native solution but not open-source. No scheduling, no JSON caching, no wizard UI, wrong tech stack.

---

#### B. DreamFactory
- **URL:** https://github.com/dreamfactorysoftware/dreamfactory
- **License:** Apache 2.0 (community edition); Commercial for Oracle
- **Oracle Support:** Commercial edition ONLY
- **Custom SQL Endpoints:** Yes (stored procedures, custom SQL)
- **Web UI:** Yes — full admin panel
- **Auth:** OAuth 2.0, SAML, LDAP, API keys (enterprise features)
- **Scheduling:** No native scheduling
- **Tech Stack:** PHP (Laravel)

| Requirement | Met? | Notes |
|-------------|------|-------|
| R1 Oracle | NO (free) | Oracle requires paid license |
| R2 Custom SQL | YES | Via stored procedures/scripts |
| R3 Dynamic params | YES | URL parameters mapped to queries |
| R4 Web UI wizard | YES | Full admin panel |
| R5 Auth | YES | Multiple methods |
| R6 Scheduling | NO | No native scheduling |
| R7 JSON output | YES | Native |
| R8 Configurable URL/port | YES | Docker/standalone |
| R9 Store JSON | NO | No caching layer |
| R10 Python/FastAPI | NO | PHP-based |
| R11 Next.js frontend | NO | Built-in Angular admin |
| R12 Open-source | PARTIAL | Oracle connector is commercial |

**Verdict:** Oracle support is paywalled. Wrong tech stack. No scheduling.

---

#### C. Directus
- **URL:** https://github.com/directus/directus
- **License:** BSL 1.1 (free for <$5M revenue organizations)
- **Oracle Support:** Listed as supported (via Knex.js)
- **Custom SQL Endpoints:** Limited — primarily CRUD on existing tables/views
- **Web UI:** Yes — excellent admin panel
- **Auth:** SSO, OAuth2, OpenID, custom
- **Scheduling:** Flows (automation) with scheduled triggers
- **Tech Stack:** TypeScript/Node.js

| Requirement | Met? | Notes |
|-------------|------|-------|
| R1 Oracle | PARTIAL | Listed but community reports issues |
| R2 Custom SQL | LIMITED | Primarily table/view CRUD; custom endpoints require extensions |
| R3 Dynamic params | LIMITED | Filter parameters, not arbitrary SQL params |
| R4 Web UI wizard | YES | Excellent UI |
| R5 Auth | YES | Multiple providers |
| R6 Scheduling | PARTIAL | Flows automation, not query-to-cache scheduling |
| R7 JSON output | YES | Native |
| R8 Configurable URL/port | YES | Environment config |
| R9 Store JSON | NO | No query-result caching |
| R10 Python/FastAPI | NO | Node.js/TypeScript |
| R11 Next.js frontend | NO | Built-in Vue.js admin |
| R12 Open-source | PARTIAL | BSL 1.1 with revenue cap |

**Verdict:** Designed for headless CMS, not raw SQL-to-API. Oracle support is unstable. Not truly open-source (BSL license). Cannot expose arbitrary SQL queries as endpoints without heavy customization.

---

#### D. Fusio
- **URL:** https://github.com/apioo/fusio
- **License:** MIT (with AGPLv3 for some components)
- **Oracle Support:** Yes (via dedicated Docker image)
- **Custom SQL Endpoints:** Yes — actions can execute arbitrary SQL
- **Web UI:** Yes — admin panel for routes, actions, connections
- **Auth:** OAuth2, API keys
- **Scheduling:** Cronjob integration
- **Tech Stack:** PHP (with Python worker support)

| Requirement | Met? | Notes |
|-------------|------|-------|
| R1 Oracle | YES | Via dedicated Docker image |
| R2 Custom SQL | YES | Actions with SQL queries |
| R3 Dynamic params | YES | Route parameters passed to actions |
| R4 Web UI wizard | YES | Admin panel |
| R5 Auth | YES | OAuth2, API keys |
| R6 Scheduling | PARTIAL | Cronjob support, not built-in scheduler UI |
| R7 JSON output | YES | Native |
| R8 Configurable URL/port | YES | Docker/config |
| R9 Store JSON | NO | No query-result caching/storage |
| R10 Python/FastAPI | NO | PHP core (Python via worker) |
| R11 Next.js frontend | NO | Built-in React admin |
| R12 Open-source | YES | MIT |

**Verdict:** Closest match feature-wise. However: PHP-based (not Python/FastAPI), no built-in JSON caching/storage from query results, Python is only available via a worker system (not native). Would require significant customization to meet all MVP requirements.

---

#### E. Sandman2
- **URL:** https://github.com/jeffknupp/sandman2
- **License:** Apache 2.0
- **Oracle Support:** Yes (via SQLAlchemy)
- **Custom SQL Endpoints:** No — auto-generates CRUD from tables only
- **Web UI:** Basic admin page
- **Auth:** No built-in authentication
- **Scheduling:** None
- **Tech Stack:** Python (Flask)

| Requirement | Met? | Notes |
|-------------|------|-------|
| R1 Oracle | YES | Via SQLAlchemy |
| R2 Custom SQL | NO | Table CRUD only |
| R3 Dynamic params | NO | No custom queries |
| R4 Web UI wizard | MINIMAL | Basic admin page |
| R5 Auth | NO | No authentication |
| R6 Scheduling | NO | None |
| R7 JSON output | YES | Native |
| R8 Configurable URL/port | YES | Flask config |
| R9 Store JSON | NO | Live queries only |
| R10 Python/FastAPI | PARTIAL | Python but Flask, not FastAPI |
| R11 Next.js frontend | NO | None |
| R12 Open-source | YES | Apache 2.0 |

**Verdict:** Too basic. No custom SQL, no auth, no scheduling. Dead project (last significant update years ago).

---

#### F. Datasette
- **URL:** https://datasette.io/
- **License:** Apache 2.0
- **Oracle Support:** No — SQLite only
- **Tech Stack:** Python

**Verdict:** Eliminated — SQLite only, no Oracle support.

---

#### G. PostgREST / Supabase / Hasura
- **URLs:** https://postgrest.org / https://supabase.com / https://hasura.io
- **Oracle Support:** None — PostgreSQL only (Hasura adds SQL Server/BigQuery)

**Verdict:** Eliminated — no Oracle support.

---

#### H. DB2Rest
- **URL:** https://db2rest.com/ / https://github.com/kdhrubo/db2rest
- **License:** Apache 2.0
- **Oracle Support:** Yes
- **Custom SQL Endpoints:** Limited — primarily CRUD
- **Web UI:** No web UI
- **Tech Stack:** Java (Spring Boot)

**Verdict:** Java-based, no web UI, limited custom SQL support, no scheduling.

---

#### I. ZenQuery
- **URL:** https://github.com/BjoernKW/ZenQuery
- **Oracle Support:** Yes
- **Custom SQL Endpoints:** Yes — read-only queries
- **Web UI:** Yes — query editor
- **Tech Stack:** Java

**Verdict:** Read-only (matches MVP GET-only requirement), but Java-based, appears to be a smaller/less maintained project.

---

### 2.3 Alternatives Comparison Matrix

| Tool | Oracle | Custom SQL | Web UI | Auth | Scheduling | JSON Cache | Python | Open-Source | Score /12 |
|------|:------:|:----------:|:------:|:----:|:----------:|:----------:|:------:|:-----------:|:---------:|
| ORDS | YES | YES | PARTIAL | YES | NO | NO | NO | NO | 5 |
| DreamFactory | NO* | YES | YES | YES | NO | NO | NO | PARTIAL | 4 |
| Directus | PARTIAL | LIMITED | YES | YES | PARTIAL | NO | NO | PARTIAL | 5 |
| **Fusio** | **YES** | **YES** | **YES** | **YES** | **PARTIAL** | **NO** | **NO** | **YES** | **7** |
| Sandman2 | YES | NO | MINIMAL | NO | NO | NO | PARTIAL | YES | 3 |
| Datasette | NO | YES | YES | PARTIAL | NO | NO | YES | YES | 4 |
| DB2Rest | YES | LIMITED | NO | YES | NO | NO | NO | YES | 4 |
| ZenQuery | YES | YES | YES | LIMITED | NO | NO | NO | YES | 5 |

*\*DreamFactory Oracle requires paid license*

### 2.4 Gap Analysis Conclusion

**No existing open-source tool fully satisfies the MVP requirements.** The key gaps across all evaluated tools:

1. **No tool combines Oracle + Custom SQL + Scheduling + JSON caching** — this is the project's unique value proposition
2. **No Python/FastAPI-based solution** supports Oracle with a wizard-driven UI
3. **Scheduling with data caching** (run query on schedule, store results, serve from cache) is not offered by any tool — they all serve live queries
4. **The wizard-based API creation flow** (connection → SQL → auth → endpoint → schedule) is unique to this project

**Fusio** comes closest (7/12) but fails on:
- Python/FastAPI tech stack (PHP core)
- No JSON result caching/storage
- No Next.js frontend
- Scheduling is basic cronjob, not the envisioned create-and-manage scheduler

**Recommendation: BUILD — proceed with custom development.** The combination of requirements is sufficiently unique that no existing tool can be adopted as-is. However, the architecture should draw inspiration from Fusio's action/connection model and ORDS's SQL template approach.

---

## 3. Project Manifesto

### 3.1 Vision

DB2API-Exposure is a self-hosted, open-source platform that democratizes database data access by enabling non-developers to create secure REST API endpoints from SQL queries through an intuitive wizard interface — without writing application code.

### 3.2 Core Principles

1. **Wizard-Driven Simplicity** — Creating an API endpoint should be a guided, step-by-step process accessible to database analysts and administrators, not just developers.
2. **Security by Default** — Every endpoint requires authentication. No anonymous access. All inputs are parameterized to prevent SQL injection. All actions are logged.
3. **Flexible Data Freshness** — Users choose between live database queries or scheduled data snapshots, balancing performance with data currency.
4. **Oracle-First, Database-Agnostic Architecture** — MVP targets Oracle, but the architecture uses abstraction layers (SQLAlchemy) to support future database additions.
5. **Separation of Concerns** — Python/FastAPI backend handles business logic and database interaction; Next.js frontend handles the user experience; PostgreSQL stores application state.

### 3.3 MVP Scope

#### Module 1: Database Connection Management
- Create, edit, delete, and test Oracle database connections
- Store connection details securely (encrypted credentials)
- Connection pooling configuration
- Health check / connectivity test

#### Module 2: API Creation Wizard
A step-by-step wizard flow:
1. **Select Connection** — Choose from pre-configured database connections
2. **Write SQL Query** — SQL editor with syntax highlighting; define dynamic parameters (`:param_name` bind variables)
3. **Preview & Map Results** — Execute query preview, view JSON structure, configure column mapping/renaming
4. **Configure Authentication** — Select from pre-configured auth methods (Bearer token, Basic Auth, API key)
5. **Define Endpoint** — Set the URL path, HTTP method (GET for MVP), response format
6. **Set Data Strategy** — Choose between:
   - **Live Query** — Execute SQL on every API call
   - **Scheduled Snapshot** — Run SQL on a schedule, cache results as JSON (in file or PostgreSQL)
7. **Review & Deploy** — Summary page, then activate the endpoint

#### Module 3: Authentication Configuration
- Create and manage authentication methods
- Supported types (MVP): Bearer Token, Basic Authentication, API Key (header)
- Custom header requirements per auth method
- Token generation and management

#### Module 4: Task Scheduling
- Create scheduled tasks to refresh cached API data
- Configurable frequencies (cron-style: every N minutes/hours/daily/weekly/custom)
- Task execution logging (start time, duration, success/failure, row count)
- Manual trigger option
- Task enable/disable toggle

#### Module 5: Settings
- Configure API base URL and port
- Application-level settings (logging level, max query timeout, etc.)
- System health dashboard

### 3.4 Proposed Tech Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| **Backend API** | Python 3.11+ / FastAPI | User preference; async support; auto-generated OpenAPI docs |
| **Oracle Connectivity** | python-oracledb | Official Oracle Python driver; thin mode (no Oracle Client needed) |
| **ORM / Query Layer** | SQLAlchemy 2.0 | Database abstraction for future multi-DB support |
| **App Database** | PostgreSQL | Stores connections, endpoints, schedules, logs, cached results |
| **Task Scheduling** | APScheduler | Python-native scheduler with cron triggers; persistent job store in PostgreSQL |
| **Frontend** | Next.js 14+ (App Router) | User preference; SSR/SSG capabilities |
| **UI Components** | shadcn/ui + Tailwind CSS | User preference; modern, accessible component library |
| **Testing** | pytest + pytest-asyncio | User preference; comprehensive async test support |
| **Auth Library** | python-jose + passlib | JWT token handling and password hashing |
| **Logging** | Python logging + structlog | Structured JSON logging for all operations |
| **Containerization** | Docker + docker-compose | Consistent deployment across environments |

### 3.5 High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Next.js Frontend                  │
│            (shadcn/ui + Tailwind CSS)                │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ Wizard   │ │ Connections│ │ Auth     │ │Settings│ │
│  │ UI       │ │ Manager   │ │ Manager  │ │ Page   │ │
│  └────┬─────┘ └─────┬────┘ └────┬─────┘ └───┬────┘ │
└───────┼──────────────┼──────────┼────────────┼──────┘
        │              │          │            │
        ▼              ▼          ▼            ▼
┌─────────────────────────────────────────────────────┐
│                FastAPI Backend                        │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │           Admin API (/api/admin/*)            │   │
│  │  • Connection CRUD    • Auth Method CRUD      │   │
│  │  • Endpoint CRUD      • Schedule CRUD         │   │
│  │  • Settings           • Logs                  │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │        Dynamic API Router (/api/data/*)       │   │
│  │  • Resolves endpoint path                     │   │
│  │  • Validates authentication                   │   │
│  │  • Returns cached JSON or executes live query │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │ APScheduler  │  │ SQLAlchemy  │  │ Auth       │ │
│  │ (Job Store)  │  │ (ORM)       │  │ Middleware │ │
│  └──────┬───────┘  └──────┬──────┘  └────────────┘ │
└─────────┼────────────────┼──────────────────────────┘
          │                │
          ▼                ▼
┌──────────────┐   ┌──────────────┐
│  PostgreSQL  │   │ Oracle DB(s) │
│  (App Data)  │   │ (User Data)  │
│  • Endpoints │   │              │
│  • Schedules │   │              │
│  • Auth      │   │              │
│  • Logs      │   │              │
│  • Cache     │   │              │
└──────────────┘   └──────────────┘
```

### 3.6 Data Flow: API Request Lifecycle

```
Client Request → GET /api/data/sales/by-region?year=2024
                        │
                        ▼
              ┌─────────────────┐
              │  Auth Middleware │ ── Validates Bearer/Basic/API Key
              └────────┬────────┘
                       │ (authenticated)
                       ▼
              ┌─────────────────┐
              │ Dynamic Router  │ ── Looks up endpoint config by path
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ Data Strategy?  │
              └────┬───────┬────┘
                   │       │
            Cached │       │ Live
                   ▼       ▼
            ┌────────┐ ┌──────────────┐
            │ Return │ │ Execute SQL  │
            │ stored │ │ with params  │
            │ JSON   │ │ on Oracle DB │
            └────────┘ └──────┬───────┘
                              │
                              ▼
                        ┌───────────┐
                        │ Return    │
                        │ JSON      │
                        └───────────┘
```

### 3.7 Security Considerations (Day One)

| Area | Approach |
|------|----------|
| SQL Injection | Parameterized queries only; bind variables enforced; no string concatenation |
| Credential Storage | AES-256 encryption for database passwords; environment-based secrets |
| Authentication | Mandatory on all data endpoints; configurable per-endpoint |
| Authorization | Role-based access in admin panel |
| Input Validation | Pydantic models for all API inputs; parameter type enforcement |
| CORS | Configurable allowed origins |
| Rate Limiting | Configurable per-endpoint rate limits |
| Logging | All access logged with timestamp, IP, user, endpoint, status |
| HTTPS | TLS termination supported via reverse proxy configuration |
| Secrets Management | Environment variables for sensitive config; no secrets in codebase |

### 3.8 Future Roadmap (Post-MVP)

| Phase | Features |
|-------|----------|
| **v1.1** | Additional databases (PostgreSQL, MySQL) via SQLAlchemy dialects |
| **v1.2** | CRUD operations (POST, PUT, DELETE endpoints) |
| **v1.3** | Request body processing and passing to database procedures |
| **v1.4** | Endpoint grouping with parent paths (/group/endpoint) |
| **v2.0** | GraphQL support |
| **v2.1** | Auto-generated OpenAPI/Swagger documentation per endpoint |
| **v2.2** | Postman collection export |
| **v2.3** | API versioning support |

---

## 4. Decision Required

Before proceeding to the detailed implementation plan, please confirm:

1. **Build vs. Adopt:** Do you agree with the recommendation to build custom rather than adopt an existing tool?
2. **Tech Stack:** Is the proposed tech stack (FastAPI + Next.js + PostgreSQL + shadcn/ui) confirmed?
3. **MVP Scope:** Is the 5-module MVP scope correctly captured?
4. **Architecture:** Does the high-level architecture align with your vision?
5. **Any adjustments** to priorities, features, or approach?

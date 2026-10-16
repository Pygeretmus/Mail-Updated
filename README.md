# Mail

A self-hosted, Gmail-style mail service: a **Django REST** API with a **React** single-page client. Users register, send messages to each other (to / cc / bcc), reply in threads, organise mail with labels, and recover deleted messages from the trash.

It is a ground-up rewrite of an earlier, simpler version, with a proper data model, a service layer, a consistent API contract, a full test suite and a one-command Docker setup.

> Mail stays inside the system: every address belongs to a registered user. There is no SMTP.

## Features

- **Compose, reply, reply-all** with `to`, `cc` and `bcc`. BCC is visible only to the sender and is never carried into a reply.
- **Conversations.** Replies join the original thread; opening a message shows the whole conversation from your own point of view.
- **Gmail-style labels.** `inbox`, `sent`, `archive`, `spam` and `starred` are system labels; you can add your own. A message can carry several labels, and "archive" is just a label swap.
- **Trash with recovery.** Deleting is soft; restore it or erase it for good. A scheduled task purges entries that have been in the trash for 30 days.
- **Per-user state.** Read/unread, labels and trash are tracked per mailbox, so Alice reading a message does not mark it read for Bob.
- **Accounts.** Register, sign in (JWT), edit profile, change password, delete account. Sensitive actions require the current password.
- **Client.** Light and dark themes, English and Ukrainian UI, pagination, responsive layout.
- **Ops-friendly.** Rate limiting, OpenAPI docs, Django admin, CI, and a Compose stack with a migration job, worker and scheduler.

## Tech stack

| Layer    | Technology                                                                    |
| -------- | ----------------------------------------------------------------------------- |
| API      | Python 3.13, Django 6, Django REST Framework, SimpleJWT, drf-spectacular      |
| Data     | PostgreSQL 17                                                                 |
| Async    | Celery (worker + beat) with Redis; Redis also backs the cache and rate limits |
| Client   | React 19, TypeScript, Vite (no UI or state libraries)                         |
| Delivery | Docker Compose, nginx reverse proxy, gunicorn                                 |
| Quality  | Django test runner, Ruff, ESLint, GitHub Actions                              |

## Quick start

Requires Docker with Compose.

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

docker compose up --build
```

Then open **<http://127.0.0.1>**. The default configuration is set up for exactly that address.

| URL                                       | What                           |
| ----------------------------------------- | ------------------------------ |
| <http://127.0.0.1>                        | The app                        |
| <http://127.0.0.1/api/schema/swagger-ui/> | Interactive API docs (Swagger) |
| <http://127.0.0.1/api/admin/>             | Django admin                   |

A superuser is created on startup from `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD`. **Change every secret in the `.env` files before exposing the stack anywhere.**

### Services

```mermaid
flowchart LR
    user([Browser]) --> nginx
    nginx -- "/" --> frontend["frontend<br/>static files"]
    nginx -- "/api, /static" --> backend["backend<br/>gunicorn"]

    backend --> postgres[(postgres)]
    backend --> redis[(redis)]
    worker["worker<br/>celery worker"] --> postgres
    worker --> redis
    beat["beat<br/>celery beat"] --> redis

    migrate["migrate<br/>one-off job"] -.->|"schema first"| postgres
```

`backend`, `worker` and `beat` start only after `migrate` has finished. `redis` is the Celery broker and also serves the cache and rate limits.

### Configuration

| Variable                                       | Purpose                                                    |
| ---------------------------------------------- | ---------------------------------------------------------- |
| `SECRET_KEY`                                   | Django secret key                                          |
| `DEBUG`                                        | Defaults to `False`                                        |
| `ALLOWED_HOSTS`                                | Comma-separated hosts                                      |
| `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` | Origins allowed to call the API (add your dev origin here) |
| `DATABASE_URL`                                 | e.g. `postgresql://user:pass@db:5432/postgres`             |
| `REDIS_URL`                                    | Celery broker and cache                                    |
| `DJANGO_SUPERUSER_EMAIL`, `..._PASSWORD`       | Initial admin account                                      |
| `POSTGRES_PASSWORD`                            | Read by Compose for the database container                 |
| `VITE_API_URL`                                 | API base URL baked into the client at build time           |

## Architecture

### Data model

One copy of a message, one small row per person who sees it.

```mermaid
erDiagram
    User ||--o{ MailboxEntry : "has"
    User ||--o{ Label : "owns"
    User |o--o{ Message : "sends"
    Thread ||--o{ Message : "groups"
    Message |o--o{ Message : "replies to"
    Message ||--o{ MailboxEntry : "delivered as"
    MailboxEntry }o--o{ Label : "tagged with"

    MailboxEntry {
        string role "sender, to, cc or bcc"
        bool is_read
        datetime deleted_at "null = not in trash"
    }
    Label {
        string name "unique per user, case-insensitive"
        bool is_system
    }
```

- **`Message`** holds the subject and body once, however many people receive it.
- **`MailboxEntry`** is a message as it sits in one user's mailbox: their role, read state, trash state and labels.
- **`Thread`** groups a conversation so it loads with a single query.
- **`Label`** covers folders and tags alike. System labels are created with the user and can't be renamed or deleted.

Sending a message to three people therefore writes one `Message` and four `MailboxEntry` rows (sender included), instead of copying the text four times as the first version did. Deleting a user removes their entries but keeps messages that others still hold; orphaned messages and threads are cleaned up by the scheduled task.

## API overview

Base path `/api`. All endpoints except registration and login need `Authorization: Bearer <access token>`. Full schemas are in Swagger.

| Method              | Path                            | Description                                                   |
| ------------------- | ------------------------------- | ------------------------------------------------------------- |
| `POST`              | `/token/`, `/token/refresh/`    | Sign in, refresh the access token                             |
| `POST`              | `/accounts/`                    | Register                                                      |
| `GET` `PUT` `PATCH` | `/accounts/me/`                 | Read or update the profile (updates need `current_password`)  |
| `PUT`               | `/accounts/password/`           | Change password                                               |
| `POST`              | `/accounts/destroy/`            | Delete the account (needs `current_password`)                 |
| `GET` `POST`        | `/labels/`                      | List or create labels                                         |
| `PATCH` `DELETE`    | `/labels/{id}/`                 | Rename or delete a custom label (system labels are read-only) |
| `POST`              | `/messages/compose/`            | Send a message (`to`, `cc`, `bcc`, `subject`, `body`)         |
| `GET`               | `/mailbox/?label=inbox`         | List a mailbox by label name (paginated)                      |
| `GET`               | `/mailbox/?deleted=true`        | List the trash                                                |
| `GET`               | `/mailbox/{id}/`                | One message with recipients, as seen by you                   |
| `PATCH`             | `/mailbox/{id}/update_state/`   | Set `is_read` and/or `label_ids`                              |
| `POST`              | `/mailbox/{id}/delete_entry/`   | Move to trash                                                 |
| `POST`              | `/mailbox/{id}/restore_entry/`  | Restore from trash                                            |
| `DELETE`            | `/mailbox/{id}/erase_entry/`    | Delete permanently (trash only)                               |
| `POST`              | `/messages/{id}/reply/`         | Reply, or reply to all with `reply_all: true`                 |
| `GET`               | `/messages/thread/{thread_id}/` | The conversation, oldest first                                |

## Development

### Backend

```bash
cd backend
uv sync
# needs PostgreSQL and Redis; point DATABASE_URL and REDIS_URL at them in backend/.env
uv run manage.py migrate
uv run manage.py runserver
```

### Tests

```bash
cd backend
DATABASE_URL=postgres://user:pass@localhost:5432/postgres \
  uv run manage.py test --settings=configuration.settings.test
```

The suite has 170+ tests, one file per endpoint plus services and the cleanup task, written in an arrange/act/assert style. Test settings disable throttling and use a fast password hasher and an in-memory cache, so no Redis is needed.

```bash
uv run ruff check . && uv run ruff format --check .   # lint
```

### Frontend

```bash
cd frontend
npm ci
npm run dev        # http://localhost:5173
npm run lint
npm run build
```

When running the dev server, set `VITE_API_URL` to your API and add `http://localhost:5173` to `CORS_ALLOWED_ORIGINS`.

### Continuous integration

GitHub Actions runs the backend tests, a check for missing migrations, a forward → backward → forward migration test, Ruff, and the frontend ESLint and production build.

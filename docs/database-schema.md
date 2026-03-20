# Database Schema

## Tables

### `users`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| username | VARCHAR(50) | Unique, indexed |
| email | VARCHAR(120) | Unique, indexed |
| hashed_password | VARCHAR(255) | bcrypt hash |
| created_at | DATETIME | Server default now() |

### `groups`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | VARCHAR(100) | |
| description | TEXT | Nullable |
| owner_id | INTEGER FK | → users.id |
| created_at | DATETIME | |

### `group_memberships`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK | → users.id |
| group_id | INTEGER FK | → groups.id |
| role | VARCHAR(20) | "owner" or "member" |
| joined_at | DATETIME | |

Unique constraint on `(user_id, group_id)`.

### `threads`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| group_id | INTEGER FK | → groups.id |
| title | VARCHAR(200) | |
| created_by | INTEGER FK | → users.id |
| created_at | DATETIME | |

### `messages`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| thread_id | INTEGER FK | → threads.id, indexed |
| user_id | INTEGER FK | → users.id, nullable (null = AI) |
| content | TEXT | |
| is_ai | BOOLEAN | Default false |
| created_at | DATETIME | Indexed |

Composite index on `(thread_id, created_at)` for efficient pagination.

### `plans`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| thread_id | INTEGER FK | → threads.id, unique |
| goals | JSON | Array of strings |
| action_items | JSON | Array of `{task, assignee, due_date}` |
| decisions | JSON | Array of strings |
| summary | TEXT | Nullable |
| generated_at | DATETIME | Updated on regeneration |

One plan per thread (unique constraint on `thread_id`). Regenerating a plan updates the existing row.

## Cascade Behavior

- Deleting a `Group` cascades to `GroupMembership` records and `Thread` records
- Deleting a `Thread` cascades to `Message` records and the `Plan` record
- Users are not deleted when removed from a group (membership row is deleted, user row is preserved)

## JSON Column Notes

SQLAlchemy's `JSON` type stores as TEXT in SQLite and maps to native JSONB in PostgreSQL automatically. No migration needed when switching databases.

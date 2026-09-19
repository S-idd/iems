# IEMS API

The school lookup routes below require the existing JWT authentication and an
`ADMIN` or `SCHOOL_ADMIN` role. Supply `Authorization: Bearer <token>`.

## School lookups

| Method | Route | Behavior |
| --- | --- | --- |
| GET | `/api/schools/city/{city}` | Exact city, case-insensitive |
| GET | `/api/schools/state/{state}` | Exact state, case-insensitive |
| GET | `/api/schools/district/{district}` | Exact district, case-insensitive |
| GET | `/api/schools/search?keyword=Academy` | Case-insensitive substring of school name |
| GET | `/api/schools/code/{code}` | Case-insensitive unique school code |

These routes return active schools only. List results are ordered by name, then
ID, and return an empty array for no match. Code lookup returns 404 when missing
or inactive. Lookup inputs are trimmed; blank values and values above the field
limit return 400 (100 characters for location, 200 for keyword, 50 for code).
Search treats `%` and `_` literally, rather than as wildcard instructions.

Successful responses keep the existing wrapper:

```json
{
  "success": true,
  "message": "School retrieved by code",
  "data": {
    "id": 1,
    "name": "Inclusive Academy",
    "code": "INC01",
    "district": "Bengaluru Urban",
    "contactEmail": "school@example.test",
    "active": true
  },
  "timestamp": "2026-09-17T10:00:00"
}
```

The example omits other response fields. Response fields supported by the stored
school model are populated; legacy response placeholders such as faculty counts,
facilities and principal details remain null. `fullAddress` joins available
address parts and never prints the literal string `null`.

## Create and update lookup data

Existing `POST /api/schools` and `PUT /api/schools/{id}` accept two additional
optional fields in `SchoolDto`: `code` (1–50 letters/digits, stored uppercase)
and `district` (up to 100 characters). Existing requests without these fields
remain valid. PUT follows the existing replacement behavior: omitted code or
district becomes null. Codes remain reserved on soft-deleted schools.

```json
{
  "name": "Inclusive Academy",
  "code": "INC01",
  "city": "Bengaluru",
  "state": "Karnataka",
  "district": "Bengaluru Urban",
  "email": "school@example.test"
}
```

A duplicate code detected before saving returns 400. A concurrent database
constraint conflict returns 409, with a structured error and no SQL details.
Missing parameters, malformed JSON and parameter type errors return 400.

## Database migration

`V14__add_school_lookup_fields.sql` adds nullable `code` and `district` columns
and a unique index on `LOWER(code)`. Existing rows keep null values until updated.
Apply through the application's normal Flyway migration process before running
these endpoints against an existing PostgreSQL database. No live application
database was modified during implementation; earlier migrations were unchanged.

## Verification

```bash
mvn -Dtest=SchoolEndpointsIntegrationTest test
```

These tests exercise HTTP mapping, validation, service logic and a real H2 JPA
repository, including create/update, duplicate codes, soft deletion, empty lists,
case-insensitive queries, literal wildcard search and error responses. They do
not exercise the JWT filter or external Kafka/Redis/RabbitMQ services. The new
migration was also checked against an isolated local PostgreSQL database with
existing rows and case-insensitive uniqueness checks.

Unused `spring-kafka-test` was removed from this application's test classpath:
its Scala 2.13 dependency conflicted with Flink's Scala 2.12 during JPA startup.
Embedded Kafka tests should use an isolated module with compatible dependencies.

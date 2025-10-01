# Inclusive Education Management System (IEMS)

A comprehensive school/college ERP system designed to support inclusive education with scholarships, accessibility reports, multi-tenant access, and real-time analytics.

## Architecture

- **Backend**: Spring Boot 3.x with Java 17
- **Database**: PostgreSQL with Flyway migrations
- **Caching**: Redis
- **Messaging**: RabbitMQ for commands, Kafka for events
- **Stream Processing**: Apache Flink
- **Monitoring**: Prometheus, Grafana, Zipkin
- **Containerization**: Docker Compose

## Features

- **Authentication & Authorization**: JWT-based with role-based access control
- **User Management**: Multi-role support (Admin, Teacher, Student, Parent, Support)
- **Accessibility Support**: Disability accommodations, accessibility reports
- **Scholarship Management**: Application processing with approval workflows
- **Event-Driven Architecture**: Real-time notifications and analytics
- **Comprehensive Monitoring**: Metrics, tracing, and dashboards

## Quick Start

### Prerequisites

- Java 17+
- Maven 3.8+
- Docker & Docker Compose
- WSL2 (for Windows users)

### Setup

1. **Clone and setup**:
```bash
git clone <repository-url>
cd iems
```

2. **Start infrastructure services**:
```bash
# Copy environment template
cp .env.example .env

# Start all services
docker-compose up -d

# Wait for services to be ready (check logs)
docker-compose logs -f
```

3. **Build and run the application**:
```bash
# Build the main application
mvn clean package -DskipTests

# Run the application
mvn spring-boot:run

# Or run with Docker
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up iems-app
```

4. **Build and deploy Flink job**:
```bash
cd flink-jobs
mvn clean package
docker build -t iems-flink-job .
```

5. **Verify setup**:
```bash
# Check application health
curl http://localhost:8080/actuator/health

# Check Kafka topics
docker-compose exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list

# Check RabbitMQ
curl -u admin:admin123 http://localhost:15672/api/overview
```

## API Documentation

Once running, access:
- **Swagger UI**: http://localhost:8080/swagger-ui.html
- **API Docs**: http://localhost:8080/v3/api-docs

## Monitoring & Observability

- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Zipkin**: http://localhost:9411
- **RabbitMQ Management**: http://localhost:15672 (admin/admin123)
- **Kafdrop (Kafka UI)**: http://localhost:9000

## Testing

```bash
# Run unit tests
mvn test

# Run integration tests
mvn verify

# Run specific test profile
mvn test -Dspring.profiles.active=test
```

## Sample Usage Flow

1. **Register Admin User**:
```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123","email":"admin@school.com","role":"ADMIN"}'
```

2. **Login and Get Token**:
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

3. **Create School**:
```bash
curl -X POST http://localhost:8080/api/schools \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Inclusive High School","address":"123 Main St","phone":"555-0123"}'
```

## Development

### Running in Development Mode

```bash
# Start only infrastructure
docker-compose up -d postgres redis rabbitmq kafka zookeeper

# Run app with dev profile
mvn spring-boot:run -Dspring.profiles.active=dev
```

### Database Migrations

```bash
# Check migration status
mvn flyway:info

# Run migrations
mvn flyway:migrate

# Rollback (if needed)
mvn flyway:undo
```

## Production Deployment

See [docs/production-hardening.md](docs/production-hardening.md) for production deployment guidelines.

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) for common issues and solutions.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

Copyright © 2024 IEMS Project. All rights reserved.
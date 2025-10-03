#!/bin/bash
# ========== scripts/build-and-run.sh ==========

set -e

echo "=========================================="
echo "IEMS Build and Run Script"
echo "=========================================="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required. Aborting." >&2; exit 1; }
command -v mvn >/dev/null 2>&1 || { echo "Maven is required. Aborting." >&2; exit 1; }

# Copy environment file if not exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
fi

# Start infrastructure
echo "Starting infrastructure services..."
docker-compose up -d postgres redis rabbitmq zookeeper kafka

# Wait for services
echo "Waiting for services to be ready (60 seconds)..."
sleep 60

# Build application
echo "Building main application..."
mvn clean package -DskipTests

# Run database migrations
echo "Running database migrations..."
mvn flyway:migrate

# Build Flink job
echo "Building Flink job..."
cd flink-jobs
mvn clean package
cd ..

# Start monitoring stack
echo "Starting monitoring services..."
docker-compose up -d prometheus grafana zipkin kafdrop

# Create Kafka topics
echo "Creating Kafka topics..."
bash scripts/kafka-setup.sh

# Start Flink cluster
echo "Starting Flink cluster..."
docker-compose up -d flink-jobmanager flink-taskmanager

# Wait for Flink
sleep 10

# Submit Flink job
echo "Submitting Flink job..."
docker cp flink-jobs/target/iems-flink-jobs-1.0.0-SNAPSHOT.jar iems-flink-jobmanager:/opt/flink/usrlib/
docker-compose exec -T flink-jobmanager /opt/flink/bin/flink run /opt/flink/usrlib/iems-flink-jobs-1.0.0-SNAPSHOT.jar &

# Start application
echo "Starting IEMS application..."
mvn spring-boot:run &

echo ""
echo "=========================================="
echo "Build and setup completed!"
echo "Application starting... (this may take a minute)"
echo ""
echo "Access URLs:"
echo "  - API: http://localhost:8080"
echo "  - Swagger: http://localhost:8080/swagger-ui.html"
echo "  - Grafana: http://localhost:3000 (admin/admin123)"
echo "  - Prometheus: http://localhost:9090"
echo "  - Zipkin: http://localhost:9411"
echo "  - RabbitMQ: http://localhost:15672 (admin/admin123)"
echo "  - Kafdrop: http://localhost:9000"
echo "  - Flink: http://localhost:8081"
echo "=========================================="

# ========== scripts/run-tests.sh ==========
#!/bin/bash

set -e

echo "Running IEMS Test Suite..."

# Start test containers
echo "Starting test infrastructure..."
docker-compose -f docker-compose.test.yml up -d

sleep 10

# Run unit tests
echo "Running unit tests..."
mvn test

# Run integration tests
echo "Running integration tests..."
mvn verify -Pintegration-tests

# Generate coverage report
echo "Generating coverage report..."
mvn jacoco:report

# Stop test containers
docker-compose -f docker-compose.test.yml down

echo "Tests completed! Coverage report: target/site/jacoco/index.html"

# ========== scripts/kafka-setup.sh ==========
#!/bin/bash

KAFKA_BROKER="localhost:9092"

echo "Creating Kafka topics for IEMS..."

# Create accessibility events topic
docker-compose exec -T kafka kafka-topics.sh --create \
  --bootstrap-server ${KAFKA_BROKER} \
  --topic iems.events.accessibility \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000 \
  --config compression.type=snappy \
  --if-not-exists

# Create scholarship events topic
docker-compose exec -T kafka kafka-topics.sh --create \
  --bootstrap-server ${KAFKA_BROKER} \
  --topic iems.events.scholarship \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000 \
  --config compression.type=snappy \
  --if-not-exists

# Create enrollment events topic
docker-compose exec -T kafka kafka-topics.sh --create \
  --bootstrap-server ${KAFKA_BROKER} \
  --topic iems.events.enrollment \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000 \
  --config compression.type=snappy \
  --if-not-exists

# Create notification events topic
docker-compose exec -T kafka kafka-topics.sh --create \
  --bootstrap-server ${KAFKA_BROKER} \
  --topic iems.events.notification \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=259200000 \
  --config compression.type=snappy \
  --if-not-exists

# Create metrics topic
docker-compose exec -T kafka kafka-topics.sh --create \
  --bootstrap-server ${KAFKA_BROKER} \
  --topic iems.metrics \
  --partitions 2 \
  --replication-factor 1 \
  --config retention.ms=2592000000 \
  --config compression.type=snappy \
  --if-not-exists

echo "Listing all topics..."
docker-compose exec -T kafka kafka-topics.sh --list --bootstrap-server ${KAFKA_BROKER}

echo "Kafka topics created successfully!"

# ========== scripts/cleanup.sh ==========
#!/bin/bash

echo "Cleaning up IEMS environment..."

# Stop all containers
echo "Stopping Docker containers..."
docker-compose down -v

# Clean Maven builds
echo "Cleaning Maven builds..."
mvn clean
cd flink-jobs && mvn clean && cd ..

# Remove logs
echo "Removing logs..."
rm -rf logs/*

# Remove target directories
rm -rf target/
rm -rf flink-jobs/target/

echo "Cleanup completed!"

# ========== scripts/database-backup.sh ==========
#!/bin/bash

BACKUP_DIR="/backups/postgres/$(date +%Y%m%d)"
mkdir -p ${BACKUP_DIR}

echo "Creating database backup..."

docker-compose exec -T postgres pg_dump -U iemsuser iemsdb | \
  gzip > ${BACKUP_DIR}/iemsdb_$(date +%H%M%S).sql.gz

echo "Backup created: ${BACKUP_DIR}/iemsdb_$(date +%H%M%S).sql.gz"

# Optional: Upload to S3
# aws s3 cp ${BACKUP_DIR}/ s3://iems-backups/postgres/ --recursive

# Cleanup old backups (keep last 30 days)
find /backups/postgres -type d -mtime +30 -exec rm -rf {} \;

echo "Database backup completed!"

# ========== scripts/check-services.sh ==========
#!/bin/bash

echo "Checking IEMS Services Status..."
echo ""

# Check Docker containers
echo "Docker Containers:"
docker-compose ps

echo ""
echo "Service Health Checks:"

# PostgreSQL
if docker-compose exec -T postgres pg_isready -U iemsuser > /dev/null 2>&1; then
    echo "✓ PostgreSQL: Running"
else
    echo "✗ PostgreSQL: Not responding"
fi

# Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis: Running"
else
    echo "✗ Redis: Not responding"
fi

# RabbitMQ
if curl -s -u admin:admin123 http://localhost:15672/api/overview > /dev/null 2>&1; then
    echo "✓ RabbitMQ: Running"
else
    echo "✗ RabbitMQ: Not responding"
fi

# Kafka
if docker-compose exec -T kafka kafka-broker-api-versions.sh --bootstrap-server localhost:9092 > /dev/null 2>&1; then
    echo "✓ Kafka: Running"
else
    echo "✗ Kafka: Not responding"
fi

# Application
if curl -s http://localhost:8080/actuator/health > /dev/null 2>&1; then
    echo "✓ Application: Running"
else
    echo "✗ Application: Not responding"
fi

# Flink
if curl -s http://localhost:8081/overview > /dev/null 2>&1; then
    echo "✓ Flink: Running"
else
    echo "✗ Flink: Not responding"
fi

echo ""
echo "Kafka Topics:"
docker-compose exec -T kafka kafka-topics.sh --list --bootstrap-server localhost:9092

echo ""
echo "RabbitMQ Queues:"
curl -s -u admin:admin123 http://localhost:15672/api/queues | jq -r '.[] | .name'

# ========== scripts/demo-data.sh ==========
#!/bin/bash

echo "Loading demo data into IEMS..."

API_URL="http://localhost:8080"

# Register admin
echo "Creating admin user..."
ADMIN_RESPONSE=$(curl -s -X POST ${API_URL}/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123",
    "email": "admin@iems.com",
    "firstName": "Admin",
    "lastName": "User",
    "role": "ADMIN"
  }')

# Login
echo "Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST ${API_URL}/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.accessToken')

# Create school
echo "Creating school..."
curl -s -X POST ${API_URL}/api/schools \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Inclusive High School",
    "address": "123 Main Street",
    "city": "Springfield",
    "state": "IL",
    "zipCode": "62701",
    "country": "USA",
    "phone": "555-0123",
    "email": "info@inclusivehigh.edu",
    "establishedYear": 1990,
    "studentCapacity": 1000
  }'

echo ""
echo "Demo data loaded successfully!"
echo "Login with: admin / admin123"
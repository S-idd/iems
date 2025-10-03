#!/bin/bash
set -e

KAFKA_BROKER="localhost:9092"
KAFKA_CONTAINER="iems-kafka"

echo "================================================"
echo "Setting up Kafka Topics for IEMS"
echo "================================================"

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
for i in {1..30}; do
    if docker-compose exec -T kafka kafka-broker-api-versions.sh --bootstrap-server ${KAFKA_BROKER} > /dev/null 2>&1; then
        echo "Kafka is ready!"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

echo ""
echo "Creating Kafka topics..."

# Create accessibility events topic
echo "Creating: iems.events.accessibility"
docker-compose exec -T kafka kafka-topics.sh --create \
  --bootstrap-server ${KAFKA_BROKER} \
  --topic iems.events.accessibility \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000 \
  --config compression.type=snappy \
  --if-not-exists

# Create scholarship events topic
echo "Creating: iems.events.scholarship"
docker-compose exec -T kafka kafka-topics.sh --create \
  --bootstrap-server ${KAFKA_BROKER} \
  --topic iems.events.scholarship \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000 \
  --config compression.type=snappy \
  --if-not-exists

# Create enrollment events topic
echo "Creating: iems.events.enrollment"
docker-compose exec -T kafka kafka-topics.sh --create \
  --bootstrap-server ${KAFKA_BROKER} \
  --topic iems.events.enrollment \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000 \
  --config compression.type=snappy \
  --if-not-exists

# Create notification events topic
echo "Creating: iems.events.notification"
docker-compose exec -T kafka kafka-topics.sh --create \
  --bootstrap-server ${KAFKA_BROKER} \
  --topic iems.events.notification \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=259200000 \
  --config compression.type=snappy \
  --if-not-exists

# Create metrics topic
echo "Creating: iems.metrics"
docker-compose exec -T kafka kafka-topics.sh --create \
  --bootstrap-server ${KAFKA_BROKER} \
  --topic iems.metrics \
  --partitions 2 \
  --replication-factor 1 \
  --config retention.ms=2592000000 \
  --config compression.type=snappy \
  --if-not-exists

echo ""
echo "Listing all topics:"
docker-compose exec -T kafka kafka-topics.sh --list --bootstrap-server ${KAFKA_BROKER}

echo ""
echo "================================================"
echo "Kafka topics created successfully!"
echo "================================================"
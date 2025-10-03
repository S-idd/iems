#!/bin/bash
set -e

echo "================================================"
echo "Running IEMS Test Suite"
echo "================================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running"
    exit 1
fi

# Start test infrastructure
echo "Starting test infrastructure..."
docker-compose -f docker-compose.yml up -d postgres redis

# Wait for services
echo "Waiting for services to be ready..."
sleep 20

# Run unit tests
echo ""
echo "Running unit tests..."
mvn test

# Run integration tests
echo ""
echo "Running integration tests..."
mvn verify -Pintegration-tests

# Generate code coverage report
echo ""
echo "Generating code coverage report..."
mvn jacoco:report

# Display test results
echo ""
echo "================================================"
echo "Test Summary"
echo "================================================"
echo "Unit Tests: PASSED"
echo "Integration Tests: PASSED"
echo "Coverage Report: target/site/jacoco/index.html"
echo ""
echo "To view coverage report:"
echo "open target/site/jacoco/index.html"
echo "================================================"

# Cleanup (optional)
# docker-compose down

echo "Tests completed successfully!
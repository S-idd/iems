
#!/bin/bash
# ========== scripts/cleanup.sh ==========
set -e

echo "================================================"
echo "IEMS Cleanup Script"
echo "================================================"

# Stop all Docker containers
echo "Stopping all Docker containers..."
docker-compose down -v

# Remove Docker volumes (optional - uncomment if needed)
# docker volume prune -f

# Clean Maven builds
echo "Cleaning Maven builds..."
mvn clean

# Clean Flink jobs
if [ -d "flink-jobs" ]; then
    echo "Cleaning Flink jobs..."
    cd flink-jobs
    mvn clean
    cd ..
fi

# Remove logs
echo "Removing log files..."
rm -rf logs/*
rm -f *.log

# Remove target directories
echo "Removing target directories..."
rm -rf target/
rm -rf flink-jobs/target/

# Remove generated files
rm -rf .DS_Store
find . -name "*.class" -type f -delete

echo ""
echo "================================================"
echo "Cleanup completed successfully!"
echo "================================================"
# Dockerfile for Flink Job
FROM flink:1.18-scala_2.12-java11

# Copy the JAR file
COPY target/iems-flink-jobs-1.0.0-SNAPSHOT.jar /opt/flink/usrlib/

# Set working directory
WORKDIR /opt/flink

# Create directories for logs
RUN mkdir -p /opt/flink/log

# Environment variables
ENV FLINK_JOB_MAIN_CLASS=com.iems.flink.AccessibilityMetricsJob
ENV FLINK_JOB_PARALLELISM=2

# Entry point to submit the Flink job
ENTRYPOINT ["/bin/bash", "-c", "/opt/flink/bin/flink run -d /opt/flink/usrlib/iems-flink-jobs-1.0.0-SNAPSHOT.jar"]
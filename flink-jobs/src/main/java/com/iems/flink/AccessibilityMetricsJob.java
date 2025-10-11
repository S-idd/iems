package com.iems.flink;

import java.io.FileInputStream;
import java.io.Serializable;
import java.sql.PreparedStatement;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;

import org.apache.flink.api.common.eventtime.*;
import org.apache.flink.api.common.functions.AggregateFunction;
import org.apache.flink.api.common.functions.MapFunction;
import org.apache.flink.api.common.serialization.SimpleStringEncoder;
import org.apache.flink.connector.jdbc.JdbcConnectionOptions;
import org.apache.flink.connector.jdbc.JdbcExecutionOptions;
import org.apache.flink.connector.jdbc.JdbcSink;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.core.fs.Path;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.sink.filesystem.StreamingFileSink;
import org.apache.flink.streaming.api.functions.windowing.ProcessWindowFunction;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.util.Collector;
import org.apache.kafka.clients.consumer.OffsetResetStrategy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.iems.flink.model.WeeklyAccessibilityMetrics;

/**
 * Flink job to compute weekly accessibility metrics by school.
 * Supports Kafka or file input modes and file or JDBC sinks.
 * Configurable via application-dev.properties.
 */
public class AccessibilityMetricsJob implements Serializable {
    private static final long serialVersionUID = 1L;
    private static final Logger LOG = LoggerFactory.getLogger(AccessibilityMetricsJob.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();

    public static void main(String[] args) throws Exception {
        // Load configuration
        Properties config = new Properties();
        try (FileInputStream fis = new FileInputStream("src/main/resources/application-dev.properties")) {
            config.load(fis);
        } catch (Exception e) {
            LOG.warn("Failed to load application-dev.properties, using defaults", e);
        }

        // Parse args
        String mode = config.getProperty("mode", "file");
        String input = config.getProperty("input", "src/test/resources/sample-accessibility-events.json");
        String output = config.getProperty("output", "output/weekly-metrics.json");
        String bootstrapServers = config.getProperty("kafka.bootstrap.servers", "localhost:9092");
        String topic = config.getProperty("kafka.topic", "accessibility-events");
        String sinkType = config.getProperty("sink.type", "file"); // file or jdbc

        for (int i = 0; i < args.length; i += 2) {
            if ("--mode".equals(args[i])) mode = args[i + 1];
            if ("--input".equals(args[i])) input = args[i + 1];
            if ("--output".equals(args[i])) output = args[i + 1];
            if ("--bootstrap.servers".equals(args[i])) bootstrapServers = args[i + 1];
            if ("--topic".equals(args[i])) topic = args[i + 1];
            if ("--sink.type".equals(args[i])) sinkType = args[i + 1];
        }

        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.setParallelism(1); // For local testing

        DataStream<AccessibilityEventRecord> source;

        try {
            if ("kafka".equals(mode)) {
                // Use custom deserialization for Flink 1.18.1
                KafkaSource<AccessibilityEventRecord> kafkaSource = KafkaSource.<AccessibilityEventRecord>builder()
                        .setBootstrapServers(bootstrapServers)
                        .setTopics(topic)
                        .setGroupId(config.getProperty("kafka.group.id", "flink-accessibility-group"))
                        .setStartingOffsets(OffsetsInitializer.committedOffsets(OffsetResetStrategy.EARLIEST))
                        .setValueOnlyDeserializer(new AccessibilityEventDeserializer())
                        .build();

                source = env.fromSource(kafkaSource, WatermarkStrategy.noWatermarks(), "Kafka Source");
            } else {
                source = env.readTextFile(input)
                        .map(new MapFunction<String, AccessibilityEventRecord>() {
                            private static final long serialVersionUID = 1L;

                            @Override
                            public AccessibilityEventRecord map(String json) throws Exception {
                                try {
                                    return MAPPER.readValue(json, AccessibilityEventRecord.class);
                                } catch (Exception e) {
                                    LOG.error("JSON parsing failed for event: {}", json, e);
                                    throw new RuntimeException("Parsing failed for JSON: " + json, e);
                                }
                            }
                        });
            }
        } catch (Exception e) {
            LOG.error("Kafka unavailable or source error, consider switching to file mode", e);
            throw e;
        }

        // Assign timestamps and watermarks
        WatermarkStrategy<AccessibilityEventRecord> wmStrategy = WatermarkStrategy
                .<AccessibilityEventRecord>forBoundedOutOfOrderness(java.time.Duration.ofMinutes(10))
                .withTimestampAssigner(new SerializableTimestampAssigner<AccessibilityEventRecord>() {
                    private static final long serialVersionUID = 1L;

                    @Override
                    public long extractTimestamp(AccessibilityEventRecord record, long recordTimestamp) {
                        return record.getTimestamp();
                    }
                });

        DataStream<WeeklyAccessibilityMetrics> metrics = source
                .assignTimestampsAndWatermarks(wmStrategy)
                .keyBy(AccessibilityEventRecord::getSchoolId)
                .window(TumblingEventTimeWindows.of(Time.days(7)))
                .aggregate(new MetricsAggregator(), new MetricsProcessWindowFunction());

        // Sink based on configuration
        if ("jdbc".equals(sinkType)) {
            JdbcConnectionOptions connOptions = new JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
                    .withUrl(config.getProperty("postgres.url", "jdbc:postgresql://iems-postgres:5432/iems"))
                    .withDriverName("org.postgresql.Driver")
                    .withUsername(config.getProperty("postgres.username", "postgres"))
                    .withPassword(config.getProperty("postgres.password", "root"))
                    .build();

            String table = config.getProperty("postgres.table", "weekly_metrics");
            metrics.addSink(JdbcSink.sink(
                    "INSERT INTO " + table + " (school_id, week_start, week_end, total_reports, avg_severity, reports_by_disability) " +
                            "VALUES (?, ?, ?, ?, ?, ?::jsonb) ON CONFLICT DO NOTHING",
                    (PreparedStatement stmt, WeeklyAccessibilityMetrics metric) -> {
                        stmt.setLong(1, metric.getSchoolId());
                        stmt.setObject(2, metric.getWeekStart());
                        stmt.setObject(3, metric.getWeekEnd());
                        stmt.setLong(4, metric.getTotalReports());
                        stmt.setDouble(5, metric.getAvgSeverity());
                        try {
                            stmt.setString(6, MAPPER.writeValueAsString(metric.getReportsByDisability()));
                        } catch (Exception e) {
                            LOG.error("Failed to serialize reports by disability", e);
                            stmt.setString(6, "{}"); // Fallback to empty JSON
                        }
                    },
                    JdbcExecutionOptions.builder().withBatchSize(1000).build(),
                    connOptions
            ));
        } else {
            StreamingFileSink<String> fileSink = StreamingFileSink
                    .forRowFormat(new Path(output), new SimpleStringEncoder<String>("UTF-8"))
                    .build();
            
            metrics.map(new MapFunction<WeeklyAccessibilityMetrics, String>() {
                private static final long serialVersionUID = 1L;

                @Override
                public String map(WeeklyAccessibilityMetrics metric) throws Exception {
                    try {
                        return MAPPER.writeValueAsString(metric);
                    } catch (Exception e) {
                        LOG.error("Failed to serialize metric", e);
                        return "{}";
                    }
                }
            }).addSink(fileSink);
        }

        env.execute("Accessibility Metrics Job");
    }

    // Aggregator for counts and sums
    public static class MetricsAggregator implements AggregateFunction<AccessibilityEventRecord, Acc, Acc> {
        private static final long serialVersionUID = 1L;

        @Override
        public Acc createAccumulator() {
            return new Acc();
        }

        @Override
        public Acc add(AccessibilityEventRecord record, Acc acc) {
            acc.count++;
            acc.sumSeverity += record.getSeverity();
            acc.disabilityCounts.merge(record.getDisabilityType(), 1L, Long::sum);
            return acc;
        }

        @Override
        public Acc getResult(Acc acc) {
            return acc;
        }

        @Override
        public Acc merge(Acc a, Acc b) {
            a.count += b.count;
            a.sumSeverity += b.sumSeverity;
            b.disabilityCounts.forEach((k, v) -> a.disabilityCounts.merge(k, v, Long::sum));
            return a;
        }
    }

    // Process function to build output with window info
    public static class MetricsProcessWindowFunction extends ProcessWindowFunction<Acc, WeeklyAccessibilityMetrics, Long, TimeWindow> {
        private static final long serialVersionUID = 1L;

        @Override
        public void process(Long schoolId, Context context, Iterable<Acc> elements, Collector<WeeklyAccessibilityMetrics> out) {
            Acc acc = elements.iterator().next();
            long start = context.window().getStart();
            long end = context.window().getEnd() - 1;

            LocalDate weekStart = Instant.ofEpochMilli(start).atZone(ZoneId.of("UTC")).toLocalDate();
            LocalDate weekEnd = Instant.ofEpochMilli(end).atZone(ZoneId.of("UTC")).toLocalDate();

            WeeklyAccessibilityMetrics metrics = new WeeklyAccessibilityMetrics();
            metrics.setSchoolId(schoolId);
            metrics.setWeekStart(weekStart);
            metrics.setWeekEnd(weekEnd);
            metrics.setTotalReports(acc.count);
            metrics.setAvgSeverity(acc.count > 0 ? acc.sumSeverity / acc.count : 0.0);
            metrics.setReportsByDisability(acc.disabilityCounts);

            out.collect(metrics);
        }
    }

    // Accumulator class
    public static class Acc implements Serializable {
        private static final long serialVersionUID = 1L;
        long count = 0;
        double sumSeverity = 0.0;
        Map<String, Long> disabilityCounts = new HashMap<>();
    }
}
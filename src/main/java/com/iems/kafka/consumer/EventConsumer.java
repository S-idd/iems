package com.iems.kafka.consumer;

import java.util.List;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Component;

import com.iems.config.KafkaConfig;
import com.iems.kafka.model.AccessibilityEvent;
import com.iems.kafka.model.EnrollmentEvent;
import com.iems.kafka.model.ScholarshipEvent;
import com.iems.model.entity.Notification;
import com.iems.model.entity.User;
import com.iems.repository.NotificationRepository;
import com.iems.repository.UserRepository;

/**
 * Kafka consumer for processing events from various topics.
 */
@Component
public class EventConsumer {

    private static final Logger logger = LoggerFactory.getLogger(EventConsumer.class);

    @Autowired
    private NotificationRepository notificationRepository;

    @Autowired
    private UserRepository userRepository;

    /**
     * Consume accessibility events for notification processing.
     */
    @KafkaListener(
        topics = KafkaConfig.ACCESSIBILITY_EVENTS_TOPIC,
        groupId = "${spring.kafka.consumer.group-id}",
        containerFactory = "kafkaListenerContainerFactory"
    )
    public void consumeAccessibilityEvent(
            @Payload AccessibilityEvent event,
            @Header(KafkaHeaders.RECEIVED_PARTITION) int partition,
            @Header(KafkaHeaders.OFFSET) long offset,
            Acknowledgment acknowledgment) {
        
        logger.info("Received accessibility event: {} from partition: {}, offset: {}", 
                    event.getEventType(), partition, offset);
        
        try {
            processAccessibilityEvent(event);
            acknowledgment.acknowledge();
            logger.info("Successfully processed accessibility event ID: {}", event.getId());
        } catch (Exception e) {
            logger.error("Error processing accessibility event: {}", event.getId(), e);
            // Don't acknowledge - message will be reprocessed
        }
    }

    /**
     * Consume scholarship events for notification and analytics.
     */
    @KafkaListener(
        topics = KafkaConfig.SCHOLARSHIP_EVENTS_TOPIC,
        groupId = "${spring.kafka.consumer.group-id}",
        containerFactory = "kafkaListenerContainerFactory"
    )
    public void consumeScholarshipEvent(
            @Payload ScholarshipEvent event,
            @Header(KafkaHeaders.RECEIVED_PARTITION) int partition,
            @Header(KafkaHeaders.OFFSET) long offset,
            Acknowledgment acknowledgment) {
        
        logger.info("Received scholarship event: {} from partition: {}, offset: {}", 
                    event.getEventType(), partition, offset);
        
        try {
            processScholarshipEvent(event);
            acknowledgment.acknowledge();
            logger.info("Successfully processed scholarship event ID: {}", event.getScholarshipId());
        } catch (Exception e) {
            logger.error("Error processing scholarship event: {}", event.getScholarshipId(), e);
        }
    }

    /**
     * Consume enrollment events.
     */
    @KafkaListener(
        topics = KafkaConfig.ENROLLMENT_EVENTS_TOPIC,
        groupId = "${spring.kafka.consumer.group-id}",
        containerFactory = "kafkaListenerContainerFactory"
    )
    public void consumeEnrollmentEvent(
            @Payload EnrollmentEvent event,
            @Header(KafkaHeaders.RECEIVED_PARTITION) int partition,
            @Header(KafkaHeaders.OFFSET) long offset,
            Acknowledgment acknowledgment) {
        
        logger.info("Received enrollment event: {} from partition: {}, offset: {}", 
                    event.getEventType(), partition, offset);
        
        try {
            processEnrollmentEvent(event);
            acknowledgment.acknowledge();
            logger.info("Successfully processed enrollment event ID: {}", event.getEnrollmentId());
        } catch (Exception e) {
            logger.error("Error processing enrollment event: {}", event.getEnrollmentId(), e);
        }
    }

    /**
     * Process accessibility event and create notifications.
     */
    private void processAccessibilityEvent(AccessibilityEvent event) {
        String message;
        String title;

        switch (event.getEventType()) {
            case "REPORT_CREATED":
                title = "New Accessibility Report";
                message = String.format("A new accessibility report has been created for %s at %s. " +
                                      "Severity: %s", 
                                      event.getStudentName(), event.getSchoolName(), event.getSeverity());
                // Notify support staff and school admins
                notifySchoolAdmins(event.getSchoolId(), title, message);
                notifySupportStaff(title, message);
                break;

            case "REPORT_RESOLVED":
                title = "Accessibility Report Resolved";
                message = String.format("Accessibility report for %s has been resolved.", 
                                      event.getStudentName());
                // Notify student
                createNotificationForStudent(event.getStudentId(), title, message);
                break;

            case "REPORT_UPDATED":
                title = "Accessibility Report Updated";
                message = String.format("Accessibility report for %s has been updated.", 
                                      event.getStudentName());
                break;

            case "ACCOMMODATION_UPDATED":
                title = "Accommodation Updated";
                message = String.format("Accommodation details have been updated for %s.", 
                                      event.getStudentName());
                createNotificationForStudent(event.getStudentId(), title, message);
                break;

            default:
                logger.warn("Unknown accessibility event type: {}", event.getEventType());
        }
    }

    /**
     * Process scholarship event and create notifications.
     */
    private void processScholarshipEvent(ScholarshipEvent event) {
        String message;
        String title;

        switch (event.getEventType()) {
            case "APPLIED":
                title = "Scholarship Application Received";
                message = String.format("Your scholarship application has been received and is under review. " +
                                      "Application ID: %d", event.getScholarshipId());
                createNotificationForStudent(event.getStudentId(), title, message);
                break;

            case "APPROVED":
                title = "Scholarship Approved!";
                message = String.format("Congratulations! Your scholarship application has been approved. " +
                                      "Approved amount: $%.2f", event.getAmount().doubleValue());
                createNotificationForStudent(event.getStudentId(), title, message);
                break;

            case "REJECTED":
                title = "Scholarship Application Status";
                message = "We regret to inform you that your scholarship application was not approved at this time.";
                createNotificationForStudent(event.getStudentId(), title, message);
                break;

            case "DISBURSED":
                title = "Scholarship Disbursed";
                message = String.format("Your scholarship funds of $%.2f have been disbursed.", 
                                      event.getAmount().doubleValue());
                createNotificationForStudent(event.getStudentId(), title, message);
                break;

            default:
                logger.warn("Unknown scholarship event type: {}", event.getEventType());
        }
    }

    /**
     * Process enrollment event and create notifications.
     */
    private void processEnrollmentEvent(EnrollmentEvent event) {
        String message;
        String title;

        switch (event.getEventType()) {
            case "ENROLLED":
                title = "Course Enrollment Confirmed";
                message = String.format("You have been successfully enrolled in %s (%s).", 
                                      event.getCourseCode(), event.getCourseCode());
                createNotificationForStudent(event.getStudentId(), title, message);
                break;

            case "DROPPED":
                title = "Course Dropped";
                message = String.format("You have dropped the course %s.", event.getCourseCode());
                createNotificationForStudent(event.getStudentId(), title, message);
                break;

            case "COMPLETED":
                title = "Course Completed";
                message = String.format("Congratulations! You have completed %s.", event.getCourseCode());
                createNotificationForStudent(event.getStudentId(), title, message);
                break;

            default:
                logger.warn("Unknown enrollment event type: {}", event.getEventType());
        }
    }

    /**
     * Create notification for a specific student.
     */
    private void createNotificationForStudent(Long studentId, String title, String message) {
        try {
            // Find user by student profile ID
            User user = userRepository.findById(studentId).orElse(null);
            if (user != null) {
                Notification notification = new Notification();
                notification.setUser(user);
                notification.setTitle(title);
                notification.setMessage(message);
                notification.setType("SYSTEM");
                notification.setIsRead(false);
                notificationRepository.save(notification);
                logger.debug("Created notification for student ID: {}", studentId);
            }
        } catch (Exception e) {
            logger.error("Error creating notification for student: {}", studentId, e);
        }
    }

    /**
     * Notify all school administrators.
     */
    private void notifySchoolAdmins(Long schoolId, String title, String message) {
        try {
            List<User> schoolAdmins = userRepository.findBySchoolIdAndActive(schoolId, true)
                    .stream()
                    .filter(u -> u.getRole().toString().contains("ADMIN"))
                    .collect(Collectors.toList());

            for (User admin : schoolAdmins) {
                Notification notification = new Notification();
                notification.setUser(admin);
                notification.setTitle(title);
                notification.setMessage(message);
                notification.setType("ADMIN");
                notification.setIsRead(false);
                notificationRepository.save(notification);
            }
            logger.debug("Notified {} school admins for school ID: {}", schoolAdmins.size(), schoolId);
        } catch (Exception e) {
            logger.error("Error notifying school admins for school: {}", schoolId, e);
        }
    }

    /**
     * Notify all support staff members.
     */
    private void notifySupportStaff(String title, String message) {
        try {
            List<User> supportStaff = userRepository.findByRole(com.iems.model.enums.UserRole.SUPPORT);

            for (User staff : supportStaff) {
                Notification notification = new Notification();
                notification.setUser(staff);
                notification.setTitle(title);
                notification.setMessage(message);
                notification.setType("SUPPORT");
                notification.setIsRead(false);
                notificationRepository.save(notification);
            }
            logger.debug("Notified {} support staff members", supportStaff.size());
        } catch (Exception e) {
            logger.error("Error notifying support staff", e);
        }
    }
}
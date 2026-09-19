package com.iems.controller;

import com.iems.model.dto.NotificationDto;
import com.iems.security.UserPrincipal;
import com.iems.service.NotificationService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * REST controller for notification management.
 */
@RestController
@RequestMapping("/api/notifications")
@Tag(name = "Notifications", description = "Notification management endpoints")
@SecurityRequirement(name = "bearerAuth")
public class NotificationController {

    @Autowired
    private NotificationService notificationService;

    @GetMapping
    @Operation(summary = "Get user notifications", description = "Get all notifications for current user")
    public ResponseEntity<List<NotificationDto>> getUserNotifications(
            @AuthenticationPrincipal UserPrincipal userPrincipal) {
        List<NotificationDto> notifications = notificationService.getNotificationsByUser(userPrincipal.getId())
                .stream().map(NotificationDto::from).toList();
        return ResponseEntity.ok(notifications);
    }

    @GetMapping("/unread")
    @Operation(summary = "Get unread notifications", description = "Get unread notifications for current user")
    public ResponseEntity<List<NotificationDto>> getUnreadNotifications(
            @AuthenticationPrincipal UserPrincipal userPrincipal) {
        List<NotificationDto> notifications = notificationService.getUnreadNotifications(userPrincipal.getId())
                .stream().map(NotificationDto::from).toList();
        return ResponseEntity.ok(notifications);
    }

    @GetMapping("/unread/count")
    @Operation(summary = "Get unread count", description = "Get count of unread notifications")
    public ResponseEntity<Long> getUnreadCount(
            @AuthenticationPrincipal UserPrincipal userPrincipal) {
        Long count = notificationService.getUnreadCount(userPrincipal.getId());
        return ResponseEntity.ok(count);
    }

    @PutMapping("/{id}/read")
    @Operation(summary = "Mark as read", description = "Mark a notification as read")
    public ResponseEntity<Void> markAsRead(@PathVariable Long id,
            @AuthenticationPrincipal UserPrincipal userPrincipal) {
        notificationService.markAsRead(id, userPrincipal.getId());
        return ResponseEntity.noContent().build();
    }

    @PutMapping("/mark-all-read")
    @Operation(summary = "Mark all as read", description = "Mark all notifications as read")
    public ResponseEntity<Void> markAllAsRead(
            @AuthenticationPrincipal UserPrincipal userPrincipal) {
        notificationService.markAllAsRead(userPrincipal.getId());
        return ResponseEntity.noContent().build();
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete notification", description = "Delete a notification")
    public ResponseEntity<Void> deleteNotification(@PathVariable Long id,
            @AuthenticationPrincipal UserPrincipal userPrincipal) {
        notificationService.deleteNotification(id, userPrincipal.getId());
        return ResponseEntity.noContent().build();
    }
}

package com.iems.model.dto;

import java.time.LocalDateTime;

import com.iems.model.entity.Notification;

public record NotificationDto(
        Long id,
        String title,
        String message,
        String type,
        Boolean isRead,
        LocalDateTime readAt,
        LocalDateTime createdAt) {

    public static NotificationDto from(Notification notification) {
        return new NotificationDto(
                notification.getId(),
                notification.getTitle(),
                notification.getMessage(),
                notification.getType(),
                notification.getIsRead(),
                notification.getReadAt(),
                notification.getCreatedAt());
    }
}

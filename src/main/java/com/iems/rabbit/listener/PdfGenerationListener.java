package com.iems.rabbit.listener;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

import com.iems.config.RabbitConfig;
import com.iems.rabbit.model.PdfTask;

/**
 * Listener for processing PDF generation tasks from RabbitMQ.
 */
@Component
public class PdfGenerationListener {
    private static final Logger logger = LoggerFactory.getLogger(PdfGenerationListener.class);

    @RabbitListener(queues = RabbitConfig.PDF_QUEUE)
    public void handlePdfTask(PdfTask task) {
        logger.info("Received PDF generation task: {} for entity: {}", 
                    task.getDocumentType(), task.getEntityId());
        try {
            // PDF generation logic here
            // For now, just log the task
            logger.info("Processing PDF: Template={}, Type={}, EntityId={}", 
                       task.getTemplateName(), task.getDocumentType(), task.getEntityId());
            
            // Simulate PDF generation
            Thread.sleep(2000);
            
            String outputPath = "/tmp/pdf/" + task.getDocumentType() + "_" + task.getEntityId() + ".pdf";
            task.setOutputPath(outputPath);
            
            logger.info("PDF generated successfully: {}", outputPath);
        } catch (Exception e) {
            logger.error("Failed to generate PDF: {}", task.getDocumentType(), e);
            throw new RuntimeException("PDF generation failed", e);
        }
    }
}
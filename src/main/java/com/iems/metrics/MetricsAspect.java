package com.iems.metrics;

import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * AOP aspect for automatic metrics collection.
 */
@Aspect
@Component
public class MetricsAspect {

    private static final Logger logger = LoggerFactory.getLogger(MetricsAspect.class);

    @Autowired
    private CustomMetrics customMetrics;

    @Around("execution(* com.iems.service.ScholarshipService.createScholarship(..))")
    public Object trackScholarshipApplication(ProceedingJoinPoint joinPoint) throws Throwable {
        Object result = joinPoint.proceed();
        customMetrics.incrementScholarshipApplications();
        return result;
    }

    @Around("execution(* com.iems.service.ScholarshipService.approveScholarship(..))")
    public Object trackScholarshipApproval(ProceedingJoinPoint joinPoint) throws Throwable {
        long startTime = System.currentTimeMillis();
        Object result = joinPoint.proceed();
        long endTime = System.currentTimeMillis();
        
        customMetrics.incrementScholarshipApprovals();
        customMetrics.recordScholarshipProcessingTime(endTime - startTime);
        
        return result;
    }

    @Around("execution(* com.iems.service.ScholarshipService.rejectScholarship(..))")
    public Object trackScholarshipRejection(ProceedingJoinPoint joinPoint) throws Throwable {
        Object result = joinPoint.proceed();
        customMetrics.incrementScholarshipRejections();
        return result;
    }

    @Around("execution(* com.iems.service.AccessibilityService.createReport(..))")
    public Object trackAccessibilityReport(ProceedingJoinPoint joinPoint) throws Throwable {
        Object result = joinPoint.proceed();
        customMetrics.incrementAccessibilityReports();
        return result;
    }

    @Around("execution(* com.iems.service.AccessibilityService.resolveReport(..))")
    public Object trackAccessibilityResolution(ProceedingJoinPoint joinPoint) throws Throwable {
        long startTime = System.currentTimeMillis();
        Object result = joinPoint.proceed();
        long endTime = System.currentTimeMillis();
        
        customMetrics.incrementAccessibilityReportsResolved();
        customMetrics.recordAccessibilityResolutionTime(endTime - startTime);
        
        return result;
    }
}
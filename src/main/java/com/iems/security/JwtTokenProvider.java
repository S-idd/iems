package com.iems.security;

import java.nio.charset.StandardCharsets;
import java.util.Date;

import javax.crypto.SecretKey;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Component;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.MalformedJwtException;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.UnsupportedJwtException;
import io.jsonwebtoken.security.Keys;

/**
 * JWT token provider for generating and validating JWT tokens.
 */
@Component
public class JwtTokenProvider {

    private static final Logger logger = LoggerFactory.getLogger(JwtTokenProvider.class);

    @Value("${app.jwt.secret}")
    private String jwtSecret;

    @Value("${app.jwt.expiration}")
    private long jwtExpirationMs;

    @Value("${app.jwt.refresh-expiration}")
    private long refreshExpirationMs;

    private SecretKey getSigningKey() {
        return Keys.hmacShaKeyFor(jwtSecret.getBytes(StandardCharsets.UTF_8));
    }

    /**
     * Generate JWT access token from authentication.
     */
    public String generateToken(Authentication authentication) {
        UserPrincipal userPrincipal = (UserPrincipal) authentication.getPrincipal();
        return generateTokenFromUsername(userPrincipal.getUsername());
    }

    /**
     * Generate JWT token from username.
     */
    public String generateTokenFromUsername(String username) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + jwtExpirationMs);

        return Jwts.builder()
                .setSubject(username)
                .setIssuedAt(now)
                .setExpiration(expiryDate)
                .signWith(getSigningKey(), SignatureAlgorithm.HS256)
                .compact();
    }

    /**
     * Generate refresh token.
     */
    public String generateRefreshToken(String username) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + refreshExpirationMs);

        return Jwts.builder()
                .setSubject(username)
                .setIssuedAt(now)
                .setExpiration(expiryDate)
                .claim("type", "refresh")
                .signWith(getSigningKey(), SignatureAlgorithm.HS256)
                .compact();
    }

    /**
     * Extract username from JWT token.
     */
    public String getUsernameFromToken(String token) {
        Claims claims = parseClaims(token);
        return claims.getSubject();
    }

    /**
     * Validate JWT token.
     */
    public boolean validateToken(String token) {
        try {
            parseClaims(token);
            return true;
        } catch (SecurityException ex) {
            logger.error("Invalid JWT signature");
        } catch (MalformedJwtException ex) {
            logger.error("Invalid JWT token");
        } catch (ExpiredJwtException ex) {
            logger.error("Expired JWT token");
        } catch (UnsupportedJwtException ex) {
            logger.error("Unsupported JWT token");
        } catch (IllegalArgumentException ex) {
            logger.error("JWT claims string is empty");
        }
        return false;
    }

    /**
     * Parse claims in a way that's compatible with multiple JJWT API versions.
     */
    private Claims parseClaims(String token) {
        try {
            // Try the newer parserBuilder() -> build() -> parseClaimsJws(...) path
            try {
                java.lang.reflect.Method parserBuilderMethod = Jwts.class.getMethod("parserBuilder");
                Object builder = parserBuilderMethod.invoke(null);
                java.lang.reflect.Method setSigningKeyMethod = builder.getClass().getMethod("setSigningKey", java.security.Key.class);
                setSigningKeyMethod.invoke(builder, getSigningKey());
                java.lang.reflect.Method buildMethod = builder.getClass().getMethod("build");
                Object parser = buildMethod.invoke(builder);
                java.lang.reflect.Method parseMethod = parser.getClass().getMethod("parseClaimsJws", String.class);
                Object jws = parseMethod.invoke(parser, token);
                java.lang.reflect.Method getBody = jws.getClass().getMethod("getBody");
                return (Claims) getBody.invoke(jws);
            } catch (NoSuchMethodException nsme) {
                // Fallback to older parser() API
                java.lang.reflect.Method parserMethod = Jwts.class.getMethod("parser");
                Object parser = parserMethod.invoke(null);
                // try setSigningKey(Key) then setSigningKey(byte[])
                try {
                    java.lang.reflect.Method setKey = parser.getClass().getMethod("setSigningKey", java.security.Key.class);
                    setKey.invoke(parser, getSigningKey());
                } catch (NoSuchMethodException e) {
                    java.lang.reflect.Method setKey2 = parser.getClass().getMethod("setSigningKey", byte[].class);
                    setKey2.invoke(parser, (Object) jwtSecret.getBytes(StandardCharsets.UTF_8));
                }
                java.lang.reflect.Method parseMethod = parser.getClass().getMethod("parseClaimsJws", String.class);
                Object jws = parseMethod.invoke(parser, token);
                java.lang.reflect.Method getBody = jws.getClass().getMethod("getBody");
                return (Claims) getBody.invoke(jws);
            }
        } catch (RuntimeException re) {
            throw re;
        } catch (Exception e) {
            throw new JwtException("Failed to parse JWT token", e);
        }
    }

    /**
     * Get expiration time in milliseconds.
     */
    public long getExpirationMs() {
        return jwtExpirationMs;
    }

    /**
     * Get refresh token expiration time in milliseconds.
     */
    public long getRefreshExpirationMs() {
        return refreshExpirationMs;
    }
}
package com.iems.service;

import java.time.LocalDateTime;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.iems.exception.BadRequestException;
import com.iems.exception.ResourceNotFoundException;
import com.iems.exception.UnauthorizedException;
import com.iems.model.dto.AuthRequest;
import com.iems.model.dto.AuthResponse;
import com.iems.model.dto.RegisterRequest;
import com.iems.model.dto.UserDto;
import com.iems.model.entity.School;
import com.iems.model.entity.User;
import com.iems.repository.SchoolRepository;
import com.iems.repository.UserRepository;
import com.iems.security.JwtTokenProvider;

/**
 * Service for handling authentication and user registration.
 */
@Service
public class AuthService {

    private static final Logger logger = LoggerFactory.getLogger(AuthService.class);

    @Autowired
    private AuthenticationManager authenticationManager;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private SchoolRepository schoolRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtTokenProvider tokenProvider;

    /**
     * Authenticate user and generate tokens.
     */
    @Transactional
    public AuthResponse login(AuthRequest request) {
        Authentication authentication = authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.getUsername(), request.getPassword())
        );

        SecurityContextHolder.getContext().setAuthentication(authentication);

        String accessToken = tokenProvider.generateToken(authentication);
        String refreshToken = tokenProvider.generateRefreshToken(request.getUsername());

        // Update user's last login and refresh token
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new ResourceNotFoundException("User", "username", request.getUsername()));
        
        user.setLastLogin(LocalDateTime.now());
        user.setRefreshToken(refreshToken);
        user.setRefreshTokenExpiry(LocalDateTime.now().plusSeconds(tokenProvider.getRefreshExpirationMs() / 1000));
        userRepository.save(user);

        UserDto userDto = convertToUserDto(user);

        return new AuthResponse(accessToken, refreshToken, tokenProvider.getExpirationMs() / 1000, userDto);
    }

    /**
     * Register a new user.
     */
    @Transactional
    public UserDto register(RegisterRequest request) {
        // Check if username exists
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new BadRequestException("Username is already taken");
        }

        // Check if email exists
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new BadRequestException("Email is already in use");
        }

        User user = new User();
        user.setUsername(request.getUsername());
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        user.setEmail(request.getEmail());
        user.setFirstName(request.getFirstName());
        user.setLastName(request.getLastName());
        user.setPhone(request.getPhone());
        user.setRole(request.getRole());
        user.setActive(true);

        // Assign school if provided
        if (request.getSchoolId() != null) {
            School school = schoolRepository.findById(request.getSchoolId())
                    .orElseThrow(() -> new ResourceNotFoundException("School", "id", request.getSchoolId()));
            user.setSchool(school);
        }

        User savedUser = userRepository.save(user);
        logger.info("New user registered: {}", savedUser.getUsername());

        return convertToUserDto(savedUser);
    }

    /**
     * Refresh access token using refresh token.
     */
    @Transactional
    public AuthResponse refreshToken(String refreshToken) {
        if (!tokenProvider.validateToken(refreshToken)) {
            throw new UnauthorizedException("Invalid refresh token");
        }

        User user = userRepository.findByValidRefreshToken(refreshToken)
                .orElseThrow(() -> new UnauthorizedException("Refresh token not found or expired"));

        String username = user.getUsername();
        String newAccessToken = tokenProvider.generateTokenFromUsername(username);
        String newRefreshToken = tokenProvider.generateRefreshToken(username);

        user.setRefreshToken(newRefreshToken);
        user.setRefreshTokenExpiry(LocalDateTime.now().plusSeconds(tokenProvider.getRefreshExpirationMs() / 1000));
        userRepository.save(user);

        UserDto userDto = convertToUserDto(user);

        return new AuthResponse(newAccessToken, newRefreshToken, tokenProvider.getExpirationMs() / 1000, userDto);
    }

    /**
     * Logout user by invalidating refresh token.
     */
    @Transactional
    public void logout(String username) {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new ResourceNotFoundException("User", "username", username));
        
        user.setRefreshToken(null);
        user.setRefreshTokenExpiry(null);
        userRepository.save(user);
    }

    private UserDto convertToUserDto(User user) {
        UserDto dto = new UserDto();
        dto.setId(user.getId());
        dto.setUsername(user.getUsername());
        dto.setEmail(user.getEmail());
        dto.setFirstName(user.getFirstName());
        dto.setLastName(user.getLastName());
        dto.setPhone(user.getPhone());
        dto.setRole(user.getRole());
        dto.setActive(user.getActive());
        if (user.getSchool() != null) {
            dto.setSchoolId(user.getSchool().getId());
            dto.setSchoolName(user.getSchool().getName());
        }
        return dto;
    }
}
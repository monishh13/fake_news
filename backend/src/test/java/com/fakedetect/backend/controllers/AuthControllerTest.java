package com.fakedetect.backend.controllers;

import com.fakedetect.backend.config.JwtTokenUtil;
import com.fakedetect.backend.models.LoginRequest;
import com.fakedetect.backend.services.CustomUserDetailsService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AuthControllerTest {

    @Mock
    private AuthenticationManager authenticationManager;

    @Mock
    private JwtTokenUtil jwtTokenUtil;

    @Mock
    private CustomUserDetailsService userDetailsService;

    @InjectMocks
    private AuthController authController;

    private MockHttpServletRequest request;

    @BeforeEach
    void setUp() {
        request = new MockHttpServletRequest();
        request.setRemoteAddr("127.0.0.1");
    }

    @Test
    void testSuccessfulLogin() {
        LoginRequest loginRequest = new LoginRequest();
        loginRequest.setUsername("admin");
        loginRequest.setPassword("password");

        UserDetails userDetails = new User("admin", "password", Collections.emptyList());
        when(userDetailsService.loadUserByUsername("admin")).thenReturn(userDetails);
        when(jwtTokenUtil.generateToken(userDetails)).thenReturn("dummy-jwt-token");

        ResponseEntity<?> response = authController.createAuthenticationToken(loginRequest, request);

        assertEquals(HttpStatus.OK, response.getStatusCode());
    }

    @Test
    void testFailedLoginIncrementsAttempts() {
        LoginRequest loginRequest = new LoginRequest();
        loginRequest.setUsername("admin");
        loginRequest.setPassword("wrong");

        when(authenticationManager.authenticate(any())).thenThrow(new BadCredentialsException("Bad info"));

        ResponseEntity<?> response = authController.createAuthenticationToken(loginRequest, request);

        assertEquals(HttpStatus.UNAUTHORIZED, response.getStatusCode());
    }

    @Test
    void testRateLimitingBlocksAfterMaxAttempts() {
        LoginRequest loginRequest = new LoginRequest();
        loginRequest.setUsername("admin");
        loginRequest.setPassword("wrong");

        when(authenticationManager.authenticate(any())).thenThrow(new BadCredentialsException("Bad info"));

        // Simulate 5 failed attempts
        for (int i = 0; i < 5; i++) {
            authController.createAuthenticationToken(loginRequest, request);
        }

        // The 6th attempt should be blocked
        ResponseEntity<?> response = authController.createAuthenticationToken(loginRequest, request);

        assertEquals(HttpStatus.TOO_MANY_REQUESTS, response.getStatusCode());
        verify(authenticationManager, times(5)).authenticate(any()); // Only attempted auth 5 times
    }
}

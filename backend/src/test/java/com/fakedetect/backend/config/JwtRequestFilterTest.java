package com.fakedetect.backend.config;

import com.fakedetect.backend.services.CustomUserDetailsService;
import io.jsonwebtoken.ExpiredJwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;

import java.io.IOException;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class JwtRequestFilterTest {

    @Mock
    private CustomUserDetailsService jwtUserDetailsService;

    @Mock
    private JwtTokenUtil jwtTokenUtil;

    @Mock
    private FilterChain filterChain;

    @InjectMocks
    private JwtRequestFilter jwtRequestFilter;

    private MockHttpServletRequest request;
    private MockHttpServletResponse response;

    @BeforeEach
    void setUp() {
        request = new MockHttpServletRequest();
        response = new MockHttpServletResponse();
        SecurityContextHolder.clearContext();
    }

    @Test
    void testValidTokenPassesThrough() throws ServletException, IOException {
        String token = "valid.jwt.token";
        request.addHeader("Authorization", "Bearer " + token);
        
        UserDetails userDetails = new User("admin", "password", Collections.emptyList());

        when(jwtTokenUtil.getUsernameFromToken(token)).thenReturn("admin");
        when(jwtUserDetailsService.loadUserByUsername("admin")).thenReturn(userDetails);
        when(jwtTokenUtil.validateToken(token, userDetails)).thenReturn(true);

        jwtRequestFilter.doFilterInternal(request, response, filterChain);

        assertNotNull(SecurityContextHolder.getContext().getAuthentication());
        verify(filterChain).doFilter(request, response);
    }

    @Test
    void testExpiredToken() throws ServletException, IOException {
        String token = "expired.jwt.token";
        request.addHeader("Authorization", "Bearer " + token);

        when(jwtTokenUtil.getUsernameFromToken(token)).thenThrow(new ExpiredJwtException(null, null, "Expired"));

        jwtRequestFilter.doFilterInternal(request, response, filterChain);

        assertNull(SecurityContextHolder.getContext().getAuthentication());
        verify(filterChain).doFilter(request, response);
    }

    @Test
    void testMalformedToken() throws ServletException, IOException {
        String token = "malformed.jwt.token";
        request.addHeader("Authorization", "Bearer " + token);

        when(jwtTokenUtil.getUsernameFromToken(token)).thenThrow(new IllegalArgumentException("Malformed"));

        jwtRequestFilter.doFilterInternal(request, response, filterChain);

        assertNull(SecurityContextHolder.getContext().getAuthentication());
        verify(filterChain).doFilter(request, response);
    }

    @Test
    void testMissingToken() throws ServletException, IOException {
        jwtRequestFilter.doFilterInternal(request, response, filterChain);

        assertNull(SecurityContextHolder.getContext().getAuthentication());
        verify(filterChain).doFilter(request, response);
    }
}

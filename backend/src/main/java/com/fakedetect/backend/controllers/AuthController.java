package com.fakedetect.backend.controllers;

import com.fakedetect.backend.config.JwtTokenUtil;
import com.fakedetect.backend.models.AuthResponse;
import com.fakedetect.backend.models.LoginRequest;
import com.fakedetect.backend.services.CustomUserDetailsService;
import jakarta.servlet.http.HttpServletRequest;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;


@RestController
@RequestMapping("/api/auth")
@CrossOrigin(originPatterns = {"http://localhost:5173", "http://localhost", "chrome-extension://*"})
public class AuthController {

    private final AuthenticationManager authenticationManager;
    private final JwtTokenUtil jwtTokenUtil;
    private final CustomUserDetailsService userDetailsService;
    private static final int MAX_ATTEMPTS = 5;
    private static final long LOCK_DURATION_MS = 10 * 60 * 1000;

    // In-memory rate limiting maps
    private final java.util.concurrent.ConcurrentHashMap<String, Integer> loginAttempts = new java.util.concurrent.ConcurrentHashMap<>();
    private final java.util.concurrent.ConcurrentHashMap<String, Long> lockExpirations = new java.util.concurrent.ConcurrentHashMap<>();

    public AuthController(AuthenticationManager authenticationManager, JwtTokenUtil jwtTokenUtil,
                          CustomUserDetailsService userDetailsService) {
        this.authenticationManager = authenticationManager;
        this.jwtTokenUtil = jwtTokenUtil;
        this.userDetailsService = userDetailsService;
    }

    private String getClientIP(HttpServletRequest request) {
        String xfHeader = request.getHeader("X-Forwarded-For");
        if (xfHeader == null) {
            return request.getRemoteAddr();
        }
        return xfHeader.split(",")[0];
    }

    @PostMapping("/login")
    public ResponseEntity<?> createAuthenticationToken(@RequestBody LoginRequest loginRequest, HttpServletRequest request) {
        String ip = getClientIP(request);

        // Check lock expiration
        if (lockExpirations.containsKey(ip) && System.currentTimeMillis() > lockExpirations.get(ip)) {
            loginAttempts.remove(ip);
            lockExpirations.remove(ip);
        }

        int attempts = loginAttempts.getOrDefault(ip, 0);

        if (attempts >= MAX_ATTEMPTS) {
            return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS)
                    .body("IP blocked due to too many failed login attempts. Try again later.");
        }

        try {
            authenticationManager.authenticate(new UsernamePasswordAuthenticationToken(
                    loginRequest.getUsername(), loginRequest.getPassword()));
            
            // Login successful, reset attempts
            loginAttempts.remove(ip);
            lockExpirations.remove(ip);
            
            final UserDetails userDetails = userDetailsService.loadUserByUsername(loginRequest.getUsername());
            final String jwt = jwtTokenUtil.generateToken(userDetails);

            return ResponseEntity.ok(new AuthResponse(jwt));
        } catch (BadCredentialsException e) {
            // Increment failed attempts
            int newAttempts = attempts + 1;
            loginAttempts.put(ip, newAttempts);
            if (newAttempts == 1) {
                // First failed attempt, set expiration timer
                lockExpirations.put(ip, System.currentTimeMillis() + LOCK_DURATION_MS);
            }
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body("Incorrect username or password");
        }
    }
}

package com.fakedetect.backend.config;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class ApiKeyInterceptor implements HandlerInterceptor {

    @Value("${api.key.secret:aivera-secret-key-123}")
    private String apiKeySecret;

    @Value("${api.rate.limit:60}")
    private int rateLimit; // per minute

    // Map of IP/Key to (timestamp, count)
    private final ConcurrentHashMap<String, RateLimitData> rateLimitMap = new ConcurrentHashMap<>();

    public static class RateLimitData {
        long resetTime;
        int count;
        public RateLimitData(long resetTime, int count) {
            this.resetTime = resetTime;
            this.count = count;
        }
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        // Skip for OPTIONS / Actuator / Swagger docs
        if (request.getMethod().equals("OPTIONS") || request.getRequestURI().contains("swagger-ui") || request.getRequestURI().contains("api-docs")) {
            return true;
        }
        
        // Target /api/ endpoints to enforce rate limits
        if (request.getRequestURI().startsWith("/api/")) {
            String clientIp = request.getRemoteAddr();
            String clientKey = request.getHeader("X-API-KEY");
            
            // Allow higher limits if valid API key is provided, or just rate limit strictly by IP if not.
            String identifier = (clientKey != null && clientKey.equals(apiKeySecret)) ? clientKey : clientIp;

            long now = System.currentTimeMillis();
            rateLimitMap.compute(identifier, (k, v) -> {
                if (v == null || now > v.resetTime) {
                    return new RateLimitData(now + 60000, 1); // Reset bucket (1 min)
                }
                v.count++;
                return v;
            });

            RateLimitData data = rateLimitMap.get(identifier);
            if (data.count > rateLimit) {
                response.setStatus(429);
                response.getWriter().write("Too Many Requests - Rate Limit Exceeded");
                return false;
            }
        }
        
        return true;
    }
}

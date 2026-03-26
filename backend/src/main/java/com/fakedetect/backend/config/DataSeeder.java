package com.fakedetect.backend.config;

import com.fakedetect.backend.models.User;
import com.fakedetect.backend.repositories.UserRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

@Component
public class DataSeeder implements CommandLineRunner {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @Value("${ADMIN_USERNAME:#{null}}")
    private String adminUsername;

    @Value("${ADMIN_PASSWORD:#{null}}")
    private String adminPassword;

    public DataSeeder(UserRepository userRepository, PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }

    @Override
    public void run(String... args) throws Exception {
        if (userRepository.count() == 0) {
            if (!StringUtils.hasText(adminUsername) || !StringUtils.hasText(adminPassword)) {
                throw new IllegalStateException("ADMIN_USERNAME and ADMIN_PASSWORD environment variables must be set! Start failed.");
            }
            User admin = new User();
            admin.setUsername(adminUsername);
            admin.setPassword(passwordEncoder.encode(adminPassword));
            admin.setRole("ROLE_ADMIN");
            userRepository.save(admin);
            System.out.println("Default admin user created from environment variables.");
        }
    }
}

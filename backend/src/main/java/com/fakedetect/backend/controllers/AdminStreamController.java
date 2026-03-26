package com.fakedetect.backend.controllers;

import com.fakedetect.backend.services.AdminEventService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import org.springframework.web.bind.annotation.CrossOrigin;

@RestController
@RequestMapping("/api/admin")
@CrossOrigin(originPatterns = {"http://localhost:5173", "http://localhost", "chrome-extension://*"})
public class AdminStreamController {

    private final AdminEventService eventService;

    public AdminStreamController(AdminEventService eventService) {
        this.eventService = eventService;
    }

    @GetMapping("/stream")
    public SseEmitter stream() {
        return eventService.addEmitter();
    }
}

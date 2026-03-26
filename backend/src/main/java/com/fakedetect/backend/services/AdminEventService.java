package com.fakedetect.backend.services;

import com.fakedetect.backend.models.Article;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
public class AdminEventService {

    private final List<SseEmitter> emitters = new CopyOnWriteArrayList<>();

    public SseEmitter addEmitter() {
        SseEmitter emitter = new SseEmitter(Long.MAX_VALUE);
        emitters.add(emitter);
        
        emitter.onCompletion(() -> emitters.remove(emitter));
        emitter.onTimeout(() -> emitters.remove(emitter));
        emitter.onError((e) -> emitters.remove(emitter));
        
        return emitter;
    }

    public void broadcastNewAnalysis(Article article) {
        synchronized (emitters) {
            for (SseEmitter emitter : emitters) {
                try {
                    emitter.send(SseEmitter.event()
                            .name("NEW_ARTICLE")
                            .data(article));
                } catch (IOException e) {
                    emitters.remove(emitter);
                }
            }
        }
    }

    public void broadcastSystemStatus(String status) {
        synchronized (emitters) {
            for (SseEmitter emitter : emitters) {
                try {
                    emitter.send(SseEmitter.event()
                            .name("SYSTEM_STATUS")
                            .data(status));
                } catch (IOException e) {
                    emitters.remove(emitter);
                }
            }
        }
    }
}

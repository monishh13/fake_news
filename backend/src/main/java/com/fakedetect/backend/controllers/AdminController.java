package com.fakedetect.backend.controllers;

import com.fakedetect.backend.models.AdminStatsResponse;
import com.fakedetect.backend.models.AdvancedStatsResponse;
import com.fakedetect.backend.models.Article;
import com.fakedetect.backend.repositories.ArticleRepository;
import com.fakedetect.backend.repositories.ClaimRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.io.BufferedWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/admin")
@CrossOrigin(originPatterns = {"http://localhost:5173", "http://localhost", "chrome-extension://*"})
public class AdminController {

    private final ArticleRepository articleRepository;
    private final ClaimRepository claimRepository;
    private final com.fakedetect.backend.services.AdminEventService eventService;

    public AdminController(ArticleRepository articleRepository, ClaimRepository claimRepository, com.fakedetect.backend.services.AdminEventService eventService) {
        this.articleRepository = articleRepository;
        this.claimRepository = claimRepository;
        this.eventService = eventService;
    }

    @GetMapping(value = "/stream", produces = org.springframework.http.MediaType.TEXT_EVENT_STREAM_VALUE)
    public org.springframework.web.servlet.mvc.method.annotation.SseEmitter streamEvents() {
        return eventService.addEmitter();
    }

    @GetMapping("/stats")
    public ResponseEntity<AdminStatsResponse> getStats() {
        int totalArticles = (int) articleRepository.count();
        int totalClaims = (int) claimRepository.count();
        
        Double avgCredibility = articleRepository.getAverageCredibilityScore();
        if (avgCredibility == null) avgCredibility = 0.0;
        
        int fakeCount = (int) articleRepository.countFakeArticles();
        int realCount = (int) articleRepository.countRealArticles();

        AdminStatsResponse stats = new AdminStatsResponse(totalArticles, totalClaims, avgCredibility, fakeCount, realCount);
        return ResponseEntity.ok(stats);
    }

    @GetMapping("/articles")
    public ResponseEntity<Page<Article>> getArticles(Pageable pageable) {
        Page<Article> articles = articleRepository.findAll(pageable);
        return ResponseEntity.ok(articles);
    }

    @PatchMapping("/articles/{id}/override")
    public ResponseEntity<?> overrideArticle(
            @PathVariable("id") Long id,
            @RequestBody java.util.Map<String, Object> updates) {
        try {
            return articleRepository.findById(id).map(article -> {
                if (updates.containsKey("verdictOverride")) {
                    Object val = updates.get("verdictOverride");
                    article.setVerdictOverride(val == null ? null : Double.valueOf(val.toString()));
                }
                if (updates.containsKey("adminNotes")) article.setAdminNotes((String) updates.get("adminNotes"));
                if (updates.containsKey("severity")) article.setSeverity((String) updates.get("severity"));
                
                Article saved = articleRepository.save(article);
                return ResponseEntity.ok(saved);
            }).orElse(ResponseEntity.notFound().build());
        } catch (Exception e) {
            e.printStackTrace(); // Log to backend console
            return ResponseEntity.status(500).body(java.util.Map.of(
                "error", e.getMessage() != null ? e.getMessage() : "Internal Error in Audit Pipeline",
                "type", e.getClass().getSimpleName()
            ));
        }
    }

    @GetMapping("/stats/advanced")
    public ResponseEntity<AdvancedStatsResponse> getAdvancedStats() {
        java.util.List<Article> all = articleRepository.findAll();
        
        // 1. Confidence Distribution (Buckets)
        java.util.Map<String, Long> distribution = new java.util.TreeMap<>();
        String[] buckets = {"0-20%", "20-40%", "40-60%", "60-80%", "80-100%"};
        for (String b : buckets) distribution.put(b, 0L);
        
        // 2. Verdict Distribution (Real vs Fake)
        java.util.Map<String, Long> verdicts = new java.util.HashMap<>();
        verdicts.put("Verified Real", 0L);
        verdicts.put("Flagged Fake", 0L);

        // 3. Daily Analysis Volume (Last 7 Days)
        java.util.Map<String, Long> dailyVolume = new java.util.LinkedHashMap<>();
        java.time.LocalDate today = java.time.LocalDate.now();
        for (int i = 6; i >= 0; i--) {
            dailyVolume.put(today.minusDays(i).toString(), 0L);
        }

        for (Article a : all) {
            double score = a.getOverallCredibility();
            // Confidence Buckets
            if (score <= 0.2) distribution.merge("0-20%", 1L, Long::sum);
            else if (score <= 0.4) distribution.merge("20-40%", 1L, Long::sum);
            else if (score <= 0.6) distribution.merge("40-60%", 1L, Long::sum);
            else if (score <= 0.8) distribution.merge("60-80%", 1L, Long::sum);
            else distribution.merge("80-100%", 1L, Long::sum);

            // Verdict Distribution
            if (score >= 0.5) verdicts.merge("Verified Real", 1L, Long::sum);
            else verdicts.merge("Flagged Fake", 1L, Long::sum);

            // Daily Volume
            String dateStr = a.getCreatedAt().toLocalDate().toString();
            if (dailyVolume.containsKey(dateStr)) {
                dailyVolume.merge(dateStr, 1L, Long::sum);
            }
        }

        // Mock Source
        java.util.Map<String, Long> sources = new java.util.HashMap<>();
        sources.put("social-media", all.stream().filter(a -> a.getContent().length() < 280).count());
        sources.put("long-form", all.stream().filter(a -> a.getContent().length() >= 280).count());

        Double avgLatency = articleRepository.getAverageLatency();
        if (avgLatency == null) avgLatency = 0.0;

        AdvancedStatsResponse advanced = new AdvancedStatsResponse(
            distribution, 
            verdicts,
            dailyVolume,
            sources, 
            avgLatency, 
            3L 
        );
        return ResponseEntity.ok(advanced);
    }

    @PostMapping("/articles/purge")
    public ResponseEntity<String> purgeArticles(@RequestParam("days") int days) {
        java.time.LocalDateTime cutoff = java.time.LocalDateTime.now().minusDays(days);
        articleRepository.purgeOldArticles(cutoff);
        return ResponseEntity.ok("Purged articles older than " + days + " days.");
    }

    @PostMapping("/model/retrain")
    public ResponseEntity<?> triggerRetrain() {
        try {
            List<Article> overrides = articleRepository.findAll().stream()
                .filter(a -> a.getVerdictOverride() != null)
                .collect(Collectors.toList());

            if (overrides.size() < 2) {
                return ResponseEntity.badRequest().body(java.util.Map.of(
                    "status", "error",
                    "message", "Insufficient audit data. At least 2 manual overrides are required to recalibrate the model."
                ));
            }

            // 1. Export to temporary CSV
            // Resolve project root by moving up from backend if needed
            java.nio.file.Path currentPath = java.nio.file.Paths.get(System.getProperty("user.dir")).toAbsolutePath();
            java.nio.file.Path root = currentPath.getFileName().toString().equals("backend") ? currentPath.getParent() : currentPath;
            
            java.nio.file.Path dataDir = root.resolve("data");
            java.nio.file.Files.createDirectories(dataDir);
            java.nio.file.Path csvPath = dataDir.resolve("calibration_data.csv");
            
            try (java.io.BufferedWriter writer = java.nio.file.Files.newBufferedWriter(csvPath)) {
                writer.write("raw_score,label\n");
                for (Article a : overrides) {
                    writer.write(String.format("%.6f,%.1f\n", a.getOverallCredibility(), a.getVerdictOverride()));
                }
            }

            // 2. Execute Python recalibration script
            // Use the .venv python if it exists in root, otherwise fallback to system python
            java.nio.file.Path venvPath = root.resolve(".venv").resolve("Scripts").resolve("python.exe");
            String pythonCmd = java.nio.file.Files.exists(venvPath) ? venvPath.toString() : "python";
            
            java.nio.file.Path scriptPath = root.resolve("ml-service").resolve("scripts").resolve("recalibrate.py");
            java.nio.file.Path paramsPath = root.resolve("ml-service").resolve("resources").resolve("calibration_params.json");

            ProcessBuilder pb = new ProcessBuilder(
                pythonCmd, 
                scriptPath.toString(), 
                csvPath.toString(), 
                paramsPath.toString()
            );
            pb.redirectErrorStream(true);
            Process process = pb.start();
            
            // Wait with timeout for safety
            boolean finished = process.waitFor(30, java.util.concurrent.TimeUnit.SECONDS);
            if (!finished) {
                process.destroy();
                return ResponseEntity.status(500).body(java.util.Map.of("error", "Recalibration script timed out."));
            }

            if (process.exitValue() != 0) {
                return ResponseEntity.status(500).body(java.util.Map.of("error", "Recalibration script failed. Exit code: " + process.exitValue()));
            }

            // 3. Notify ML Service to reload
            try {
                new org.springframework.web.client.RestTemplate().postForEntity("http://localhost:8000/internal/recalibrate", null, String.class);
            } catch (Exception e) {
                return ResponseEntity.ok(java.util.Map.of(
                    "status", "warning", 
                    "message", "Model recalibrated, but failed to notify ML Service to reload. Changes will apply on next service restart."
                ));
            }

            return ResponseEntity.ok(java.util.Map.of(
                "status", "success", 
                "message", "Model successfully recalibrated based on " + overrides.size() + " manual overrides.",
                "count", overrides.size()
            ));

        } catch (Exception e) {
            e.printStackTrace();
            return ResponseEntity.status(500).body(java.util.Map.of(
                "error", e.getMessage() != null ? e.getMessage() : "Exception during retraining orchestration",
                "type", e.getClass().getSimpleName()
            ));
        }
    }
}

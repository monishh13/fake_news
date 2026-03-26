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

@RestController
@RequestMapping("/api/admin")
@CrossOrigin(originPatterns = {"http://localhost:5173", "http://localhost", "chrome-extension://*"})
public class AdminController {

    private final ArticleRepository articleRepository;
    private final ClaimRepository claimRepository;

    public AdminController(ArticleRepository articleRepository, ClaimRepository claimRepository) {
        this.articleRepository = articleRepository;
        this.claimRepository = claimRepository;
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
    public ResponseEntity<Article> overrideArticle(
            @PathVariable Long id,
            @RequestBody java.util.Map<String, Object> updates) {
        return articleRepository.findById(id).map(article -> {
            if (updates.containsKey("verdictOverride")) article.setVerdictOverride((Double) updates.get("verdictOverride"));
            if (updates.containsKey("adminNotes")) article.setAdminNotes((String) updates.get("adminNotes"));
            if (updates.containsKey("severity")) article.setSeverity((String) updates.get("severity"));
            return ResponseEntity.ok(articleRepository.save(article));
        }).orElse(ResponseEntity.notFound().build());
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
    public ResponseEntity<String> purgeArticles(@RequestParam int days) {
        java.time.LocalDateTime cutoff = java.time.LocalDateTime.now().minusDays(days);
        articleRepository.purgeOldArticles(cutoff);
        return ResponseEntity.ok("Purged articles older than " + days + " days.");
    }

    @PostMapping("/model/retrain")
    public ResponseEntity<java.util.Map<String, String>> triggerRetrain() {
        // Mock retraining
        return ResponseEntity.ok(java.util.Map.of(
            "status", "OPTIMIZING",
            "eta", "2 mins",
            "message", "Model retraining pipeline initiated using human-overridden corrections."
        ));
    }
}

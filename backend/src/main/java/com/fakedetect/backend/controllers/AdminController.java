package com.fakedetect.backend.controllers;

import com.fakedetect.backend.models.AdminStatsResponse;
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
}

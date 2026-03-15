package com.fakedetect.backend.controllers;

import com.fakedetect.backend.models.Article;
import com.fakedetect.backend.models.Claim;
import com.fakedetect.backend.repositories.ArticleRepository;
import com.fakedetect.backend.services.MlServiceClient;
import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import jakarta.transaction.Transactional;

import java.io.IOException;
import java.util.*;

@RestController
@RequestMapping("/api/detection")
@CrossOrigin(origins = "*")
public class DetectionController {

    private final MlServiceClient mlServiceClient;
    private final ArticleRepository articleRepository;

    public DetectionController(MlServiceClient mlServiceClient, ArticleRepository articleRepository) {
        this.mlServiceClient = mlServiceClient;
        this.articleRepository = articleRepository;
    }

    @PostMapping("/text")
    @Transactional
    public ResponseEntity<Article> analyzeText(@RequestParam("text") String text) {
        JsonNode result = mlServiceClient.analyzeText(text);
        return ResponseEntity.ok(saveResult(result));
    }

    @PostMapping("/file")
    @Transactional
    public ResponseEntity<Article> analyzeFile(@RequestParam("file") MultipartFile file) {
        System.out.println("[DetectionController] received file upload: " + file.getOriginalFilename() + " (" + file.getContentType() + ")");
        try {
            JsonNode result = mlServiceClient.analyzeFile(file);
            return ResponseEntity.ok(saveResult(result));
        } catch (IOException e) {
            e.printStackTrace();
            return ResponseEntity.internalServerError().build();
        }
    }

    @PostMapping("/extract-url")
    public ResponseEntity<JsonNode> extractUrl(@RequestParam("url") String url) {
        try {
            return ResponseEntity.ok(mlServiceClient.extractUrl(url));
        } catch (Exception e) {
            return ResponseEntity.internalServerError().build();
        }
    }

    @GetMapping("/history")
    public ResponseEntity<List<Article>> getHistory() {
        return ResponseEntity.ok(articleRepository.findAllByOrderByCreatedAtDesc());
    }

    @GetMapping("/{id}")
    public ResponseEntity<Article> getReport(@PathVariable Long id) {
        return articleRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    private Article saveResult(JsonNode result) {
        Article article = new Article();
        article.setContent(result.get("article_text").asText());
        article.setOverallCredibility(result.get("overall_credibility").asDouble());
        
        List<Claim> claimsList = new ArrayList<>();
        JsonNode claimsNode = result.get("claims");
        if (claimsNode != null && claimsNode.isArray()) {
            for (JsonNode claimNode : claimsNode) {
                Claim claim = new Claim();
                claim.setClaimText(claimNode.get("claim_text").asText());
                claim.setCredibilityScore(claimNode.get("credibility_score").asDouble());
                claim.setStatus(claimNode.get("status").asText());
                
                // Add evidence
                List<String> evidence = new ArrayList<>();
                JsonNode evidenceNode = claimNode.get("evidence_snippets");
                if (evidenceNode != null && evidenceNode.isArray()) {
                    evidenceNode.forEach(e -> evidence.add(e.asText()));
                }
                claim.setEvidenceSnippets(evidence);
                
                // Add SHAP mapping
                Map<String, Double> shap = new HashMap<>();
                JsonNode shapNode = claimNode.get("shap_explanation");
                if (shapNode != null && shapNode.isObject()) {
                    Iterator<Map.Entry<String, JsonNode>> fields = shapNode.fields();
                    while (fields.hasNext()) {
                        Map.Entry<String, JsonNode> field = fields.next();
                        shap.put(field.getKey(), field.getValue().asDouble());
                    }
                }
                claim.setShapExplanation(shap);
                claim.setArticle(article);
                claimsList.add(claim);
            }
        }
        article.setClaims(claimsList);
        return articleRepository.save(article);
    }
}

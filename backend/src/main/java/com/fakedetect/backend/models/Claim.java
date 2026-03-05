package com.fakedetect.backend.models;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.List;
import java.util.Map;

@Entity
@Data
@NoArgsConstructor
public class Claim {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(columnDefinition = "TEXT")
    private String claimText;

    private Double credibilityScore;

    private String status; // SUPPORTED, CONTRADICTED, INSUFFICIENT_EVIDENCE

    @ElementCollection
    @CollectionTable(name = "claim_evidence", joinColumns = @JoinColumn(name = "claim_id"))
    @Column(name = "evidence_snippet", columnDefinition = "TEXT")
    private List<String> evidenceSnippets;

    @ElementCollection
    @CollectionTable(name = "claim_shap", joinColumns = @JoinColumn(name = "claim_id"))
    @MapKeyColumn(name = "word")
    @Column(name = "impact_score")
    private Map<String, Double> shapExplanation;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "article_id")
    @com.fasterxml.jackson.annotation.JsonIgnore
    private Article article;
}

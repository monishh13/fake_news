package com.fakedetect.backend.models;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class AdminStatsResponse {
    private Integer totalArticles;
    private Integer totalClaims;
    private Double averageCredibilityScore;
    private Integer fakeCount;
    private Integer realCount;
}

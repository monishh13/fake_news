package com.fakedetect.backend.models;

import lombok.AllArgsConstructor;
import lombok.Data;
import java.util.Map;

@Data
@AllArgsConstructor
public class AdvancedStatsResponse {
    private Map<String, Long> confidenceDistribution;
    private Map<String, Long> verdictDistribution; // Real vs Fake
    private Map<String, Long> dailyAnalysisVolume; // Last 7 days
    private Map<String, Long> sourceAnalysis;
    private Double averageLatencyMs;
    private Long errorRatePercentage;
}

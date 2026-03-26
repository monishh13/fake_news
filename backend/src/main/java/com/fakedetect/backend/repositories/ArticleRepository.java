package com.fakedetect.backend.repositories;

import com.fakedetect.backend.models.Article;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ArticleRepository extends JpaRepository<Article, Long> {
    List<Article> findAllByOrderByCreatedAtDesc();

    @Query("SELECT AVG(a.overallCredibility) FROM Article a")
    Double getAverageCredibilityScore();

    @Query("SELECT COUNT(a) FROM Article a WHERE a.overallCredibility < 0.5")
    long countFakeArticles();

    @Query("SELECT COUNT(a) FROM Article a WHERE a.overallCredibility >= 0.5")
    long countRealArticles();
}

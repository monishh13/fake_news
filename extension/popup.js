document.addEventListener('DOMContentLoaded', () => {
    const appDiv = document.getElementById('app');

    // Check if there is pending text to analyze
    chrome.storage.local.get(['aiveraPendingText'], (result) => {
        const text = result.aiveraPendingText;
        if (text) {
            // Clear it so it doesn't run again on next open
            chrome.storage.local.remove(['aiveraPendingText']);
            analyzeText(text);
        }
    });

    async function analyzeText(text) {
        appDiv.innerHTML = `<div class="loader">Analyzing custom ML pipeline...</div>`;
        
        try {
            const formData = new URLSearchParams();
            formData.append('text', text);

            const res = await fetch('http://localhost:8081/api/detection/text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });

            if (!res.ok) throw new Error('API Error');
            const data = await res.json();
            renderResults(data);
        } catch (err) {
            appDiv.innerHTML = `
                <div class="empty-state" style="color: #f43f5e;">
                    🚨 Failed to reach AIVera local backend. Is the Spring Boot gateway running on port 8081?
                </div>
            `;
        }
    }

    function renderResults(data) {
        let html = `
            <div class="result-card" style="text-align: center;">
                <div style="font-size:12px; opacity:0.6; text-transform:uppercase;">Overall Credibility</div>
                <div class="score ${getScoreClass(data.overallCredibility)}">${Math.round(data.overallCredibility * 100)}%</div>
            </div>
            <h4 style="margin: 16px 0 8px 0; font-size: 12px; text-transform:uppercase; opacity:0.7">Extracted Claims</h4>
        `;

        if (data.claims && data.claims.length > 0) {
            data.claims.forEach(c => {
                const sColor = c.status.startsWith('SUPPORTED') ? 'background: rgba(16,185,129,0.2); color:#34d399' : 
                               c.status.startsWith('CONTRADICTED') ? 'background: rgba(244,63,94,0.2); color:#f43f5e' :
                               'background: rgba(251,191,36,0.2); color:#fbbf24';
                
                html += `
                    <div class="result-card">
                        <div class="claim">"${c.claimText}"</div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
                            <span class="badge" style="${sColor}">${c.status.replace('_', ' ')}</span>
                            <span class="${getScoreClass(c.credibilityScore)}" style="font-weight:bold">${Math.round(c.credibilityScore*100)}%</span>
                        </div>
                        
                        ${c.evidenceSnippets && c.evidenceSnippets.length > 0 ? `
                            <div class="evidence-section">
                                <div class="evidence-title">Supporting Evidence</div>
                                ${c.evidenceSnippets.slice(0, 2).map(snippet => {
                                    let badge = '';
                                    let text = snippet;
                                    if (snippet.startsWith('[Wikipedia]')) {
                                        badge = '<span class="source-badge source-wiki">WIKI</span>';
                                        text = snippet.replace('[Wikipedia] ', '');
                                    } else if (snippet.startsWith('[Google Fact Check]')) {
                                        badge = '<span class="source-badge source-google">FACT CHECK</span>';
                                        text = snippet.replace('[Google Fact Check] ', '');
                                    } else if (snippet.startsWith('[NewsAPI')) {
                                        badge = '<span class="source-badge source-news">NEWS</span>';
                                        text = snippet.replace(/\[NewsAPI - .*?\] /, '');
                                    }
                                    return `<div class="evidence-item">${badge}${text}</div>`;
                                }).join('')}
                            </div>
                        ` : ''}
                    </div>
                `;
            });
        }

        html += `<button class="btn" style="margin-top:20px" id="open-dashboard">Open Full Dashboard</button>`;
        appDiv.innerHTML = html;

        const dashboardBtn = document.getElementById('open-dashboard');
        if (dashboardBtn) {
            dashboardBtn.addEventListener('click', () => {
                if (data && data.id) {
                    // Save the full result so the content bridge can pass it to the page,
                    // bypassing any database lookup (solves H2 in-memory reset issue).
                    chrome.storage.local.set({ aivera_pending_report: data }, () => {
                        chrome.tabs.create({ url: `http://localhost:5173/?report=${data.id}` });
                    });
                } else {
                    alert("Analysis report ID not found. The report may not have been saved to the database.");
                }
            });
        }

    }

    function getScoreClass(score) {
        if (score >= 0.7) return 'high';
        if (score >= 0.4) return 'med';
        return 'low';
    }
});

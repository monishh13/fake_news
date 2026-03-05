import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { UploadCloud, FileText, AlertTriangle, Activity, Search, History, Info, Sun, Moon, Shield } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';

function App() {
    const [text, setText] = useState('');
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [activePage, setActivePage] = useState('analyze');
    const [theme, setTheme] = useState('dark');
    const [history, setHistory] = useState([]);

    const fileInputRef = useRef(null);
    const API_BASE = 'http://localhost:8080/api/detection';

    // Load history from local storage on mount
    useEffect(() => {
        const saved = localStorage.getItem('aivera_history');
        if (saved) {
            try { setHistory(JSON.parse(saved)); } catch (e) { }
        }
    }, []);

    // Save history to local storage whenever it changes
    useEffect(() => {
        localStorage.setItem('aivera_history', JSON.stringify(history));
    }, [history]);

    const toggleTheme = () => {
        const next = theme === 'dark' ? 'light' : 'dark';
        setTheme(next);
        document.documentElement.setAttribute('data-theme', next);
    };

    const addToHistory = (data, type, query) => {
        const newRecord = {
            ...data,
            timestamp: new Date().toISOString(),
            type,
            query: typeof query === 'string' ? (query.length > 80 ? query.substring(0, 80) + '...' : query) : 'Document Analysis'
        };
        setHistory(prev => [newRecord, ...prev].slice(0, 5)); // Keep last 5
    };

    const handleTextSubmit = async () => {
        if (!text.trim()) { setError('Please enter some text to analyze.'); return; }
        setLoading(true); setError(''); setResult(null);
        try {
            const formData = new FormData();
            formData.append('text', text);
            const { data } = await axios.post(`${API_BASE}/text`, formData);
            setResult(data);
            addToHistory(data, 'text', text);
        } catch (err) {
            setError('Failed to analyze text. Ensure backend services are running.');
        } finally { setLoading(false); }
    };

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) setFile(e.target.files[0]);
    };

    const handleFileSubmit = async () => {
        if (!file) { setError('Please select a file to upload.'); return; }
        setLoading(true); setError(''); setResult(null);
        try {
            const formData = new FormData();
            formData.append('file', file);
            const { data } = await axios.post(`${API_BASE}/file`, formData);
            setResult(data);
            addToHistory(data, 'file', file.name);
        } catch (err) {
            setError('Failed to analyze file. Ensure backend services are running.');
        } finally { setLoading(false); }
    };

    const getScoreColor = (score) => {
        if (score >= 0.7) return 'var(--success)';
        if (score >= 0.4) return 'var(--warning)';
        return 'var(--danger)';
    };

    const formatShapData = (shapDict) => {
        if (!shapDict) return [];
        return Object.entries(shapDict)
            .map(([word, score]) => ({ word, score }))
            .sort((a, b) => Math.abs(b.score) - Math.abs(a.score))
            .slice(0, 8);
    };

    const navItems = [
        { id: 'analyze', label: 'Analyze News', icon: Search },
        { id: 'history', label: 'History', icon: History },
        { id: 'about', label: 'About', icon: Info },
    ];

    const renderAnalyze = () => (
        <>
            {error && (
                <div className="error-msg">
                    <AlertTriangle size={18} style={{ marginRight: '10px', flexShrink: 0 }} />{error}
                </div>
            )}

            <div className="upload-section">
                <div className="card">
                    <div className="input-group">
                        <label><FileText size={16} /> Text Input</label>
                        <textarea
                            placeholder="Paste news article or social media post here..."
                            value={text}
                            onChange={e => setText(e.target.value)}
                        />
                    </div>
                    <button className="btn btn-primary" onClick={handleTextSubmit} disabled={loading}>
                        {loading ? 'Analyzing...' : 'Analyze Text'}
                    </button>
                </div>

                <div className="card">
                    <div className="input-group" style={{ height: '100%' }}>
                        <label><UploadCloud size={16} /> Upload File</label>
                        <div
                            className="file-drop-area"
                            onClick={() => fileInputRef.current.click()}
                            onDragOver={e => e.preventDefault()}
                            onDrop={e => { e.preventDefault(); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); }}
                        >
                            <UploadCloud size={40} color="var(--accent)" style={{ marginBottom: '0.75rem', opacity: 0.7 }} />
                            {file ? (
                                <span style={{ color: 'var(--success)', fontWeight: 600 }}>{file.name}</span>
                            ) : (
                                <>
                                    <span style={{ fontWeight: 500 }}>Drag & Drop or Click</span>
                                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>PDF, PNG, JPG, JPEG</span>
                                </>
                            )}
                            <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".pdf,image/*" />
                        </div>
                        <button className="btn btn-primary" onClick={handleFileSubmit} disabled={loading || !file} style={{ marginTop: 'auto' }}>
                            {loading ? 'Analyzing...' : 'Analyze File'}
                        </button>
                    </div>
                </div>
            </div>

            {loading && <div className="loader"></div>}

            {result && (
                <div className="results-section card">
                    <div className="score-container">
                        <div>
                            <h2 style={{ fontSize: '1.5rem', marginBottom: '0.4rem' }}>Analysis Results</h2>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                                Extracted and verified {result.claims?.length || 0} declarative claims.
                            </p>
                        </div>
                        <div className="score-circle" style={{ borderColor: getScoreColor(result.overallCredibility) }}>
                            <span>{Math.round(result.overallCredibility * 100)}%</span>
                            <span className="score-label">Credibility</span>
                        </div>
                    </div>

                    <div className="claims-list">
                        <h3><Activity size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} />Claim Level Breakdown</h3>
                        {result.claims?.map((claim, idx) => (
                            <div key={idx} className="claim-card">
                                <div className="claim-header">
                                    <div className="claim-text">"{claim.claimText}"</div>
                                    <div className={`badge ${claim.status.toLowerCase().split('_')[0]}`}>
                                        {claim.status.replace('_', ' ')}
                                    </div>
                                </div>

                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: '0.75rem 0', fontWeight: 'bold', fontSize: '0.85rem', color: getScoreColor(claim.credibilityScore) }}>
                                    <div style={{ flex: 1, height: '6px', background: 'var(--border)', borderRadius: '3px', overflow: 'hidden' }}>
                                        <div style={{ height: '100%', width: `${claim.credibilityScore * 100}%`, background: getScoreColor(claim.credibilityScore), transition: 'width 1s ease' }}></div>
                                    </div>
                                    <span>{Math.round(claim.credibilityScore * 100)}% Trusted</span>
                                </div>

                                <div className="claim-details">
                                    <div>
                                        <h4>Impact Analysis (SHAP)</h4>
                                        <div style={{ height: '200px' }}>
                                            <ResponsiveContainer width="100%" height="100%">
                                                <BarChart data={formatShapData(claim.shapExplanation)} layout="vertical" margin={{ top: 5, right: 20, left: 40, bottom: 5 }}>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                                                    <XAxis type="number" hide />
                                                    <YAxis dataKey="word" type="category" stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} />
                                                    <Tooltip cursor={{ fill: 'var(--accent-glow)' }} contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)' }} />
                                                    <Bar dataKey="score" radius={[0, 4, 4, 0]} barSize={10}>
                                                        {formatShapData(claim.shapExplanation).map((entry, index) => (
                                                            <Cell key={`cell-${index}`} fill={entry.score > 0 ? 'var(--success)' : 'var(--danger)'} />
                                                        ))}
                                                    </Bar>
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>

                                    <div>
                                        <h4>Retrieved Evidence</h4>
                                        {claim.evidenceSnippets?.length > 0 ? (
                                            <ul className="evidence-list">
                                                {claim.evidenceSnippets.map((ev, i) => (
                                                    <li key={i}>{ev}</li>
                                                ))}
                                            </ul>
                                        ) : (
                                            <p style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.9rem' }}>No relevant verified facts found for this claim.</p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </>
    );

    const renderHistory = () => (
        <div className="card">
            <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>Recent Analyses</h2>
            {history.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem 0' }}>No recent analyses found.</p>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {history.map((record, idx) => (
                        <div
                            key={idx}
                            className="claim-card"
                            style={{ cursor: 'pointer', background: 'var(--bg-card)' }}
                            onClick={() => { setResult(record); setActivePage('analyze'); }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                                <span className="badge" style={{ background: 'var(--bg-input)' }}>{record.type.toUpperCase()}</span>
                                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{new Date(record.timestamp).toLocaleString()}</span>
                            </div>
                            <h4 style={{ marginBottom: '1rem', fontStyle: 'italic', fontWeight: 500, color: 'var(--text-primary)' }}>"{record.query}"</h4>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: getScoreColor(record.overallCredibility) }}></div>
                                <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                                    {Math.round(record.overallCredibility * 100)}% Credibility · {record.claims?.length || 0} Claims
                                </span>
                                <span style={{ marginLeft: 'auto', fontSize: '0.8rem', color: 'var(--accent)' }}>View Results →</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );

    const renderAbout = () => (
        <div className="card">
            <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>About AIVera</h2>
            <div style={{ color: 'var(--text-secondary)', lineHeight: '1.7', fontSize: '1rem' }}>
                <p style={{ marginBottom: '1rem' }}>
                    <strong>AIVera</strong> is an Explainable Fake News Detection System designed to analyze news articles and social media posts at a granular level.
                </p>
                <p style={{ marginBottom: '1rem' }}>
                    Unlike traditional binary classification systems that evaluate whole articles as completely true or false, AIVera segments content into individual verifiable claims. It evaluates the credibility of each claim using a fine-tuned DistilBERT transformer model and provides <strong>transparent AI reasoning</strong> using SHAP (SHapley Additive exPlanations) to highlight exactly which words influenced its decision.
                </p>
                <p style={{ marginBottom: '2rem' }}>
                    Coupled with a retrieval-augmented generation approach, AIVera fetches real-world evidence to support or contradict claims, bringing robust fact-checking out of the black box.
                </p>
                <div style={{ padding: '1.5rem', background: 'var(--bg-input)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <h4 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>System Information</h4>
                    <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        <li><strong>Version:</strong> 1.0.0</li>
                        <li><strong>Frontend:</strong> React, Vite, Recharts</li>
                        <li><strong>Backend:</strong> Spring Boot, Java 17, H2 Database</li>
                        <li><strong>Machine Learning:</strong> Python, FastAPI, HuggingFace Transformers</li>
                        <li><strong>Model:</strong> DistilBERT (Fine-tuned on LIAR dataset)</li>
                    </ul>
                </div>
            </div>
        </div>
    );

    const renderContent = () => {
        switch (activePage) {
            case 'history': return renderHistory();
            case 'about': return renderAbout();
            case 'analyze':
            default: return renderAnalyze();
        }
    };

    return (
        <div className="layout">
            {/* Sidebar */}
            <aside className="sidebar">
                <div className="sidebar-logo">
                    <div className="logo-icon"><Shield size={18} /></div>
                    <h2>AIVera</h2>
                </div>
                <nav className="sidebar-nav">
                    {navItems.map(item => (
                        <button
                            key={item.id}
                            className={`nav-item ${activePage === item.id ? 'active' : ''}`}
                            onClick={() => setActivePage(item.id)}
                        >
                            <item.icon size={18} />
                            {item.label}
                        </button>
                    ))}
                </nav>
                <div className="sidebar-footer">
                    v1.0.0 · Explainable AI
                </div>
            </aside>

            {/* Topbar */}
            <div className="topbar">
                <span className="topbar-title">
                    {navItems.find(n => n.id === activePage)?.label || 'AIVera'}
                </span>
                <div className="topbar-actions">
                    <button className="theme-toggle" onClick={toggleTheme} title="Toggle theme">
                        {theme === 'dark' ? <Sun size={0} /> : <Moon size={0} />}
                    </button>
                    <div className="user-avatar">M</div>
                </div>
            </div>

            {/* Main Content */}
            <main className="main-content">
                {renderContent()}

                <footer className="app-footer">
                    AIVera — AI-powered credibility analysis. Results are generated by machine learning models and should not be considered definitive judgments.
                </footer>
            </main>
        </div>
    );
}

export default App;

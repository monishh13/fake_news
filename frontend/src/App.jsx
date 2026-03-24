import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { 
    UploadCloud, FileText, AlertTriangle, Activity, Search, 
    History, Info, Sun, Moon, Shield, Copy, Share2, Twitter, Check, Download 
} from 'lucide-react';
import html2pdf from 'html2pdf.js';
import { VerdictBadge, ZoneScoreBar, ContextualNote, ClaimHeatmap, SummaryStrip, InfluenceBreakdown, WordExplanationPanel, EvidenceCard, ClaimCard } from './ui_components';

function cn(...inputs) { return twMerge(clsx(inputs)); }

// -- Animation Variants --
const containerVariants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } }
};
const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
};

// -- Glass Card Component --
const GlassCard = ({ children, className, ...props }) => (
    <motion.div 
        className={cn("bg-[var(--bg-card)] backdrop-blur-xl border border-[var(--border)] rounded-2xl shadow-xl overflow-hidden", className)}
        {...props}
    >
        {children}
    </motion.div>
);

// -- Trust Meter Component --
const TrustMeter = ({ score }) => {
    const percentage = Math.round(score * 100);
    const radius = 40;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;
    const colorClass = percentage >= 70 ? 'text-emerald-400' : (percentage >= 40 ? 'text-amber-400' : 'text-rose-500');

    return (
        <div className="relative flex items-center justify-center w-32 h-32">
            {/* Background Circle */}
            <svg className="w-full h-full transform -rotate-90">
                <circle cx="64" cy="64" r={radius} stroke="currentColor" strokeWidth="8" fill="transparent" className="text-gray-700/50" />
                <motion.circle 
                    cx="64" cy="64" r={radius} 
                    stroke="currentColor" strokeWidth="8" fill="transparent" 
                    className={colorClass}
                    strokeDasharray={circumference}
                    initial={{ strokeDashoffset: circumference }}
                    animate={{ strokeDashoffset }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold tracking-tighter text-[var(--text-primary)]">{percentage}%</span>
                <span className="text-[10px] font-semibold tracking-widest text-muted-foreground uppercase">Trust</span>
            </div>
        </div>
    );
};



// -- Clipboard Button Component --
const ClipboardButton = ({ text }) => {
    const [copied, setCopied] = useState(false);
    const handleCopy = () => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };
    return (
        <button onClick={handleCopy} aria-label="Copy to clipboard" className="p-1.5 text-muted-foreground hover:text-primary transition-colors hover:bg-[var(--bg-input)] rounded-md" title="Copy to clipboard">
            {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
        </button>
    );
};

export default function App() {
    const [text, setText] = useState('');
    const [file, setFile] = useState(null);
    const [url, setUrl] = useState('');
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [activePage, setActivePage] = useState('analyze');
    const [theme, setTheme] = useState('dark');
    const [history, setHistory] = useState([]);
    
    // For sharing feature
    const [shareCopied, setShareCopied] = useState(false);

    const fileInputRef = useRef(null);
    const API_BASE = 'http://localhost:8081/api/detection';

    // On Mount
    useEffect(() => {
        // Load history from backend, fallback to localStorage
        const loadHistory = async () => {
            try {
                const { data } = await axios.get(`${API_BASE}/history`);
                setHistory(data.slice(0, 20));
            } catch (err) {
                const saved = localStorage.getItem('aivera_history');
                if (saved) { try { setHistory(JSON.parse(saved)); } catch (e) { } }
            }
        };
        loadHistory();

        const urlParams = new URLSearchParams(window.location.search);
        const reportId = urlParams.get('report');

        if (reportId) {
            // Listen for the full result payload from the content bridge.
            // When React sends AIVERA_READY, the bridge replies with AIVERA_REPORT.
            // This is race-free because the bridge waits for our signal.
            const onMessage = (event) => {
                if (event.source === window && event.data && event.data.type === 'AIVERA_REPORT') {
                    window.removeEventListener('message', onMessage);
                    setError('');          // clear any API error that may have raced
                    setResult(event.data.data);
                    addToHistory(event.data.data, 'extension', event.data.data.content || 'Extension Analysis');
                    window.history.replaceState({}, '', window.location.pathname);
                }
            };
            window.addEventListener('message', onMessage);

            // Signal the content bridge that React is ready
            window.postMessage({ type: 'AIVERA_READY' }, '*');

            // Also kick off the API fetch as a fallback (works if DB is intact)
            fetchReport(reportId);

            return () => window.removeEventListener('message', onMessage);
        }
    }, []);


    const [isFetchingReport, setIsFetchingReport] = useState(false);
    const fetchReport = async (id) => {
        setIsFetchingReport(true); setError(''); setResult(null); setActivePage('analyze');
        try {
            const { data } = await axios.get(`${API_BASE}/${id}`);
            setResult(data);
        } catch (err) {
            setError("Couldn't find that report. It may have been deleted, the ID is invalid, or the backend was restarted (clearing in-memory data).");
        } finally {
            setIsFetchingReport(false);
        }
    };

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
        const updated = [newRecord, ...history].filter((v,i,a)=>a.findIndex(t=>(t.id === v.id))===i).slice(0, 10);
        setHistory(updated);
        localStorage.setItem('aivera_history', JSON.stringify(updated));
    };

    const analyzeMutation = useMutation({
        mutationFn: async ({ type, payload }) => {
            if (type === 'text') {
                const formData = new FormData();
                formData.append('text', payload);
                return axios.post(`${API_BASE}/text`, formData).then(res => res.data);
            } else if (type === 'file') {
                const formData = new FormData();
                formData.append('file', payload);
                return axios.post(`${API_BASE}/file`, formData).then(res => res.data);
            } else if (type === 'url') {
                const { data: extracted } = await axios.post(`${API_BASE}/extract-url?url=${encodeURIComponent(payload)}`);
                if (!extracted.text) throw new Error("Could not extract text from this URL.");
                
                setText(extracted.title ? `${extracted.title}\n\n${extracted.text}` : extracted.text);
                
                const formData = new FormData();
                formData.append('text', extracted.title ? `${extracted.title}\n\n${extracted.text}` : extracted.text);
                return axios.post(`${API_BASE}/text`, formData).then(res => res.data);
            }
        },
        onSuccess: (data, variables) => {
            setResult(data);
            let queryVal = variables.type === 'file' ? variables.payload.name : variables.payload;
            addToHistory(data, variables.type, queryVal);
            window.history.pushState({}, '', window.location.pathname);
        },
        onError: (err) => {
            setError('Analysis failed: ' + (err.response?.data?.message || err.message));
        }
    });

    const loading = analyzeMutation.isPending || isFetchingReport;

    const handleTextSubmit = () => {
        if (!text.trim()) { setError('Please enter some text to analyze.'); return; }
        setError(''); setResult(null);
        analyzeMutation.mutate({ type: 'text', payload: text });
    };

    const handleFileSubmit = () => {
        if (!file) { setError('Please select a file to upload.'); return; }
        setError(''); setResult(null);
        analyzeMutation.mutate({ type: 'file', payload: file });
    };

    const handleUrlSubmit = () => {
        if (!url.trim()) { setError('Please enter a valid URL.'); return; }
        setError(''); setResult(null);
        analyzeMutation.mutate({ type: 'url', payload: url });
    };

    const getScoreColor = (score) => {
        if (score >= 0.7) return '#34d399'; // emerald-400
        if (score >= 0.4) return '#fbbf24'; // amber-400
        return '#f43f5e'; // rose-500
    };

    const getCredibilityLabel = (score) => {
        if (score >= 0.7) return 'Real / Authentic';
        if (score >= 0.4) return 'Mixed / Uncertain';
        return 'Fake / Misleading';
    };

    const handleDownloadPDF = () => {
        const element = document.getElementById('report-content');
        if (!element) return;
        
        // Apply printing class for high-quality capture
        element.classList.add('printing-pdf');
        
        const opt = {
            margin:       0.5,
            filename:     `aivera_report_${result?.id || 'new'}.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  { 
                scale: 3, 
                useCORS: true,
                logging: false,
                letterRendering: true
            },
            jsPDF:        { unit: 'in', format: 'a4', orientation: 'portrait' }
        };

        // Use promise to ensure class is removed after capture
        html2pdf().set(opt).from(element).save().then(() => {
            element.classList.remove('printing-pdf');
        }).catch(err => {
            console.error("PDF generation failed:", err);
            element.classList.remove('printing-pdf');
        });
    };



    const shareUrl = result?.id ? `${window.location.origin}${window.location.pathname}?report=${result.id}` : '';
    const shareText = result ? `Check out this fact-check report from AIVera: Credibility ${Math.round(result.overallCredibility * 100)}%` : '';

    const handleShareCopy = () => {
        navigator.clipboard.writeText(shareUrl);
        setShareCopied(true); setTimeout(() => setShareCopied(false), 2000);
    };

    const renderAnalyze = () => (
        <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-6 max-w-5xl mx-auto w-full">
            <AnimatePresence>
                {error && (
                    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="p-4 bg-red-500/10 border border-red-500/20 text-red-500 rounded-xl flex items-center gap-3">
                        <AlertTriangle size={20} className="flex-shrink-0" />
                        <span className="text-sm font-medium">{error}</span>
                    </motion.div>
                )}
            </AnimatePresence>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 relative z-10">
                <GlassCard className="p-6 flex flex-col gap-4">
                    <div className="flex items-center gap-2 text-sm font-semibold tracking-wider text-muted-foreground uppercase">
                        <FileText size={16} /> Text Input
                    </div>
                    <textarea
                        className="w-full flex-1 min-h-[160px] p-4 rounded-xl bg-[var(--bg-input)] border border-[var(--border)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all resize-none"
                        placeholder="Paste news article or social media post here..."
                        value={text}
                        onChange={e => setText(e.target.value)}
                    />
                    <button 
                        onClick={handleTextSubmit} disabled={loading}
                        className="w-full py-3 px-4 rounded-xl bg-accent hover:bg-accent/90 text-[var(--text-primary)] font-medium shadow-[0_0_20px_rgba(108,92,231,0.3)] transition-all active:scale-[0.98] disabled:opacity-50 flex justify-center items-center gap-2"
                    >
                        {loading ? <div className="w-5 h-5 rounded-full border-2 border-white/30 border-t-white animate-spin" /> : 'Analyze Text'}
                    </button>
                </GlassCard>

                <GlassCard className="p-6 flex flex-col gap-4">
                    <div className="flex items-center gap-2 text-sm font-semibold tracking-wider text-muted-foreground uppercase">
                        <Search size={16} /> URL Link
                    </div>
                    <div className="w-full flex-1 min-h-[160px] rounded-xl flex flex-col justify-center text-center transition-all group">
                        <input 
                            type="url"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            placeholder="https://example.com/news/..."
                            className="w-full p-4 rounded-xl bg-[var(--bg-input)] border border-[var(--border)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all"
                        />
                        <div className="text-xs text-muted-foreground mt-4 leading-relaxed">
                            AIVera will attempt to automatically extract the main article content from the given webpage.
                        </div>
                    </div>
                    <button 
                        onClick={handleUrlSubmit} disabled={loading || !url}
                        className="w-full py-3 px-4 rounded-xl bg-[var(--bg-input)] hover:bg-white/20 border border-[var(--border)] text-[var(--text-primary)] font-medium transition-all active:scale-[0.98] disabled:opacity-50 flex justify-center items-center gap-2"
                    >
                        {loading ? <div className="w-5 h-5 rounded-full border-2 border-white/30 border-t-white animate-spin" /> : 'Analyze URL'}
                    </button>
                </GlassCard>

                <GlassCard className="p-6 flex flex-col gap-4">
                    <div className="flex items-center gap-2 text-sm font-semibold tracking-wider text-muted-foreground uppercase">
                        <UploadCloud size={16} /> Upload File
                    </div>
                    <div 
                        onClick={() => fileInputRef.current?.click()}
                        className="w-full flex-1 min-h-[160px] border-2 border-dashed border-[var(--border)] hover:border-accent/50 hover:bg-accent/5 rounded-xl flex flex-col items-center justify-center p-6 text-center cursor-pointer transition-all group"
                    >
                        <UploadCloud size={32} className="text-[var(--text-primary)]/20 group-hover:text-accent/70 transition-colors mb-2" />
                        {file ? (
                            <span className="text-emerald-400 font-medium truncate w-full px-2" title={file.name}>{file.name}</span>
                        ) : (
                            <>
                                <span className="font-semibold text-[var(--text-primary)]">Drag & Drop File</span>
                                <span className="text-xs text-muted-foreground mt-1">PDF, PNG, JPG</span>
                            </>
                        )}
                        <input type="file" ref={fileInputRef} onChange={e => {if(e.target.files[0]) setFile(e.target.files[0])}} className="hidden" accept=".pdf,image/*" />
                    </div>
                    <button 
                        onClick={handleFileSubmit} disabled={loading || !file}
                        className="w-full py-3 px-4 rounded-xl bg-[var(--bg-input)] hover:bg-white/20 border border-[var(--border)] text-[var(--text-primary)] font-medium transition-all active:scale-[0.98] disabled:opacity-50 flex justify-center items-center gap-2"
                    >
                        {loading ? <div className="w-5 h-5 rounded-full border-2 border-white/30 border-t-white animate-spin" /> : 'Analyze File'}
                    </button>
                </GlassCard>
            </div>

            {loading && (
                <div className="flex flex-col items-center justify-center py-20 opacity-80 animate-pulse text-accent">
                    <Shield size={64} className="mb-6 animate-bounce" />
                    <p className="text-lg font-medium tracking-wide">Processing through custom ML pipeline...</p>
                </div>
            )}

            {result && !loading && (
                <motion.div variants={itemVariants} className="space-y-8 mt-8" id="report-content">
                    {/* Hero Results Card */}
                    <GlassCard className="p-8 relative overflow-hidden flex flex-col md:flex-row items-center justify-between gap-8 border-accent/20">
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-400 via-amber-400 to-rose-500 opacity-50"></div>
                        
                        <div className="space-y-2 flex-1 text-center md:text-left">
                            <h2 className="text-3xl font-extrabold tracking-tight bg-gradient-to-br from-white to-white/60 bg-clip-text text-transparent">Analysis Complete</h2>
                            <p className="text-muted-foreground max-w-lg mx-auto md:mx-0">
                                Extracted and verified <span className="text-[var(--text-primary)] font-semibold">{result.claims?.length || 0} declarative claims</span> from the provided content using our custom DistilBERT ensemble.
                            </p>
                            
                            {/* Share Actions */}
                            <div className="flex flex-wrap items-center justify-center md:justify-start gap-3 mt-6" data-html2canvas-ignore="true">
                                <button onClick={handleDownloadPDF} className="flex items-center gap-2 px-4 py-2 bg-accent/10 hover:bg-accent/20 border border-accent/20 text-accent rounded-full text-sm font-medium transition-all">
                                    <Download size={16} /> Save PDF
                                </button>
                                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mx-2">Share</span>
                                <button onClick={handleShareCopy} className="flex items-center gap-2 px-4 py-2 bg-[var(--bg-input)] hover:bg-[var(--bg-input)] border border-[var(--border)] rounded-full text-sm font-medium transition-all">
                                    {shareCopied ? <Check size={16} className="text-emerald-400" /> : <Share2 size={16} />} 
                                    {shareCopied ? 'Copied Link!' : 'Copy Link'}
                                </button>
                                <a href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`} target="_blank" rel="noreferrer" className="flex items-center gap-2 px-4 py-2 bg-[#1DA1F2]/10 hover:bg-[#1DA1F2]/20 border border-[#1DA1F2]/20 text-[#1DA1F2] rounded-full text-sm font-medium transition-all">
                                    <Twitter size={16} /> Post on X
                                </a>
                            </div>
                        </div>

                        <div className="flex flex-col items-center">
                            <TrustMeter score={result.overallCredibility} />
                            <p className="mt-4 text-xs tracking-widest uppercase font-semibold text-muted-foreground mb-1">Overall Score</p>
                            <p className={cn("text-sm font-bold uppercase tracking-wide", result.overallCredibility >= 0.7 ? 'text-emerald-400' : (result.overallCredibility >= 0.4 ? 'text-amber-400' : 'text-rose-500'))}>
                                {getCredibilityLabel(result.overallCredibility)}
                            </p>
                        </div>
                    </GlassCard>

                    {/* Claims Breakdown */}
                    <div className="space-y-6">
                        <h3 className="flex items-center gap-3 text-xl font-semibold tracking-tight">
                            <Activity className="text-accent" /> Full Claim Breakdown
                        </h3>
                        
                        {result.claims?.map((claim, idx) => (
                            <ClaimCard key={idx} claim={claim} getScoreColor={getScoreColor} />
                        ))}
                    </div>
                </motion.div>
            )}
        </motion.div>
    );

    const renderHistory = () => (
        <motion.div variants={containerVariants} initial="hidden" animate="show" className="max-w-4xl mx-auto w-full space-y-6">
            <h2 className="text-2xl font-bold tracking-tight mb-8">Recent Analyses</h2>
            
            {history.length === 0 ? (
                <div className="text-center py-24 text-[var(--text-muted)]">
                    <History size={48} className="mx-auto mb-4" />
                    <p>Your analysis history is empty.</p>
                </div>
            ) : (
                <div className="space-y-4">
                    {history.map((record, idx) => (
                        <motion.div variants={itemVariants} key={record.id || idx}>
                            <GlassCard 
                                className="p-6 cursor-pointer hover:border-accent/50 hover:bg-[var(--bg-input)] transition-all group"
                                onClick={() => { setResult(record); setActivePage('analyze'); }}
                            >
                                <div className="flex justify-between items-center mb-4">
                                    <span className="uppercase tracking-widest text-[10px] font-bold px-3 py-1 bg-[var(--bg-input)] rounded-full border border-[var(--border)] text-[var(--text-secondary)]">
                                        {record.type || 'DBRECORD'}
                                    </span>
                                    <span className="text-xs text-muted-foreground">{new Date(record.timestamp || record.createdAt || new Date()).toLocaleString()}</span>
                                </div>
                                <h4 className="text-lg font-medium italic text-[var(--text-primary)] mb-4 line-clamp-2">"{record.query || (record.content ? record.content.substring(0, 80) + '...' : 'Saved Analysis')}"</h4>
                                <div className="flex items-center gap-4 text-sm font-semibold">
                                    <div className="w-3 h-3 rounded-full shadow-[0_0_10px_rgba(255,255,255,0.2)]" style={{ backgroundColor: getScoreColor(record.overallCredibility) }} />
                                    <span className="text-[var(--text-secondary)]">{Math.round(record.overallCredibility * 100)}% Credibility</span>
                                    <span className="text-[var(--text-muted)] font-normal">·</span>
                                    <span className="text-[var(--text-secondary)]">{record.claims?.length || 0} claims extracted</span>
                                    
                                    <span className="ml-auto text-accent opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                                        View Results <span className="text-lg leading-none">→</span>
                                    </span>
                                </div>
                            </GlassCard>
                        </motion.div>
                    ))}
                </div>
            )}
        </motion.div>
    );

    const renderAbout = () => (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-3xl mx-auto w-full space-y-8">
            <div>
                <h2 className="text-3xl font-extrabold tracking-tight mb-4">About AIVera</h2>
                <p className="text-lg text-[var(--text-secondary)] leading-relaxed mb-6">
                    AIVera is a next-generation Explainable Fake News Detection System designed to analyze content at an unprecedented granular level.
                </p>
                <div className="prose prose-invert text-[var(--text-secondary)] leading-relaxed">
                    <p>Unlike traditional binary classification systems that evaluate whole articles as simply true or false, AIVera segments content into individual verifiable declarative claims.</p>
                    <p>It evaluates the credibility of each claim using a fine-tuned DistilBERT transformer model and provides <strong>transparent AI reasoning</strong> using SHAP (SHapley Additive exPlanations) to highlight exactly which tokens and phrases influenced its multidimensional decision.</p>
                    <p>Coupled with a retrieval-augmented generation approach, AIVera seamlessly interfaces with live databanks (Wikipedia, News API) to fetch real-world factual evidence supporting or contradicting the AI's claims, moving critical NLP fact-checking out of the algorithmic black box.</p>
                </div>
            </div>

            <GlassCard className="p-8 border-accent/20 bg-accent/5">
                <h4 className="font-semibold text-lg mb-6 flex items-center gap-2"><Activity className="text-accent" /> System Stack</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-[var(--text-secondary)]">
                    <div className="space-y-3">
                        <div className="flex justify-between border-b border-[var(--border)] pb-2">
                            <span className="text-[var(--text-muted)]">Frontend</span>
                            <span className="font-medium text-[var(--text-primary)]">React, Tailwind, Framer</span>
                        </div>
                        <div className="flex justify-between border-b border-[var(--border)] pb-2">
                            <span className="text-[var(--text-muted)]">Gateway</span>
                            <span className="font-medium text-[var(--text-primary)]">Java 17, Spring Boot</span>
                        </div>
                        <div className="flex justify-between border-b border-[var(--border)] pb-2">
                            <span className="text-[var(--text-muted)]">Database</span>
                            <span className="font-medium text-[var(--text-primary)]">Relational DB</span>
                        </div>
                    </div>
                    <div className="space-y-3">
                        <div className="flex justify-between border-b border-[var(--border)] pb-2">
                            <span className="text-[var(--text-muted)]">Microservice</span>
                            <span className="font-medium text-[var(--text-primary)]">Python, FastAPI</span>
                        </div>
                        <div className="flex justify-between border-b border-[var(--border)] pb-2">
                            <span className="text-[var(--text-muted)]">Core Model</span>
                            <span className="font-medium text-[var(--text-primary)]">DistilBERT (LIAR)</span>
                        </div>
                        <div className="flex justify-between border-b border-[var(--border)] pb-2">
                            <span className="text-[var(--text-muted)]">Explainability</span>
                            <span className="font-medium text-[var(--text-primary)]">SHAP Gradient Logic</span>
                        </div>
                    </div>
                </div>
            </GlassCard>
        </motion.div>
    );

    const navItems = [
        { id: 'analyze', label: 'Analyze Center', icon: Search },
        { id: 'history', label: 'History Archive', icon: History },
        { id: 'about', label: 'System Info', icon: Info },
    ];

    return (
        <div className="flex min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] font-sans selection:bg-accent/30 overflow-hidden relative">
            {/* Background Effects */}
            <div className="fixed inset-0 pointer-events-none z-0">
                <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-accent/10 blur-[120px]" />
                <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-emerald-500/5 blur-[120px]" />
                <div className="absolute top-[20%] right-[10%] w-[30%] h-[30%] rounded-full bg-amber-500/5 blur-[120px]" />
            </div>

            {/* Sidebar */}
            <aside className="w-[260px] border-r border-[var(--border)] bg-[var(--bg-sidebar)] backdrop-blur-2xl flex flex-col fixed inset-y-0 z-50">
                <div className="p-6 border-b border-[var(--border)] flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-purple-800 flex items-center justify-center shadow-[0_0_20px_rgba(108,92,231,0.4)]">
                        <Shield size={20} className="text-[var(--text-primary)]" />
                    </div>
                    <h2 className="text-xl font-bold tracking-tight bg-gradient-to-br from-white to-white/50 bg-clip-text text-transparent">AIVera</h2>
                </div>
                
                <nav className="flex-1 p-4 space-y-2">
                    {navItems.map(item => (
                        <button
                            key={item.id}
                            onClick={() => setActivePage(item.id)}
                            className={cn(
                                "flex items-center gap-3 w-full px-4 py-3 rounded-xl transition-all text-sm font-medium",
                                activePage === item.id 
                                    ? "bg-[var(--bg-input)] text-[var(--text-primary)] shadow-inner border border-[var(--border)]" 
                                    : "text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-input)]"
                            )}
                        >
                            <item.icon size={18} className={activePage === item.id ? "text-accent" : ""} />
                            {item.label}
                        </button>
                    ))}
                </nav>

                <div className="p-6 border-t border-[var(--border)]">
                    <div className="text-[10px] uppercase tracking-widest font-bold text-[var(--text-muted)] flex items-center justify-between">
                        <span>v2.0.0</span>
                        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]"></span> Online</span>
                    </div>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 ml-[260px] flex flex-col relative z-10 min-h-screen max-h-screen overflow-y-auto custom-scrollbar">
                
                {/* Topbar */}
                <header className="h-[80px] sticky top-0 z-40 bg-[var(--bg-input)] backdrop-blur-md border-b border-[var(--border)] px-8 flex items-center justify-between shadow-sm">
                    <div className="flex items-center gap-3">
                        <div className="h-5 w-1 rounded-full bg-accent"></div>
                        <h1 className="text-lg font-semibold tracking-tight text-[var(--text-primary)]">
                            {navItems.find(n => n.id === activePage)?.label}
                        </h1>
                    </div>
                    
                    <div className="flex items-center gap-4">
                        <button onClick={toggleTheme} aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'} className="w-10 h-10 rounded-full bg-[var(--bg-input)] hover:bg-[var(--bg-input)] border border-[var(--border)] flex items-center justify-center transition-colors text-[var(--text-secondary)]">
                            {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
                        </button>
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gray-700 to-gray-900 border border-[var(--border)] flex items-center justify-center font-bold shadow-inner cursor-pointer hover:border-accent transition-colors">
                            U
                        </div>
                    </div>
                </header>

                {/* Content */}
                <div className="flex-1 p-8 pb-20">
                    {activePage === 'analyze' && renderAnalyze()}
                    {activePage === 'history' && renderHistory()}
                    {activePage === 'about' && renderAbout()}
                </div>
            </main>
        </div>
    );
}

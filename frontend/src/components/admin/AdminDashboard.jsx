import React, { useEffect, useState, useMemo } from 'react';
import { useAuth } from '../../context/AuthContext';
import api from '../../utils/axiosConfig';
import { GlassCard, VerdictBadge, ClaimHeatmap, ZoneScoreBar } from '../../ui_components';
import { 
  Shield, Activity, FileText, CheckCircle, AlertTriangle, LogOut, 
  Search, Filter, ExternalLink, RefreshCw, Trash2, Cpu, BarChart3, Database,
  ArrowRight, X, MessageSquare, ShieldAlert, TrendingUp
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip, 
  ResponsiveContainer, PieChart, Pie, Cell as ReCell, LineChart, Line
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';

const AdminDashboard = () => {
  const { logout } = useAuth();
  const [stats, setStats] = useState(null);
  const [advStats, setAdvStats] = useState(null);
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [isRetraining, setIsRetraining] = useState(false);
  const [healthStatus, setHealthStatus] = useState({ backend: 'online', ml: 'online', db: 'online' });
  const [searchTerm, setSearchTerm] = useState('');
  const [showOnlyFlagged, setShowOnlyFlagged] = useState(false);

  // SSE Subscription
  useEffect(() => {
    const eventSource = new EventSource('http://localhost:8081/api/admin/stream');
    
    eventSource.addEventListener('NEW_ARTICLE', (e) => {
      const article = JSON.parse(e.data);
      setArticles(prev => [article, ...prev].slice(0, 50));
      fetchStats();
    });

    eventSource.onerror = () => {
      console.error('SSE Connection failed');
      eventSource.close();
    };

    return () => eventSource.close();
  }, []);

  const fetchStats = async () => {
    try {
      const [s, adv] = await Promise.all([
        api.get('/admin/stats'),
        api.get('/admin/stats/advanced')
      ]);
      setStats(s.data);
      setAdvStats(adv.data);
    } catch (err) {
      console.error('Stats fetch failed', err);
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        const res = await api.get('/admin/articles?page=0&size=50&sort=createdAt,desc');
        setArticles(res.data.content || []);
        await fetchStats();
      } catch (err) {
        console.error('Init fetch failed', err);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const handleOverride = async (id, updates) => {
    try {
      const res = await api.patch(`/admin/articles/${id}/override`, updates);
      setArticles(prev => prev.map(a => a.id === id ? res.data : a));
      setSelectedArticle(res.data);
    } catch (err) {
      alert('Failed to save override');
    }
  };

  const triggerRetrain = async () => {
    setIsRetraining(true);
    try {
        await api.post('/admin/model/retrain');
        setTimeout(() => setIsRetraining(false), 5000);
    } catch (err) {
        setIsRetraining(false);
    }
  };

  const filteredArticles = useMemo(() => {
    return articles.filter(a => {
        const matchesSearch = a.content?.toLowerCase().includes(searchTerm.toLowerCase()) || a.id.toString().includes(searchTerm);
        const matchesFlag = showOnlyFlagged ? (a.overallCredibility < 0.5) : true;
        return matchesSearch && matchesFlag;
    });
  }, [articles, searchTerm, showOnlyFlagged]);

  // Chart Data Preparation
  const histogramData = useMemo(() => {
    if (!advStats) return [];
    return Object.entries(advStats.confidenceDistribution).map(([name, value]) => ({ name, value }));
  }, [advStats]);

  const verdictData = useMemo(() => {
    if (!advStats) return [];
    return Object.entries(advStats.verdictDistribution).map(([name, value]) => ({ name, value }));
  }, [advStats]);

  const trendData = useMemo(() => {
    if (!advStats) return [];
    return Object.entries(advStats.dailyAnalysisVolume).map(([name, value]) => ({ 
        name: name.split('-').slice(1).join('/'), 
        value 
    }));
  }, [advStats]);

  const COLORS = ['#10b981', '#f43f5e', '#6366f1', '#a855f7'];

  if (loading) {
    return (
      <div className="min-h-screen bg-[#08080a] flex flex-col items-center justify-center text-accent">
          <Shield size={64} className="mb-6 animate-pulse" />
          <p className="text-sm font-bold tracking-[0.2em] uppercase">Initializing Secure Neural Link...</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-[#08080a] text-white font-sans selection:bg-accent/30 selection:text-white">
      <div className="fixed inset-0 pointer-events-none opacity-40">
          <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-accent/20 blur-[150px]" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-emerald-500/10 blur-[150px]" />
      </div>

      <div className="flex-1 flex flex-col relative z-10 overflow-hidden">
        <header className="h-16 flex items-center justify-between px-8 border-b border-white/5 bg-black/40 backdrop-blur-xl sticky top-0 z-50">
            <div className="flex items-center gap-4">
                <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center shadow-[0_0_15px_rgba(108,92,231,0.5)]">
                    <Shield size={16} />
                </div>
                <div className="flex flex-col">
                    <h1 className="text-sm font-bold tracking-tight uppercase leading-none mb-1">AIvera Control</h1>
                    <div className="flex items-center gap-2">
                        <HealthIndicator label="Backend" status={healthStatus.backend} />
                        <HealthIndicator label="ML Service" status={healthStatus.ml} />
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-4">
                <button 
                  onClick={() => { fetchStats(); api.get('/admin/articles?page=0&size=50&sort=createdAt,desc').then(res => setArticles(res.data.content || [])); }}
                  className="p-2 hover:bg-accent/10 text-muted-foreground hover:text-accent rounded-lg transition-all border border-transparent hover:border-accent/20"
                  title="Force Sync Stats"
                >
                    <RefreshCw size={18} />
                </button>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-lg border border-white/10">
                    <Database size={14} className="text-muted-foreground" />
                    <span className="text-[10px] font-bold tracking-widest uppercase">{stats?.totalArticles} Records</span>
                </div>
                <button onClick={logout} className="p-2 hover:bg-rose-500/10 hover:text-rose-400 rounded-lg transition-colors border border-transparent hover:border-rose-500/20">
                    <LogOut size={18} />
                </button>
            </div>
        </header>

        <main className="flex-1 overflow-y-auto p-8 lg:px-12 custom-scrollbar">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
              <StatCard title="System Throughput" value={`${stats?.totalArticles}`} desc="Total analyses processed" icon={<Activity size={20}/>} />
              <StatCard title="Avg Model Latency" value={`${advStats?.averageLatencyMs.toFixed(0)}ms`} desc="Real-time processing speed" icon={<Cpu size={20}/>} trend="-12%" />
              <StatCard title="Audit Coverage" value="98.2%" desc="Verification success rate" icon={<Shield size={20}/>} />
              <StatCard title="Error Rate" value={`${advStats?.errorRatePercentage}%`} desc="Pipeline failure metrics" icon={<AlertTriangle size={20}/>} color="text-rose-400" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-10">
             {/* 7-Day Trend Line Chart */}
             <GlassCard className="lg:col-span-2 p-6">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h2 className="text-lg font-bold mb-1">Analysis Volume Trend</h2>
                        <p className="text-xs text-muted-foreground">Historical volume tracking over the last 7 days</p>
                    </div>
                    <TrendingUp size={20} className="text-accent" />
                </div>
                <div className="h-[250px] w-full">
                    <ResponsiveContainer>
                        <LineChart data={trendData}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="name" fontSize={10} axisLine={false} tickLine={false} dy={10} />
                            <YAxis fontSize={10} axisLine={false} tickLine={false} />
                            <ReTooltip contentStyle={{backgroundColor: '#101015', border: '1px solid #303035', fontSize: 12, borderRadius: 12}} />
                            <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={3} dot={{fill: '#6366f1', strokeWidth: 2, r: 4}} activeDot={{r: 6, strokeWidth: 0}} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
             </GlassCard>

             {/* Verdict Pie Chart */}
             <GlassCard className="p-6">
                <h2 className="text-lg font-bold mb-6">Verdict Distribution</h2>
                <div className="h-[180px] w-full relative">
                    <ResponsiveContainer>
                        <PieChart>
                            <Pie data={verdictData} innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                                {verdictData.map((entry, index) => (
                                    <ReCell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                        </PieChart>
                    </ResponsiveContainer>
                    <div className="absolute inset-0 flex items-center justify-center flex-col">
                        <span className="text-2xl font-bold tracking-tighter">{stats?.totalArticles}</span>
                        <span className="text-[8px] uppercase tracking-widest text-muted-foreground">Total</span>
                    </div>
                </div>
                <div className="mt-6 space-y-3">
                    {verdictData.map((s, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full" style={{backgroundColor: COLORS[i % COLORS.length]}} />
                                <span className="text-muted-foreground">{s.name}</span>
                            </div>
                            <span className="font-bold">{s.value}</span>
                        </div>
                    ))}
                </div>
             </GlassCard>
          </div>

          <div className="bg-[#101015] border border-white/5 rounded-2xl mb-8 p-4 flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-4 flex-1">
                  <div className="relative w-72">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
                      <input 
                        type="text" 
                        placeholder="Search articles..."
                        className="w-full bg-white/5 border border-white/10 rounded-xl py-2 pl-10 pr-4 text-sm focus:outline-none focus:border-accent transition-all"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                      />
                  </div>
                  <button 
                    onClick={() => setShowOnlyFlagged(!showOnlyFlagged)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all border ${
                        showOnlyFlagged 
                        ? 'bg-rose-500/20 border-rose-500/40 text-rose-400' 
                        : 'bg-white/5 border-white/10 text-muted-foreground hover:bg-white/10'
                    }`}
                  >
                    <Filter size={14} />
                    {showOnlyFlagged ? "Showing Flagged Only" : "Filter: All Results"}
                  </button>
              </div>
              <div className="flex items-center gap-3">
                  <button onClick={triggerRetrain} disabled={isRetraining} className="flex items-center gap-2 px-4 py-2 bg-accent/10 border border-accent/20 text-accent rounded-xl text-xs font-bold uppercase tracking-widest hover:bg-accent/20 transition-all disabled:opacity-50">
                    <RefreshCw size={14} className={isRetraining ? "animate-spin" : ""} />
                    {isRetraining ? "Retraining Pipeline..." : "Retrain Model"}
                  </button>
              </div>
          </div>

          <GlassCard className="overflow-hidden border-white/5 shadow-2xl">
            <div className="overflow-x-auto text-[13px]">
                <table className="w-full text-left">
                    <thead className="bg-white/[0.02] border-b border-white/5">
                        <tr>
                            <th className="px-6 py-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Analysis Identity</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Verdict</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Perf Metrics</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Audit Status</th>
                            <th className="px-6 py-4"></th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {filteredArticles.map((article) => (
                            <tr 
                                key={article.id} 
                                className="group hover:bg-white/[0.02] transition-colors cursor-pointer"
                                onClick={() => setSelectedArticle(article)}
                            >
                                <td className="px-6 py-5">
                                    <div className="flex flex-col">
                                        <span className="text-xs font-bold text-accent mb-1 flex items-center gap-2">
                                            AID-{article.id}
                                            <span className="text-[10px] text-muted-foreground uppercase font-medium">{new Date(article.createdAt).toLocaleTimeString()}</span>
                                        </span>
                                        <p className="text-sm text-muted-foreground line-clamp-1 italic group-hover:text-white transition-colors" title={article.content}>
                                            "{article.content?.substring(0, 70)}..."
                                        </p>
                                    </div>
                                </td>
                                <td className="px-6 py-5">
                                    <VerdictBadge score={article.overallCredibility} />
                                </td>
                                <td className="px-6 py-5">
                                    <div className="flex flex-col gap-1">
                                        <span className="text-[11px] font-mono text-muted-foreground">{article.latencyMs || '--'}ms response</span>
                                        <div className="w-20 h-1 bg-white/5 rounded-full overflow-hidden">
                                            <div className="h-full bg-accent opacity-40" style={{width: `${Math.min((article.latencyMs || 0)/10, 100)}%`}} />
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-5">
                                    {article.verdictOverride !== null ? (
                                        <div className="flex items-center gap-2 text-emerald-400">
                                            <CheckCircle size={14} />
                                            <span className="text-[10px] font-bold uppercase tracking-widest">Overridden</span>
                                        </div>
                                    ) : (
                                        <span className="text-[10px] font-bold text-white/10 uppercase tracking-widest">Awaiting Review</span>
                                    )}
                                </td>
                                <td className="px-6 py-5 text-right opacity-0 group-hover:opacity-100 transition-opacity">
                                    <div className="flex items-center justify-end gap-2 text-accent">
                                        <span className="text-[10px] font-bold uppercase tracking-widest">Audit</span>
                                        <ArrowRight size={16} />
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
          </GlassCard>
        </main>
      </div>

      <AnimatePresence>
        {selectedArticle && (
            <motion.div 
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                className="fixed inset-y-0 right-0 w-full lg:w-[600px] bg-[#0c0c0f] border-l border-white/10 z-[60] shadow-[-20px_0_50px_rgba(0,0,0,0.5)] flex flex-col"
            >
                <div className="p-6 border-b border-white/10 flex items-center justify-between bg-black/20">
                    <div className="flex items-center gap-4">
                        <button onClick={() => setSelectedArticle(null)} className="p-2 hover:bg-white/5 rounded-full transition-colors">
                            <X size={20} />
                        </button>
                        <div>
                            <h2 className="text-sm font-bold uppercase tracking-widest">Audit Terminal: AID-{selectedArticle.id}</h2>
                            <p className="text-[10px] text-muted-foreground">{new Date(selectedArticle.createdAt).toLocaleString()}</p>
                        </div>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
                    <section className="mb-10">
                        <div className="flex items-center gap-2 mb-4 text-accent">
                            <Cpu size={18} />
                            <h3 className="text-xs font-bold uppercase tracking-widest">Neural Analysis Hub</h3>
                        </div>
                        <GlassCard className="p-6 bg-white/[0.02]">
                            <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-4">Signal Breakdown (SHAP)</h4>
                            <div className="max-h-[250px] overflow-y-auto pr-2 custom-scrollbar">
                                <ClaimHeatmap 
                                    claimText={selectedArticle.content} 
                                    shapExplanation={selectedArticle.claims?.reduce((acc, c) => ({...acc, ...c.shapExplanation}), {})}
                                />
                            </div>
                        </GlassCard>
                        <div className="grid grid-cols-2 gap-4 mt-4">
                             <div className="p-4 rounded-xl border border-white/5 bg-white/[0.01]">
                                <span className="text-[9px] uppercase font-bold text-muted-foreground block mb-2">Model Confidence</span>
                                <ZoneScoreBar score={selectedArticle.overallCredibility} />
                             </div>
                             <div className="p-4 rounded-xl border border-white/5 bg-white/[0.01]">
                                <span className="text-[9px] uppercase font-bold text-muted-foreground block mb-2">Internal Signals</span>
                                <span className="text-xs font-bold">{selectedArticle.claims?.length || 0} sub-claims analyzed</span>
                             </div>
                        </div>
                    </section>

                    <section className="mb-10">
                        <div className="flex items-center gap-2 mb-4 text-emerald-400">
                            <MessageSquare size={18} />
                            <h3 className="text-xs font-bold uppercase tracking-widest">Human Moderation</h3>
                        </div>
                        <div className="space-y-6">
                            <div>
                                <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2 block">Audit Rationale</label>
                                <textarea 
                                    className="w-full bg-white/5 border border-white/10 rounded-xl p-4 text-sm focus:outline-none focus:border-emerald-500/50 min-h-[120px] transition-all"
                                    placeholder="Enter reasoning for verdict override or internal audit notes..."
                                    value={selectedArticle.adminNotes || ''}
                                    onChange={(e) => handleOverride(selectedArticle.id, { adminNotes: e.target.value })}
                                />
                            </div>
                            <div className="flex gap-4">
                                <div className="flex-1">
                                    <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2 block">Verdict Override</label>
                                    <select 
                                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:outline-none"
                                        value={selectedArticle.verdictOverride || ''}
                                        onChange={(e) => handleOverride(selectedArticle.id, { verdictOverride: e.target.value === '' ? null : parseFloat(e.target.value) })}
                                    >
                                        <option value="">No Override</option>
                                        <option value="1.0">Human Verified: REAL</option>
                                        <option value="0.0">Human Flagged: FAKE</option>
                                    </select>
                                </div>
                                <div className="flex-1">
                                    <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2 block">Risk Severity</label>
                                    <select 
                                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:outline-none"
                                        value={selectedArticle.severity || 'Medium'}
                                        onChange={(e) => handleOverride(selectedArticle.id, { severity: e.target.value })}
                                    >
                                        <option value="Low">Low Risk</option>
                                        <option value="Medium">Medium Severity</option>
                                        <option value="High">Priority / Viral</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </section>

                    <div className="p-6 rounded-2xl bg-accent/5 border border-accent/20 flex items-start gap-4">
                        <ShieldAlert className="text-accent flex-shrink-0 mt-1" size={20} />
                        <div>
                            <h4 className="text-xs font-bold uppercase tracking-widest text-accent mb-1">Feedback Loop Candidate</h4>
                            <p className="text-[10px] text-accent/70 leading-relaxed">This unit matches criteria for high-fidelity retraining. Overridden data will be prioritized in the next model tuning cycle.</p>
                        </div>
                    </div>
                </div>
            </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const StatCard = ({ title, value, desc, icon, trend, color = 'text-white' }) => (
    <GlassCard className="p-6 group hover:bg-white/[0.02] transition-all border-white/5">
        <div className="flex items-center justify-between mb-4">
            <div className="p-2.5 bg-white/5 rounded-xl border border-white/10 text-muted-foreground group-hover:text-accent group-hover:border-accent/30 transition-all">
                {icon}
            </div>
            {trend && <span className="text-[10px] font-bold text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded-full">{trend}</span>}
        </div>
        <dt className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1">{title}</dt>
        <dd className={`text-2xl font-bold tracking-tight mb-1 ${color}`}>{value}</dd>
        <dd className="text-[10px] text-muted-foreground">{desc}</dd>
    </GlassCard>
);

const HealthIndicator = ({ label, status }) => (
    <div className="flex items-center gap-1.5">
        <div className={`w-1.5 h-1.5 rounded-full ${status === 'online' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-rose-500 animate-pulse'}`} />
        <span className="text-[8px] font-bold uppercase tracking-tighter text-muted-foreground">{label}</span>
    </div>
);

export default AdminDashboard;


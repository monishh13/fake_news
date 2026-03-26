import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import api from '../../utils/axiosConfig';
import { GlassCard } from '../../ui_components';
import { Shield, Activity, FileText, CheckCircle, AlertTriangle, LogOut } from 'lucide-react';

const AdminDashboard = () => {
  const { logout } = useAuth();
  const [stats, setStats] = useState(null);
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [statsRes, articlesRes] = await Promise.all([
          api.get('/admin/stats'),
          api.get('/admin/articles?page=0&size=10&sort=createdAt,desc')
        ]);
        setStats(statsRes.data);
        setArticles(articlesRes.data.content || []);
      } catch (err) {
        console.error('Failed to fetch dashboard data', err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex flex-col items-center justify-center py-20 opacity-80 animate-pulse text-accent">
          <Shield size={64} className="mb-6 animate-bounce" />
          <p className="text-lg font-medium tracking-wide">Loading Secure Dashboard...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] font-sans relative overflow-hidden">
      {/* Background Effects */}
      <div className="fixed inset-0 pointer-events-none z-0">
          <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-accent/10 blur-[120px]" />
          <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-emerald-500/5 blur-[120px]" />
      </div>

      {/* Top Navbar */}
      <header className="h-[80px] sticky top-0 z-40 bg-[var(--bg-input)] backdrop-blur-md border-b border-[var(--border)] px-8 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-purple-800 flex items-center justify-center shadow-[0_0_20px_rgba(108,92,231,0.4)]">
                  <Shield size={20} className="text-[var(--text-primary)]" />
              </div>
              <h1 className="text-xl font-bold tracking-tight bg-gradient-to-br from-white to-white/50 bg-clip-text text-transparent hidden sm:block">
                  AIvera Admin Console
              </h1>
          </div>
          
          <button 
            onClick={logout}
            className="flex items-center gap-2 px-4 py-2 border border-[var(--border)] rounded-xl text-sm font-medium text-[var(--text-secondary)] hover:text-rose-400 hover:border-rose-500/50 hover:bg-rose-500/10 transition-all font-sans"
          >
            <LogOut size={16} />
            <span className="hidden sm:inline">Terminate Session</span>
          </button>
      </header>

      <main className="flex-1 w-full max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 relative z-10 overflow-y-auto custom-scrollbar">
        {stats && (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
            <StatCard icon={<FileText size={24} className="text-blue-400" />} title="Total Articles" value={stats.totalArticles} />
            <StatCard icon={<Activity size={24} className="text-accent" />} title="Avg Credibility" value={`${(stats.averageCredibilityScore * 100).toFixed(1)}%`} />
            <StatCard icon={<CheckCircle size={24} className="text-emerald-400" />} title="Verified Authentic" value={stats.realCount} color="text-emerald-400" />
            <StatCard icon={<AlertTriangle size={24} className="text-rose-400" />} title="Flagged Anomalies" value={stats.fakeCount} color="text-rose-400" />
          </div>
        )}

        <GlassCard className="flex flex-col border-[var(--border)]">
          <div className="px-6 py-5 border-b border-[var(--border)] flex items-center gap-3">
            <h3 className="text-lg leading-6 font-semibold text-[var(--text-primary)] tracking-wide">Analysis Log</h3>
            <span className="text-[10px] uppercase tracking-widest font-bold px-3 py-1 bg-[var(--bg-input)] rounded-full border border-[var(--border)] text-[var(--text-secondary)] shadow-inner">Live</span>
          </div>
          <div className="overflow-x-auto flex-1">
            <table className="min-w-full divide-y divide-[var(--border)] text-left">
              <thead className="bg-[#101015]">
                <tr>
                  <th className="px-6 py-4 text-xs font-bold text-[var(--text-muted)] uppercase tracking-widest">Timestamp</th>
                  <th className="px-6 py-4 text-xs font-bold text-[var(--text-muted)] uppercase tracking-widest">Content Trace</th>
                  <th className="px-6 py-4 text-xs font-bold text-[var(--text-muted)] uppercase tracking-widest">Verdict</th>
                  <th className="px-6 py-4 text-xs font-bold text-[var(--text-muted)] uppercase tracking-widest">Claims</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)] bg-transparent">
                {articles.map((article) => (
                  <tr key={article.id} className="hover:bg-[var(--bg-input)] transition-colors">
                    <td className="px-6 py-5 whitespace-nowrap text-xs text-[var(--text-muted)] font-medium">
                      {new Date(article.createdAt).toLocaleString()}
                    </td>
                    <td className="px-6 py-5 text-sm text-[var(--text-secondary)] max-w-md truncate italic">
                      "{article.content ? article.content.substring(0, 80) + '...' : 'N/A'}"
                    </td>
                    <td className="px-6 py-5 whitespace-nowrap">
                      <span className={`px-3 py-1 text-[10px] uppercase font-bold tracking-widest rounded-full border ${
                        article.overallCredibility >= 0.5 
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
                        : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                      }`}>
                        {(article.overallCredibility * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-6 py-5 whitespace-nowrap text-sm text-[var(--text-secondary)] font-semibold">
                      {article.claims ? article.claims.length : 0} extracted
                    </td>
                  </tr>
                ))}
                {articles.length === 0 && (
                  <tr>
                    <td colSpan="4" className="px-6 py-12 text-center text-sm text-[var(--text-muted)] italic">
                      No anomalies detected in the system yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </main>
    </div>
  );
};

const StatCard = ({ icon, title, value, color = 'text-[var(--text-primary)]' }) => (
  <GlassCard className="p-6 transition-all hover:bg-[var(--bg-input)]">
    <div className="flex items-center gap-4">
      <div className="p-3 bg-[var(--bg-input)] rounded-xl border border-[var(--border)] shadow-inner">
        {icon}
      </div>
      <div>
        <dt className="text-[10px] font-bold tracking-widest uppercase text-[var(--text-muted)] mb-1">{title}</dt>
        <dd className={`text-3xl font-semibold tracking-tight ${color}`}>{value}</dd>
      </div>
    </div>
  </GlassCard>
);

export default AdminDashboard;

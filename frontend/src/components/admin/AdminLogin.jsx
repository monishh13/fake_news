import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import api from '../../utils/axiosConfig';
import { Shield, AlertTriangle } from 'lucide-react';
import { GlassCard } from '../../ui_components';
import { motion, AnimatePresence } from 'framer-motion';

const AdminLogin = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/admin/dashboard';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = await api.post('/auth/login', { username, password });
      login(response.data.jwt);
      navigate(from, { replace: true });
    } catch (err) {
      if (err.response?.status === 429) {
        setError('Too many failed attempts. Please try again later.');
      } else if (err.response?.status === 401) {
        setError('Invalid username or password.');
      } else {
        setError('An error occurred during login.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] font-sans flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background Effects */}
      <div className="fixed inset-0 pointer-events-none z-0">
          <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-accent/10 blur-[120px]" />
          <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-emerald-500/5 blur-[120px]" />
      </div>

      <div className="relative z-10 sm:mx-auto sm:w-full sm:max-w-md mb-8 flex flex-col items-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent to-purple-800 flex items-center justify-center shadow-[0_0_30px_rgba(108,92,231,0.5)] mb-6">
            <Shield size={32} className="text-[var(--text-primary)]" />
        </div>
        <h2 className="text-center text-3xl font-extrabold tracking-tight bg-gradient-to-br from-white to-white/60 bg-clip-text text-transparent">
          Secure Portal
        </h2>
      </div>

      <div className="relative z-10 sm:mx-auto sm:w-full sm:max-w-[420px]">
        <GlassCard className="py-8 px-6 sm:px-10">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <AnimatePresence>
                {error && (
                    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="p-4 bg-red-500/10 border border-red-500/20 text-red-500 rounded-xl flex items-center gap-3 overflow-hidden">
                        <AlertTriangle size={20} className="flex-shrink-0" />
                        <span className="text-sm font-medium">{error}</span>
                    </motion.div>
                )}
            </AnimatePresence>
            
            <div>
              <label className="block text-xs font-bold tracking-widest text-[var(--text-muted)] uppercase mb-2">Username</label>
              <div className="mt-1">
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="appearance-none block w-full px-4 py-3 bg-[var(--bg-input)] border border-[var(--border)] rounded-xl text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all sm:text-sm shadow-inner"
                  placeholder="Enter administrator ID"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold tracking-widest text-[var(--text-muted)] uppercase mb-2">Password</label>
              <div className="mt-1">
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="appearance-none block w-full px-4 py-3 bg-[var(--bg-input)] border border-[var(--border)] rounded-xl text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all sm:text-sm shadow-inner"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center items-center py-3 px-4 rounded-xl bg-accent hover:bg-accent/90 text-[var(--text-primary)] font-medium shadow-[0_0_20px_rgba(108,92,231,0.3)] transition-all active:scale-[0.98] disabled:opacity-50 gap-2"
              >
                {isLoading ? <div className="w-5 h-5 rounded-full border-2 border-white/30 border-t-white animate-spin" /> : 'Authenticate'}
              </button>
            </div>
          </form>
        </GlassCard>
      </div>
    </div>
  );
};

export default AdminLogin;

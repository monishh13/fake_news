import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Check, Copy, Info, AlertTriangle } from 'lucide-react';

const cn = (...i) => twMerge(clsx(i));

// ── Helpers ────────────────────────────────────────────────────────────────
export const getVerdict = (s) => {
  const p = s * 100;
  if (p > 75) return { label: 'Verified',  cls: 'bg-emerald-600/20 text-emerald-400 border-emerald-600/30' };
  if (p > 55) return { label: 'Supported', cls: 'bg-green-500/20 text-green-400 border-green-500/30' };
  if (p > 40) return { label: 'Uncertain', cls: 'bg-amber-500/20 text-amber-400 border-amber-500/30' };
  return             { label: 'Disputed',  cls: 'bg-rose-500/20 text-rose-400 border-rose-500/30' };
};

export const strengthLabel = (v) =>
  v >= 0.25 ? 'Very Strong' : v >= 0.15 ? 'Strong' : v >= 0.07 ? 'Moderate' : 'Slight';

const wordExplain = (w, s) => s > 0
  ? `"${w}" is a ${strengthLabel(Math.abs(s)).toLowerCase()} positive signal. In credible reporting, similar terms frequently appear in well-sourced content, increasing the model's confidence.`
  : `"${w}" is a ${strengthLabel(Math.abs(s)).toLowerCase()} negative signal. This term tends to appear in unverified content, reducing the model's confidence score.`;

// ── VerdictBadge ───────────────────────────────────────────────────────────
export const VerdictBadge = ({ score }) => {
  const { label, cls } = getVerdict(score);
  return (
    <span className={cn('uppercase tracking-widest text-[10px] font-bold px-3 py-1.5 rounded-full border flex-shrink-0', cls)}>
      {label}
    </span>
  );
};

// ── ZoneScoreBar ───────────────────────────────────────────────────────────
export const ZoneScoreBar = ({ score }) => {
  const seg = Math.min(Math.floor(score * 7), 6);
  const cols = ['#f43f5e', '#fb923c', '#fbbf24', '#facc15', '#a3e635', '#4ade80', '#34d399'];
  return (
    <div className="w-full">
      <div className="flex gap-1 h-3 mb-1">
        {cols.map((c, i) => (
          <div key={i} className="flex-1 rounded-sm transition-all"
            style={{ backgroundColor: c, opacity: i === seg ? 1 : i < seg ? 0.45 : 0.15 }} />
        ))}
      </div>
      <div className="flex justify-between text-[9px] text-muted-foreground px-0.5">
        <span>Disputed</span><span>Uncertain</span><span>Verified</span>
      </div>
    </div>
  );
};

// ── ContextualNote ─────────────────────────────────────────────────────────
export const ContextualNote = ({ score }) => {
  const p = score * 100;
  const [msg, cls] = p > 75
    ? ['Strong supporting evidence detected. This claim is likely reliable.',
       'bg-emerald-500/10 border-emerald-500/20 text-emerald-400']
    : p > 55
    ? ['Moderate evidence detected. Treat this with appropriate caution.',
       'bg-green-500/10 border-green-500/20 text-green-400']
    : p > 40
    ? ['Uncertain range. Manual verification is recommended for critical decisions.',
       'bg-amber-500/10 border-amber-500/20 text-amber-400']
    : ['Model flags this as likely disputed. Treat with significant skepticism.',
       'bg-rose-500/10 border-rose-500/20 text-rose-400'];
  return (
    <div className={cn('flex items-start gap-2 px-4 py-3 rounded-xl border text-xs leading-relaxed', cls)}>
      <span className="flex-shrink-0">ℹ</span><span>{msg}</span>
    </div>
  );
};

// ── StrengthDots ───────────────────────────────────────────────────────────
export const StrengthDots = ({ score }) => {
  const a = Math.abs(score);
  const f = a >= 0.25 ? 4 : a >= 0.15 ? 3 : a >= 0.07 ? 2 : 1;
  return (
    <span className="text-sm tracking-widest">
      {[0, 1, 2, 3].map(i => (
        <span key={i} className={i < f ? 'text-accent' : 'text-white/20'}>●</span>
      ))}
    </span>
  );
};

// ── ClaimHeatmap ───────────────────────────────────────────────────────────
export const ClaimHeatmap = ({ claimText, shapExplanation, activeWord, onWordClick }) => {
  const shap = shapExplanation || {};
  const maxAbs = Math.max(...Object.values(shap).map(Math.abs), 0.001);
  return (
    <div>
      <p className="leading-9 flex flex-wrap text-base">
        {(claimText || '').split(/(\s+)/).map((tok, i) => {
          if (/^\s+$/.test(tok)) return <span key={i}>&nbsp;</span>;
          const key = tok.replace(/[^a-zA-Z0-9']/g, '').toLowerCase();
          const sc = shap[key] ?? shap[tok.toLowerCase()] ?? null;
          if (sc === null || Math.abs(sc) < 0.01) return <span key={i}>{tok}</span>;
          const op = Math.max(0.15, Math.abs(sc) / maxAbs) * 0.8;
          return (
            <span key={i}
              onClick={() => onWordClick(key, sc)}
              className={cn('cursor-pointer rounded px-0.5 mx-px transition-all',
                activeWord === key ? 'ring-2 ring-purple-500' : 'hover:ring-1 hover:ring-purple-400/70')}
              style={{ backgroundColor: sc > 0 ? `rgba(52,211,153,${op})` : `rgba(244,63,94,${op})` }}>
              {tok}
            </span>
          );
        })}
      </p>
      <div className="flex items-center gap-4 mt-3 text-[10px] text-[var(--text-muted)] flex-wrap">
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-sm bg-emerald-400/60" />Boosts score
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-sm bg-rose-400/60" />Lowers score
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-sm bg-white/10" />No effect
        </span>
        <span className="italic ml-auto opacity-70">Darker = stronger influence</span>
      </div>
    </div>
  );
};

// ── SummaryStrip ───────────────────────────────────────────────────────────
export const SummaryStrip = ({ shapExplanation }) => {
  const e = Object.entries(shapExplanation || {});
  const b = e.filter(([, v]) => v > 0.01).length;
  const l = e.filter(([, v]) => v < -0.01).length;
  return (
    <div className="flex items-center gap-3 flex-wrap text-xs py-1">
      <span className="px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400 font-semibold border border-emerald-500/20">
        {b} word{b !== 1 ? 's' : ''} boosted it
      </span>
      <span className="text-[var(--text-muted)]">·</span>
      <span className="px-2.5 py-1 rounded-full bg-rose-500/15 text-rose-400 font-semibold border border-rose-500/20">
        {l} word{l !== 1 ? 's' : ''} lowered it
      </span>
      <span className="text-[var(--text-muted)]">·</span>
      <span className="italic text-[var(--text-muted)]">Click any word to understand why</span>
    </div>
  );
};

// ── InfluenceBreakdown ─────────────────────────────────────────────────────
export const InfluenceBreakdown = ({ shapExplanation, activeWord, onWordClick }) => {
  const entries = Object.entries(shapExplanation || {})
    .filter(([, v]) => Math.abs(v) >= 0.01)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const boosted = entries.filter(([, v]) => v > 0);
  const lowered = entries.filter(([, v]) => v < 0);
  const Pill = ({ word, score }) => (
    <button
      onClick={() => onWordClick(word, score)}
      className={cn(
        'flex items-center justify-between gap-2 px-3 py-1.5 rounded-full border text-xs w-full transition-all',
        activeWord === word
          ? 'ring-2 ring-purple-500 border-purple-400/50 bg-purple-500/10'
          : 'border-[var(--border)] bg-[var(--bg-input)] hover:border-purple-400/50'
      )}>
      <span className="font-medium truncate">{word}</span>
      <span className={cn('text-[9px] font-bold px-2 py-0.5 rounded-full flex-shrink-0',
        score > 0 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400')}>
        {strengthLabel(Math.abs(score))}
      </span>
    </button>
  );
  const empty = <p className="text-xs text-[var(--text-muted)] italic px-1">None detected</p>;
  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <p className="text-[9px] font-bold tracking-widest text-emerald-400 uppercase mb-2">↑ Boosted the score</p>
        <div className="space-y-1">
          {boosted.length ? boosted.map(([w, s]) => <Pill key={w} word={w} score={s} />) : empty}
        </div>
      </div>
      <div>
        <p className="text-[9px] font-bold tracking-widest text-rose-400 uppercase mb-2">↓ Lowered the score</p>
        <div className="space-y-1">
          {lowered.length ? lowered.map(([w, s]) => <Pill key={w} word={w} score={s} />) : empty}
        </div>
      </div>
    </div>
  );
};

// ── WordExplanationPanel ───────────────────────────────────────────────────
export const WordExplanationPanel = ({ activeWord, activeScore }) => activeWord ? (
  <div className="p-4 rounded-xl border border-purple-500/30 bg-purple-500/5 space-y-2">
    <div className="flex items-center justify-between gap-2">
      <span className="text-lg font-bold">"{activeWord}"</span>
      <StrengthDots score={activeScore} />
    </div>
    <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{wordExplain(activeWord, activeScore)}</p>
    <div className="flex items-center gap-2 text-[10px]">
      <span className={cn('px-2 py-0.5 rounded-full font-semibold',
        activeScore > 0 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400')}>
        {strengthLabel(Math.abs(activeScore))}
      </span>
      <span className="text-[var(--text-muted)]">
        {activeScore > 0 ? 'Positive influence' : 'Negative influence'}
      </span>
    </div>
  </div>
) : (
  <div className="flex items-center justify-center p-4 rounded-xl border border-dashed border-[var(--border)] text-xs italic text-[var(--text-muted)]">
    Click any highlighted word or pill to see an explanation.
  </div>
);

// ── Internal CopyBtn (used by EvidenceCard & ClaimCard) ────────────────────
const CopyBtn = ({ text }) => {
  const [copied, setCopied] = useState(false);
  const doCopy = () => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); };
  return (
    <button onClick={doCopy} className="p-1.5 text-muted-foreground hover:text-primary transition-colors hover:bg-[var(--bg-input)] rounded-md">
      {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
    </button>
  );
};

// ── EvidenceCard ───────────────────────────────────────────────────────────
export const EvidenceCard = ({ evidenceText, activeFilter }) => {
  const [open, setOpen] = useState(false);
  const m = evidenceText.match(/^\[(.*?)\]\s*(.*)$/);
  const src = m ? m[1] : 'Source';
  const txt = m ? m[2] : evidenceText;

  let tier = 'Low', tCls = 'bg-rose-500/20 text-rose-400 border-rose-500/30', barColor = '#f43f5e';
  if (src.includes('Google') || src.includes('Fact Check') || src.includes('Wikipedia')) {
    tier = 'High'; tCls = 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'; barColor = '#34d399';
  } else if (src.includes('NewsAPI') || src.includes('NewsData')) {
    tier = 'Medium'; tCls = 'bg-amber-500/20 text-amber-400 border-amber-500/30'; barColor = '#fbbf24';
  } else if (src.includes('GDELT')) {
    tier = 'Context'; tCls = 'bg-blue-500/20 text-blue-400 border-blue-500/30'; barColor = '#60a5fa';
  }

  if (activeFilter === 'high' && tier !== 'High') return null;
  if (activeFilter === 'context' && tier !== 'Context') return null;

  const credW = tier === 'High' ? '88%' : tier === 'Medium' ? '60%' : tier === 'Context' ? '72%' : '28%';

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-input)] overflow-hidden">
      <button onClick={() => setOpen(o => !o)}
        className="w-full p-3 flex items-start gap-3 text-left hover:bg-white/5 transition-colors">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className={cn('text-[10px] uppercase tracking-widest font-bold px-2 py-0.5 rounded-md border', tCls)}>{src}</span>
            <span className={cn('text-[10px] font-semibold px-2 py-0.5 rounded-full border', tCls)}>{tier}</span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] line-clamp-1 italic">{txt}</p>
        </div>
        <motion.span animate={{ rotate: open ? 90 : 0 }} transition={{ duration: 0.2 }}
          className="text-[var(--text-muted)] text-[10px] flex-shrink-0 mt-1 font-bold">▶</motion.span>
      </button>
      <div className="px-3 pb-2">
        <div className="h-1 bg-white/5 rounded-full overflow-hidden">
          <div className="h-full rounded-full" style={{ width: credW, backgroundColor: barColor }} />
        </div>
      </div>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="px-3 pb-3 pt-2 border-t border-[var(--border)] space-y-2">
              <p className="text-sm leading-relaxed">"{txt}"</p>
              <div className="flex flex-wrap gap-2 items-center text-[10px]">
                <span className="px-2 py-0.5 rounded-full bg-white/5 text-[var(--text-muted)]">Source: {src}</span>
                <span className="px-2 py-0.5 rounded-full bg-white/5 text-[var(--text-muted)]">Credibility: {tier}</span>
                <CopyBtn text={txt} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ── ClaimCard ──────────────────────────────────────────────────────────────
export const ClaimCard = ({ claim, getScoreColor }) => {
  const [activeWord, setActiveWord] = useState(null);
  const [activeScore, setActiveScore] = useState(0);
  const [evFilter, setEvFilter] = useState('all');

  const hasShap = claim.shapExplanation && Object.keys(claim.shapExplanation).length > 0;
  const isLow = claim.credibilityScore >= 0.35 && claim.credibilityScore <= 0.65;
  const handleWord = (word, score) => {
    setActiveWord(w => w === word ? null : word);
    setActiveScore(score);
  };
  const filters = [
    { id: 'all', label: 'All' },
    { id: 'high', label: 'High Credibility' },
    { id: 'context', label: 'Context Only' },
  ];

  return (
    <motion.div className="bg-[var(--bg-card)] backdrop-blur-xl border border-[var(--border)] rounded-2xl shadow-xl overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-[var(--border)]">
        <div className="flex flex-col md:flex-row justify-between items-start gap-4 mb-4">
          <div className="flex-1 flex items-start gap-2">
            <p className="text-lg font-medium leading-relaxed italic">"{claim.claimText}"</p>
            <CopyBtn text={claim.claimText} />
          </div>
          <VerdictBadge score={claim.credibilityScore} />
        </div>
        <ZoneScoreBar score={claim.credibilityScore} />
        <div className="flex items-center gap-3 mt-2">
          <div className="flex-1"><ContextualNote score={claim.credibilityScore} /></div>
          <span className="text-sm font-bold flex-shrink-0"
            style={{ color: getScoreColor(claim.credibilityScore) }}>
            {Math.round(claim.credibilityScore * 100)}%
          </span>
        </div>
      </div>

      {/* Low Confidence Warning */}
      {isLow && (
        <div className="mx-6 mt-4 flex items-start gap-2 px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs">
          <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
          <span><strong>Low confidence</strong> — score near 0.5. Verify from primary sources.</span>
        </div>
      )}

      {/* Two-panel grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 bg-[var(--bg-input)] divide-y lg:divide-y-0 lg:divide-x divide-white/5 mt-4">
        {/* Left: Word Influence */}
        <div className="p-6 space-y-4">
          <h4 className="text-sm font-semibold tracking-widest text-muted-foreground uppercase flex items-center justify-between">
            Word Influence
            <span className="text-[10px] font-normal italic lowercase text-[var(--text-muted)]">click words to explore</span>
          </h4>
          {hasShap ? (
            <>
              <ClaimHeatmap claimText={claim.claimText} shapExplanation={claim.shapExplanation}
                activeWord={activeWord} onWordClick={handleWord} />
              <SummaryStrip shapExplanation={claim.shapExplanation} />
              <InfluenceBreakdown shapExplanation={claim.shapExplanation}
                activeWord={activeWord} onWordClick={handleWord} />
              <WordExplanationPanel activeWord={activeWord} activeScore={activeScore} />
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-40 text-center opacity-40">
              <Info size={28} className="mb-2" />
              <p className="text-sm">No word influence data available.</p>
            </div>
          )}
        </div>

        {/* Right: Evidence */}
        <div className="p-6 space-y-4">
          <h4 className="text-sm font-semibold tracking-widest text-muted-foreground uppercase">Retrieved Evidence</h4>
          {claim.evidenceSnippets?.length > 0 ? (
            <>
              <div className="flex items-center gap-2 flex-wrap">
                {filters.map(f => (
                  <button key={f.id} onClick={() => setEvFilter(f.id)}
                    className={cn('text-[10px] px-2.5 py-1 rounded-full border font-semibold transition-all',
                      evFilter === f.id
                        ? 'bg-accent text-white border-accent'
                        : 'border-[var(--border)] text-[var(--text-muted)] hover:border-accent/50')}>
                    {f.label}
                  </button>
                ))}
              </div>
              <div className="space-y-2">
                {claim.evidenceSnippets.map((ev, i) => (
                  <EvidenceCard key={i} evidenceText={ev} activeFilter={evFilter} />
                ))}
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center text-center opacity-40 py-8">
              <Info size={32} className="mb-3" />
              <p className="text-sm">No verified factual evidence<br />located for this claim.</p>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

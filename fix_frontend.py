import re

with open(r"d:\Study\projects\fake_news\fake_news\frontend\src\App.jsx", "r", encoding="utf-8") as f:
    content = f.read()

# Replace colors
replacements = {
    r'bg-\[\#06080F\]': r'bg-[var(--bg-primary)]',
    r'bg-black/40': r'bg-[var(--bg-sidebar)]',
    r'bg-black/20': r'bg-[var(--bg-input)]',
    r'bg-white/5': r'bg-[var(--bg-input)]',
    r'bg-white/10': r'bg-[var(--bg-input)]',
    r'text-white/90': r'text-[var(--text-primary)]',
    r'text-white/80': r'text-[var(--text-primary)]',
    r'text-white/70': r'text-[var(--text-secondary)]',
    r'text-white/60': r'text-[var(--text-secondary)]',
    r'text-white/50': r'text-[var(--text-muted)]',
    r'text-white/40': r'text-[var(--text-muted)]',
    r'text-white/30': r'text-[var(--text-muted)]',
    r'text-white': r'text-[var(--text-primary)]',
    r'border-white/10': r'border-[var(--border)]',
    r'border-white/5': r'border-[var(--border)]',
    r'border-white/20': r'border-[var(--border)]',
    r'placeholder:text-white/30': r'placeholder:text-[var(--text-muted)]',
    r'bg-card/70': r'bg-[var(--bg-card)]',
    r'text-foreground': r'text-[var(--text-primary)]',
}

for old, new_ in replacements.items():
    content = re.sub(old, new_, content)

# Also fix the topbar theme toggle button
# Find the button containing <Sun size={18} /> and add onClick
# <button className="w-10 h-10 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center transition-colors text-white/70">
#     <Sun size={18} />
# </button>

toggle_btn_pattern = r'(<button className=")([^"]+)(">\s*<Sun size=\{18\} />\s*</button>)'
def repl_toggle(m):
    return f'<button onClick={{toggleTheme}} className="{m.group(2)}">\n                            {{theme === "light" ? <Moon size={{18}} /> : <Sun size={{18}} />}}\n                        </button>'

content = re.sub(toggle_btn_pattern, repl_toggle, content)

with open(r"d:\Study\projects\fake_news\fake_news\frontend\src\App.jsx", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated App.jsx")

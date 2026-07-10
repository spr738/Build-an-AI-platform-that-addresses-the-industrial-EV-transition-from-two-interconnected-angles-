
Action: file_editor create /app/frontend/src/index.css --file-text "@import url('https://fonts.googleapis.com/css2?family=Chivo:wght@400;700;900&family=Manrope:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --vc-page: #050505;
  --vc-surface: #111111;
  --vc-surface-2: #171717;
  --vc-surface-3: #1a1a1a;
  --vc-border: #262626;
  --vc-border-subtle: rgba(255, 255, 255, 0.06);
  --vc-text: #f4f4f5;
  --vc-text-2: #a1a1aa;
  --vc-text-muted: #71717a;
  --vc-brand: #0055ff;
  --vc-brand-hover: #0044cc;
  --vc-success: #00e676;
  --vc-warning: #ffb000;
  --vc-alert: #ff3b30;
}

@layer base {
  :root {
    --background: 0 0% 2%;
    --foreground: 0 0% 96%;
    --card: 0 0% 6.7%;
    --card-foreground: 0 0% 96%;
    --popover: 0 0% 6.7%;
    --popover-foreground: 0 0% 96%;
    --primary: 220 100% 50%;
    --primary-foreground: 0 0% 100%;
    --secondary: 0 0% 10%;
    --secondary-foreground: 0 0% 96%;
    --muted: 0 0% 10%;
    --muted-foreground: 0 0% 63%;
    --accent: 0 0% 10%;
    --accent-foreground: 0 0% 96%;
    --destructive: 4 100% 60%;
    --destructive-foreground: 0 0% 98%;
    --border: 0 0% 14.9%;
    --input: 0 0% 10%;
    --ring: 220 100% 50%;
    --radius: 0.125rem;
  }
}

html, body, #root {
  height: 100%;
  background: var(--vc-page);
  color: var(--vc-text);
}

body {
  margin: 0;
  font-family: 'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-image:
    radial-gradient(1200px 600px at 10% -10%, rgba(0, 85, 255, 0.06), transparent),
    radial-gradient(800px 500px at 100% 100%, rgba(0, 230, 118, 0.03), transparent);
  background-attachment: fixed;
}

/* Noise overlay */
body::before {
  content: \"\";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  opacity: 0.035;
  background-image: url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>\");
}

h1, h2, h3, h4 { font-family: 'Chivo', sans-serif; letter-spacing: -0.01em; }
.font-mono, code, pre { font-family: 'JetBrains Mono', monospace; }

.vc-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--vc-text-muted);
}

.vc-surface {
  background: var(--vc-surface);
  border: 1px solid var(--vc-border);
  border-radius: 2px;
}

.vc-surface-hover:hover {
  background: var(--vc-surface-3);
  border-color: #333;
  transition: background-color 150ms ease-out, border-color 150ms ease-out;
}

.vc-btn-primary {
  background: var(--vc-brand);
  color: white;
  border: 1px solid var(--vc-brand);
  padding: 0.55rem 1rem;
  border-radius: 2px;
  font-weight: 600;
  font-size: 0.85rem;
  letter-spacing: 0.01em;
  transition: background-color 150ms ease-out, border-color 150ms ease-out;
}
.vc-btn-primary:hover { background: var(--vc-brand-hover); border-color: var(--vc-brand-hover); }
.vc-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.vc-btn-ghost {
  background: transparent;
  color: var(--vc-text);
  border: 1px solid var(--vc-border);
  padding: 0.55rem 1rem;
  border-radius: 2px;
  font-size: 0.85rem;
  transition: background-color 150ms ease-out, border-color 150ms ease-out;
}
.vc-btn-ghost:hover { background: var(--vc-surface-3); border-color: #333; }

.vc-input {
  background: var(--vc-surface-2);
  border: 1px solid var(--vc-border);
  color: var(--vc-text);
  padding: 0.6rem 0.75rem;
  border-radius: 2px;
  font-family: 'Manrope', sans-serif;
  font-size: 0.9rem;
  width: 100%;
  outline: none;
  transition: border-color 150ms ease-out;
}
.vc-input:focus { border-color: var(--vc-brand); }

.vc-metric { font-family: 'JetBrains Mono', monospace; font-weight: 700; letter-spacing: -0.02em; }

.status-dot {
  display: inline-block; width: 8px; height: 8px; border-radius: 999px;
  box-shadow: 0 0 0 2px rgba(255,255,255,0.03);
}
.status-active { background: #00e676; box-shadow: 0 0 8px rgba(0,230,118,0.6); }
.status-charging { background: #0055ff; box-shadow: 0 0 8px rgba(0,85,255,0.6); }
.status-down { background: #ff3b30; box-shadow: 0 0 8px rgba(255,59,48,0.6); }
.status-warning { background: #ffb000; box-shadow: 0 0 8px rgba(255,176,0,0.6); }

.scanlines {
  background-image: repeating-linear-gradient(0deg, rgba(255,255,255,0.02) 0px, rgba(255,255,255,0.02) 1px, transparent 1px, transparent 3px);
}

.vc-scroll::-webkit-scrollbar { width: 6px; height: 6px; }
.vc-scroll::-webkit-scrollbar-track { background: transparent; }
.vc-scroll::-webkit-scrollbar-thumb { background: #262626; border-radius: 999px; }
.vc-scroll::-webkit-scrollbar-thumb:hover { background: #333; }

/* recharts overrides */
.recharts-cartesian-axis-tick-value { font-family: 'JetBrains Mono', monospace; font-size: 10px; fill: #71717a; }
.recharts-tooltip-wrapper .recharts-default-tooltip { background: #111 !important; border: 1px solid #262626 !important; border-radius: 2px !important; font-family: 'JetBrains Mono', monospace !important; }
"
Observation: Overwrite successful: /app/frontend/src/index.css
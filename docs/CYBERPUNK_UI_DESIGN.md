# Cyberpunk UI Design System

## 🎨 Theme Overview
**Aesthetic**: High-tech, dystopian, neon-noir, "Cyberpunk 2077" inspired.
**Core Principles**:
- **Dark Mode Only**: Deep blacks and violet backgrounds.
- **High Contrast**: Neon text on dark backgrounds.
- **Geometric**: Angled corners (45-degree cuts), grid lines, technical markings.
- **Glitch**: Subtle animations, scanlines, chromatic aberration on hover.
- **Information Density**: Dense data displays, HUD-like overlays.

## 🎨 Color Palette

### Backgrounds
- **Void Black**: `#050505` (Main Background)
- **Deep Violet**: `#0a0a14` (Card Background)
- **Grid Lines**: `#1a1a2e` (Subtle dividers)

### Primary Accents (Neon)
- **Cyber Blue**: `#00f0ff` (Primary Action, Links, Borders)
- **Neon Pink**: `#ff003c` (Alerts, Errors, "Critical" status)
- **Toxic Green**: `#39ff14` (Success, "Safe" status, Stable)
- **Solar Yellow**: `#fcee0a` (Warnings, "Caution" status)

### Text
- **Holo White**: `#e0e0e0` (Primary Text)
- **Dimmed Gray**: `#888888` (Secondary Text)

## 🔠 Typography

### Headers & Data
- **Font**: `Rajdhani` (Google Font)
- **Weights**: Bold (700), SemiBold (600)
- **Usage**: Titles, component names, metrics.

### Body Copy
- **Font**: `Roboto Mono` or `Share Tech Mono`
- **Usage**: Logs, descriptions, chat messages.

### Decorative
- **Font**: `Orbitron`
- **Usage**: Large display numbers, system status, countdowns.

## 🧩 UI Components

### 1. The "Shard" Container
A standard card element with a "chipped" or angled corner.
```css
.shard-card {
  background: #0a0a14;
  border: 1px solid #1a1a2e;
  border-left: 2px solid #00f0ff; /* Neon accent on left */
  clip-path: polygon(0 0, 100% 0, 100% 85%, 95% 100%, 0 100%); /* Cut corner */
  box-shadow: 0 0 10px rgba(0, 240, 255, 0.1);
}
```

### 2. Neon Buttons
Buttons that glow and "glitch" on hover.
```css
.cyber-button {
  background: transparent;
  border: 1px solid #fcee0a;
  color: #fcee0a;
  text-transform: uppercase;
  font-family: 'Rajdhani', sans-serif;
  letter-spacing: 2px;
}
.cyber-button:hover {
  background: #fcee0a;
  color: #000;
  box-shadow: 0 0 15px #fcee0a;
  /* Add glitch animation keyframes here */
}
```

### 3. Scanline Overlay
A subtle CRT effect over the entire screen.
```css
.scanlines {
  background: linear-gradient(
    to bottom,
    rgba(255,255,255,0),
    rgba(255,255,255,0) 50%,
    rgba(0,0,0,0.1) 50%,
    rgba(0,0,0,0.1)
  );
  background-size: 100% 4px;
  pointer-events: none;
}
```

## 📱 Layout Strategy

### Dashboard (HUD)
- **Top Bar**: System status, connection quality (Ping), current time.
- **Left Sidebar**: Navigation (Diagnostics, TSBs, Database, Settings).
- **Main Stage**: The active tool.
- **Right Panel**: "Assistant" stream (Chat/Logs).

## 🛠 Tech Stack
- **Framework**: Next.js 14+ (App Router)
- **Styling**: Tailwind CSS + Custom CSS Modules
- **Icons**: Lucide React (with glowing stroke customizations)
- **State**: React Query (for API data)

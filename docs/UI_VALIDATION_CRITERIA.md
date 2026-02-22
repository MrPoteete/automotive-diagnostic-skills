# Cyberpunk UI Validation Criteria

## 1. 🎨 Atmospheric & Aesthetic
- [ ] **Dark Mode Only**: The interface must be primarily dark (Void Black/Deep Violet) with no "light mode" option.
- [ ] **Neon Contrast**: Interactive elements (buttons, links, active states) must use high-saturation neon colors (#00f0ff, #ff003c, #39ff14).
- [ ] **Scanline Effect**: A subtle CRT/Scanline overlay must be visible but not interfere with text readability.
- [ ] **Radial Vignette**: The corners of the screen should be noticeably darker than the center.

## 2. 🔠 Typography
- [ ] **Font Hierarchy**:
  - Headers: `Rajdhani` (Bold/SemiBold)
  - Data/Numbers: `Orbitron`
  - Body Text: `Roboto Mono`
- [ ] **Readability**: Despite the stylized fonts, body text must be legible (min 14px, good contrast).

## 3. 🧩 Component Design
- [ ] **"Shard" Cards**: Containers must not be simple rectangles. They should have at least one "cut" corner (clip-path).
- [ ] **Borders**: Borders should be thin (1px) with occasional "glowing" impacts or double lines.
- [ ] **Buttons**:
  - Hover state must trigger a "glitch" or "glow" effect.
  - Text must be uppercase with wide letter-spacing.
- [ ] **Input Fields**: Should look like command-line inputs (minimalist, blinking cursor).

## 4. 🎬 Animation & Motion
- [ ] **Glitch Effects**: Hovering over primary actions should trigger a subtle CSS chromatic aberration shift.
- [ ] **Pulse**: "Live" status indicators (e.g., connection status) must pulse.
- [ ] **Typing Effect**: Large blocks of text (like AI responses) should appear as if being typed out character-by-character.

## 5. 📱 Layout (The "HUD" Feel)
- [ ] **Fixed Frame**: The UI should feel like a fixed "cockpit" or HUD, not a scrolling web page.
- [ ] **Status Bar**: Always-visible top bar showing system stats (Time, Connection, etc.).
- [ ] **Sidebar**: Navigation should be distinct and accessible.

## 6. ⚠️ Feedback States
- [ ] **Success**: Toxic Green glow/text.
- [ ] **Error**: Neon Pink glow/text + "Malfunction" visual cue.
- [ ] **Loading**: Animated technical loader (not a standard spinner).

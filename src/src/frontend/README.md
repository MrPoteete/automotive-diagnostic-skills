# Automotive Diagnostic UI - Cyberpunk Edition

A high-tech, cyberpunk-themed diagnostic interface for the Automotive Diagnostic Skills system.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd src/frontend
npm install
```

### 2. Configure Environment

Create a `.env.local` file:

```bash
cp .env.example .env.local
```

Edit `.env.local` with your settings:
- `NEXT_PUBLIC_API_URL` - Backend API URL (default: `http://localhost:8000`)
- `NEXT_PUBLIC_API_KEY` - API key from `server/home_server.py` (default: `mechanic-secret-key-123`)

### 3. Start the Backend Server

In a separate terminal:

```bash
cd ../../server
python home_server.py
```

The backend should start on `http://localhost:8000`

### 4. Start the Frontend

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 🎨 Design System

This UI implements the cyberpunk design system from `docs/CYBERPUNK_UI_DESIGN.md`:

- **Colors**: Neon blues (#00f0ff), pinks (#ff003c), greens (#39ff14)
- **Fonts**: Rajdhani (headers), Orbitron (display), Roboto Mono (code)
- **Effects**: Scanlines, glitch animations, neon glows

### Validation Criteria

See `docs/UI_VALIDATION_CRITERIA.md` for the complete checklist.

## 🔌 API Integration

The UI connects to the FastAPI backend at `server/home_server.py`:

### Available Endpoints

1. **GET /** - Health check
2. **GET /search?query={query}&limit={limit}** - Search NHTSA complaints
3. **GET /search_tsbs?query={query}&limit={limit}** - Search TSBs

### Example Queries

- `"2018 Ford F-150 transmission shudder"`
- `"Chevrolet Silverado brake noise"`
- `"TSB RAM 1500 TIPM"`

## 📁 Project Structure

```
src/frontend/
├── app/
│   ├── components/       # React components
│   │   ├── CyberButton.tsx
│   │   ├── CyberInput.tsx
│   │   ├── LoadingState.tsx
│   │   ├── ShardCard.tsx
│   │   └── TypewriterText.tsx
│   ├── layout.tsx        # Root layout (fonts, scanlines)
│   ├── page.tsx          # Main diagnostic interface
│   └── globals.css       # Global styles + cyberpunk effects
├── lib/
│   └── api.ts            # API client for backend
├── .env.example          # Environment template
├── .env.local            # Your local config (gitignored)
└── tailwind.config.ts    # Tailwind + custom cyberpunk theme
```

## 🧪 Testing

### Test Backend Connection

1. Start the backend server
2. Open the UI - you should see "SYSTEM ONLINE" in the header
3. Try a sample query: `"Ford F-150 transmission"`

### Troubleshooting

**"SYSTEM OFFLINE" error:**
- Verify backend is running: `curl http://localhost:8000`
- Check API key matches in both `.env.local` and `server/home_server.py`
- Look for CORS errors in browser console

**No results returned:**
- Verify database exists at `database/automotive_complaints.db`
- Check backend logs in `server/server.log`
- Try simpler search terms

## 🎯 Next Steps

- [ ] Add vehicle selection form
- [ ] Implement DTC code lookup
- [ ] Add result filtering/sorting
- [ ] Confidence scoring visualization
- [ ] Safety alert highlighting

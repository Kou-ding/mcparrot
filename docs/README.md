# MCParrot GitHub Pages

This is the official website for MCParrot, served via GitHub Pages.

## Structure

- `index.html` — Main landing page
- `logs.html` — Conversation logs viewer
- `assets/css/style.css` — Styling
- `assets/js/main.js` — Main page JS
- `assets/js/logs.js` — Logs viewer logic
- `assets/images/` — Images referenced throughout

## Adding Logs

1. Place JSON log files in `logs/` (at repo root, or adjust path in `logs.js`)
2. Add an entry to `LOGS_INDEX` array in `assets/js/logs.js`
3. Push to main branch; GitHub Pages will auto-deploy.

## Setup

Enable GitHub Pages in repository Settings → Pages → Source → Branch: `main`, Folder: `/docs`.

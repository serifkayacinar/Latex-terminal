# LATEX TERMINAL

A Bloomberg-terminal-style dashboard for global natural rubber and latex prices, with country-level coverage for **Malaysia, Thailand, Indonesia, Vietnam, China, India** and a global benchmark from SGX RSS3 / TSR20. Five years of daily history, refreshed every 6 hours by GitHub Actions, hosted free on GitHub Pages.

![dashboard](https://img.shields.io/badge/data-5yr%20daily-amber) ![hosting](https://img.shields.io/badge/hosting-GitHub%20Pages-black) ![update](https://img.shields.io/badge/refresh-every%206h-green)

---

## What's tracked

| Code | Series | Country | Unit | Source tier |
|------|--------|---------|------|-------------|
| `RSS3_SGP` | RSS3 Singapore (benchmark) | Global | USD/kg | SGX/SICOM |
| `TSR20_SGP` | TSR20 SGX | Global | USD/kg | SGX |
| `SMR20_MYS` | SMR20 | Malaysia | USD/kg | Malaysian Rubber Board (MRE) |
| `LATEX_60_MYS` | Concentrated latex 60% DRC | Malaysia | USD/kg | MRB |
| `STR20_THA` | STR20 | Thailand | USD/kg | RAOT |
| `LATEX_60_THA` | Concentrated latex 60% DRC | Thailand | USD/kg | RAOT |
| `SIR20_IDN` | SIR20 | Indonesia | USD/kg | Gapkindo |
| `SVR3L_VNM` | SVR3L | Vietnam | USD/kg | VRG |
| `SVR10_VNM` | SVR10 | Vietnam | USD/kg | VRG |
| `RU_SHFE_CNY` | RU front-month | China | USD/kg eq. | SHFE |
| `TOCOM_RSS3` | RSS3 TOCOM | Japan ref. | USD/kg eq. | OSE/TOCOM |
| `RSS4_KOTTAYAM_INR` | RSS4 Kottayam | India | INR/100kg | Rubber Board India |

---

## Deploy in ~5 minutes

### 1. Create the GitHub repo
```bash
cd "LATEX price tracker"
git init
git add .
git commit -m "init: latex terminal"
gh repo create latex-terminal --public --source=. --push
# (or do it via the web: github.com/new -> upload these files)
```

### 2. Enable GitHub Pages
1. Open the repo on github.com
2. **Settings → Pages**
3. Source: **GitHub Actions** (not "Deploy from branch")
4. Wait ~1 min, then your URL appears: `https://<your-username>.github.io/latex-terminal/`

### 3. Enable workflow write permissions (so the bot can commit refreshed data)
1. **Settings → Actions → General**
2. Scroll to **Workflow permissions**
3. Select **Read and write permissions**
4. Save

### 4. Trigger the first data refresh manually
1. **Actions** tab → **Update latex prices** → **Run workflow**
2. After it completes, the homepage's "UPDATED" indicator switches from `SEED` to a UTC timestamp.

That's it. Share `https://<your-username>.github.io/latex-terminal/` with anyone — opens on phone & laptop, no login.

---

## How "updates whenever someone opens it" works

Static sites can't fetch from arbitrary commodity websites at view time (CORS + reliability). Instead:

1. A scheduled GitHub Action runs **every 6 hours**, scrapes the latest prints from MRB, RAOT, Investing.com, etc.
2. The Action commits the refreshed `data/prices.json` back to the repo.
3. GitHub Pages auto-redeploys.
4. When a viewer opens the page, their browser fetches `data/prices.json?ts=<cachebust>` — they always see the latest values committed to the repo (typically ≤6 h old).

Adjust the cron in `.github/workflows/update-prices.yml` if you want it more often (GitHub allows down to ~5 min).

---

## Local development

```bash
# generate seed historical data (only needed once)
python3 scripts/seed.py

# run the daily fetcher locally
pip install -r scripts/requirements.txt
python3 scripts/fetch.py

# preview the dashboard
python3 -m http.server 8000
# open http://localhost:8000
```

---

## Data sources

**Daily / live (scraped by `fetch.py`)**
- [SGX TSR20 futures](https://www.investing.com/commodities/rubber-tsr20-futures) via Investing.com
- [TOCOM RSS3](https://www.investing.com/commodities/rubber) via Investing.com (JPY → USD via Yahoo FX)
- [MRB Daily Prices](http://www3.lgm.gov.my/mre/Daily.aspx) — Malaysian Rubber Board (MYR → USD)
- [Rubber Board of India](https://rubberboard.gov.in/public) — Kottayam RSS4
- [SHFE RU futures](https://www.investing.com/commodities/rubber-ru-futures) (CNY/t → USD/kg)
- Yahoo Finance (`MYR=X`, `JPY=X`, `CNY=X`) — FX rates for unit conversion

**Historical baseline (built into `seed.py`, swappable)**
- [World Bank Pink Sheet](https://www.worldbank.org/en/research/commodity-markets) — monthly RSS3 SGP/MYS and TSR20 SGP, ~60 yr history
- [ANRPC monthly statistical bulletin](https://www.anrpc.org/) — Vietnam, Indonesia, Sri Lanka, India production-weighted prices
- Malaysian Rubber Council [archived monthly prices](https://www.myrubbercouncil.com/malaysia-rubber-price/)
- [Rubber Trade Association Singapore](https://www.rtas.sg/rubber-prices/) — SGX official settlement prices, last 3 months

**Reliability tiers** (which series are most/least likely to break)
1. **Tier 1 — futures via Investing.com** (TSR20, TOCOM, SHFE): updates daily but Investing.com sometimes hardens against scrapers; fallback to Barchart or RTAS if that happens.
2. **Tier 2 — official boards** (MRB, RAOT, India Rubber Board): very reliable but pages change format every year or two; expect minor parser maintenance.
3. **Tier 3 — country grades not on a public daily feed** (SVR, SIR, latex grades): seeded from monthly anchors and updated weekly via WB/ANRPC. For true daily granularity here you'd need a paid feed (Refinitiv, Helixtap, Argus, etc.).

---

## Customising

- **Add a new series** — edit `scripts/seed.py` (add a new entry in `SPREADS` and `DAILY_VOL`), regenerate `prices.json`, then write a fetcher in `scripts/fetch.py` and add it to `FETCHERS`.
- **Change theme** — all colors are CSS variables at the top of `index.html` (`:root { --amber: ...; --green: ...; }`).
- **Adjust refresh frequency** — `cron` line in `.github/workflows/update-prices.yml`.
- **Custom domain** — add a `CNAME` file with your domain, point a CNAME record at `<your-username>.github.io`, then enable HTTPS in **Settings → Pages**.

---

## Limitations & caveats

- The seed historical data is **interpolated from monthly anchors** with realistic noise — the *trends and ranges* match real published prices, but daily wiggles are synthetic for the period before the first live fetch. Each scheduled run progressively replaces today's seed value with a real scraped print.
- The dashboard is **reference only — not for trading**. Latency is hours, not real-time, and grade spreads are estimates.
- Scraping public sites is fragile. If Investing.com, MRB, or India Rubber Board changes their HTML, the affected series stops updating until the parser is patched. The dashboard keeps working with whatever data is in `prices.json`.

---

## License

MIT (do whatever you want, no warranty).

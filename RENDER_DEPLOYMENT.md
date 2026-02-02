# Render Deployment Checklist

## Required Setup in Render

Before deploying to Render, you **MUST** configure these in the Render dashboard:

### 1. REQUIRED (Bot will not work without these)

| What to Set | Where | Value | Where to Get It |
|-------------|-------|-------|-----------------|
| `KALSHI_API_KEY` | Environment Variable | Your API Key ID | [Kalshi Settings → API](https://kalshi.com/settings/api) |
| `kalshi_private_key` | **Secret File** ⭐ | Your full RSA private key | [Kalshi Settings → API](https://kalshi.com/settings/api) |
| `KALSHI_API_SECRET` | Environment Variable | `/etc/secrets/kalshi_private_key` | Points to the Secret File |

**Recommended Method:** Use Render's **Secret Files** for your private key (multi-line support built-in)!

### 2. CRITICAL SAFETY SETTING

| Variable | Recommended Value | Description |
|----------|-------------------|-------------|
| `AUTO_EXECUTE_TRADES` | `false` (for testing)<br>`true` (for live trading) | **IMPORTANT:** Start with `false` to test scanning only. Change to `true` when ready for live trading. |

## Optional Environment Variables (Already Set in render.yaml)

These have sensible defaults in `render.yaml`, but you can override them in the Render dashboard:

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `MAX_CAPITAL_PER_TRADE_PCT` | `0.05` | Risk 5% of capital per trade |
| `MAX_TOTAL_EXPOSURE_PCT` | `0.30` | Max 30% total exposure |
| `MIN_BALANCE_BUFFER` | `100.0` | Keep $100 safety buffer |
| `MARKET_SCAN_LIMIT` | `1000` | Scan up to 1000 markets |
| `SCAN_INTERVAL_SECONDS` | `30` | Scan every 30 seconds |
| `MIN_PROFIT_CENTS` | `2` | Min 2¢ profit per contract |
| `MAX_POSITION_SIZE` | `1000` | Max contracts per trade |
| `MIN_LIQUIDITY` | `10000` | Min $100 liquidity |
| `MIN_PROFIT_PER_DAY` | `0.1` | Min $0.10 daily profit |

---

## Step-by-Step Deployment

### 1. Create Render Account
- Go to [render.com](https://render.com) and sign up

### 2. Connect GitHub Repository
- In Render dashboard, click "New +"
- Select "Background Worker"
- Connect your GitHub account
- Select repository: `rch3232/kalshi-arbitrage-bot`
- Select branch: `claude/kalshi-bot-setup-OmpF6`

### 3. Configure Environment Variables & Secret Files

#### Option A: Using Secret Files (RECOMMENDED) ⭐
Secret Files are designed for multi-line secrets like private keys.

**In Environment tab:**
1. Add Environment Variable:
   - `KALSHI_API_KEY` = [Your API Key ID from Kalshi]

2. Create Secret File (scroll to "Secret Files" section):
   - Filename: `kalshi_private_key`
   - Contents: [Paste your FULL RSA private key including -----BEGIN/END----- lines]

3. Add Environment Variable to point to the file:
   - `KALSHI_API_SECRET` = `/etc/secrets/kalshi_private_key`

4. Add safety setting:
   - `AUTO_EXECUTE_TRADES` = `false`

**See [RENDER_SECRET_FILE_GUIDE.md](RENDER_SECRET_FILE_GUIDE.md) for detailed instructions.**

#### Option B: Using Base64 Environment Variable (Alternative)
If you prefer not to use Secret Files:

1. Run `python encode_key.py` locally to convert your key to base64
2. Add Environment Variables:
   - `KALSHI_API_KEY` = [Your API Key ID]
   - `KALSHI_API_SECRET` = [Base64-encoded private key]
   - `AUTO_EXECUTE_TRADES` = `false`

### 4. Deploy
- Click "Create Background Worker"
- Wait for deployment to complete
- Check logs to verify bot is scanning markets

### 5. Enable Live Trading (When Ready)
- Go to Environment tab
- Change `AUTO_EXECUTE_TRADES` to `true`
- Save changes (bot will automatically restart)

---

## Testing Before Live Trading

**CRITICAL:** Always test in dry-run mode first:

1. Set `AUTO_EXECUTE_TRADES=false`
2. Deploy and monitor logs for 24 hours
3. Verify bot finds opportunities correctly
4. Check that capital calculations look correct
5. Only then enable `AUTO_EXECUTE_TRADES=true`

---

## Monitoring Your Bot

### View Logs
1. Go to Render dashboard
2. Click on your worker
3. Click "Logs" tab
4. You'll see:
   - Capital status on startup
   - Market scans every 30 seconds
   - Opportunities found
   - Trades executed (if auto-execute enabled)
   - Statistics every 10 scans

### Expected Log Output
```
======================================================================
CAPITAL STATUS
======================================================================
Total Balance: $1000.00
Available Capital: $900.00
Max Per Trade: $45.00 (5.0%)
Max Total Exposure: $270.00 (30.0%)
======================================================================

Starting market scan #1
Scanned 1000 markets, 487 passed liquidity filter
✅ Found 12 opportunities
```

---

## Cost

- **Starter Plan:** $7/month (sufficient for this bot)
- **Standard Plan:** $25/month (if you need more resources)

The bot is lightweight and Starter plan should work fine.

---

## Security Best Practices

1. ✅ **NEVER** commit your API keys to GitHub
2. ✅ Set API keys only in Render dashboard (never in code)
3. ✅ Start with `AUTO_EXECUTE_TRADES=false` for testing
4. ✅ Monitor logs regularly
5. ✅ Set conservative risk limits initially

---

## Troubleshooting

### Bot Won't Start
- Check that `KALSHI_API_KEY` and `KALSHI_API_SECRET` are set correctly
- Verify API keys are valid in Kalshi dashboard

### No Opportunities Found
- This is normal! Not every scan finds opportunities
- Bot scans every 30 seconds, so be patient
- Check logs for any API errors

### Want to Stop Trading
- Set `AUTO_EXECUTE_TRADES=false` in Environment tab
- Or pause/delete the worker in Render dashboard

---

## Quick Reference: Minimum Setup

**Only 3 variables required to start:**

1. `KALSHI_API_KEY` = [your key]
2. `KALSHI_API_SECRET` = [your secret]
3. `AUTO_EXECUTE_TRADES` = `false` (for testing) or `true` (for live trading)

Everything else has sensible defaults! 🚀

---

## 🔒 Safety Features

The bot includes several safety mechanisms:

1. **IOC (Immediate or Cancel) Orders** - All trades use IOC orders by default
   - Orders either fill immediately or get cancelled automatically
   - No hanging orders in the orderbook
   - Prevents one-sided exposure from unfilled orders

2. **Order Fill Verification** - Bot checks that both legs of arbitrage executed
   - Warns if sell order fails after buy order fills
   - Tracks order status to detect partial fills

3. **Dynamic Capital Management** - Automatically adjusts position sizes
   - Never risks more than configured percentage per trade
   - Maintains minimum balance buffer

4. **Rate Limiting** - Respects API limits to avoid throttling

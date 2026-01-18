# Render Secret File Setup Guide

## 🎯 Using Secret Files for Your Private Key (RECOMMENDED)

Secret Files are Render's built-in feature for storing multi-line secrets like RSA private keys. This is **much cleaner** than trying to paste multi-line keys into environment variables.

---

## 📋 Step-by-Step Setup

### 1. Create the Background Worker in Render
- Go to [render.com](https://render.com)
- Click "New +" → "Background Worker"
- Connect your GitHub repo: `rch3232/kalshi-arbitrage-bot`
- Select branch: `claude/kalshi-bot-setup-OmpF6`

### 2. Add Your API Key (Environment Variable)
In the **Environment** tab:
- Click "Add Environment Variable"
- Key: `KALSHI_API_KEY`
- Value: `your-api-key-id-from-kalshi`

### 3. Create a Secret File for Your Private Key
In the **Environment** tab:
- Scroll down to "Secret Files" section
- Click "Add Secret File"

**Configure the Secret File:**
- **Filename**: `kalshi_private_key` (or any name you want)
- **Contents**: Paste your FULL private key, including:
  ```
  -----BEGIN RSA PRIVATE KEY-----
  MIIEvgIBADANBgkqhkiG9w0BAQEFAASC...
  (all the lines)
  ...
  -----END RSA PRIVATE KEY-----
  ```
- Click "Save"

### 4. Set KALSHI_API_SECRET to Point to the Secret File
In the **Environment** tab (Environment Variables section):
- Click "Add Environment Variable"
- Key: `KALSHI_API_SECRET`
- Value: `/etc/secrets/kalshi_private_key`

**Important:** The path is always `/etc/secrets/[filename]` where `[filename]` is what you named your secret file.

### 5. Set Auto-Execute Mode
In the **Environment** tab:
- Click "Add Environment Variable"
- Key: `AUTO_EXECUTE_TRADES`
- Value: `false` (for testing) or `true` (for live trading)

### 6. Deploy!
- Click "Create Background Worker"
- Render will build and deploy your bot
- The bot will automatically read the private key from the secret file

---

## ✅ What You Should See in Logs

After deployment, check the logs. You should see:

```
✅ Reading private key from file: /etc/secrets/kalshi_private_key
✅ Loaded private key from file (1704 chars)
✅ Private key appears valid (27 lines)
✅ Kalshi SDK initialized successfully

======================================================================
CAPITAL STATUS
======================================================================
Total Balance: $1000.00
...

Starting market scan #1
Scanned 1000 markets, 487 passed liquidity filter
```

---

## 🔄 Updating Your Private Key

To update the private key later:
1. Go to your worker in Render dashboard
2. Click "Environment" tab
3. Scroll to "Secret Files" section
4. Click the edit icon next to `kalshi_private_key`
5. Update the contents
6. Save (Render will automatically redeploy)

---

## 📊 Summary: Secret Files vs Environment Variables

| Method | Pros | Cons |
|--------|------|------|
| **Secret Files** ✅ | • Multi-line support<br>• No escaping needed<br>• Purpose-built for keys<br>• Easy to update | • Requires 2 steps (file + env var) |
| **Base64 Env Var** | • Single step<br>• One variable | • Must encode first<br>• Less obvious what it is |
| **Direct Env Var** | • Simplest concept | • Doesn't work (line break issues) |

**Recommendation: Use Secret Files** - they're designed for exactly this use case!

---

## 🔒 Security Notes

- Secret Files are encrypted at rest by Render
- They're mounted read-only at runtime
- Only accessible to your service
- Never logged or exposed in UI after creation
- Perfect for private keys, certificates, etc.

---

## 🎯 Quick Reference

**3 Things to Set:**

1. **Environment Variable**: `KALSHI_API_KEY` = `your-api-key-id`
2. **Secret File**: `kalshi_private_key` = `[your full RSA private key]`
3. **Environment Variable**: `KALSHI_API_SECRET` = `/etc/secrets/kalshi_private_key`
4. **Environment Variable**: `AUTO_EXECUTE_TRADES` = `false` or `true`

That's it! 🚀

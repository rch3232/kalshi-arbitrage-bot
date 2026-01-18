# Kalshi Arbitrage Trading Bot

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/Code%20Style-PEP%208-orange.svg)](https://www.python.org/dev/peps/pep-0008/)

> **An intelligent trading system designed to identify and capitalize on arbitrage opportunities in Kalshi prediction markets.**

The Kalshi Arbitrage Trading Bot is a professional-grade Python application that continuously monitors market conditions and identifies two distinct types of profitable trading opportunities. With an intuitive interactive menu system and comprehensive automation capabilities, the bot makes sophisticated market analysis accessible to traders of all experience levels.

**Repository**: [kalshi-arbitrage-bot](https://github.com/vladmeer/kalshi-arbitrage-bot)

---

## ✨ Key Features

### 🎯 **Dual Opportunity Detection**
- **Probability Arbitrage**: Identifies markets where YES and NO contract probabilities don't sum to 100%, creating risk-free profit opportunities
- **Spread Trading**: Finds orderbook inefficiencies where bid prices exceed ask prices, enabling instant profit through simultaneous buy and sell execution

### 💼 **Professional Features**
- **Interactive Menu System**: User-friendly interface with arrow key navigation (no command-line arguments needed!)
- **Dynamic Capital Management**: Automatically adjusts trade sizes based on your Kalshi balance
- **Maximum Market Coverage**: Scans up to 1000 markets per iteration for comprehensive opportunity detection
- **Intelligent Fee Calculation**: Accurate cost analysis ensuring realistic profit projections
- **Automated Execution**: Optional automatic trade execution with comprehensive safety controls
- **Continuous Monitoring**: Long-term market surveillance with customizable scan intervals
- **Risk Management**: Built-in position sizing, liquidity filtering, and profit thresholds
- **Cloud Deployment Ready**: Pre-configured for one-click deployment on Render

### 🛡️ **Production-Ready**
- **Robust Error Handling**: Graceful handling of API failures, rate limits, and network issues
- **Rate Limiting**: Intelligent API rate limit management with automatic backoff
- **Type Safety**: Comprehensive type hints for better IDE support and maintainability
- **Modular Architecture**: Clean, well-organized codebase following best practices

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** installed on your system
- **Kalshi API credentials** (API Key ID and Private Key)
- **pip** (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/vladmeer/kalshi-arbitrage-bot.git
   cd kalshi-arbitrage-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your API credentials**
   
   Create a `.env` file in the project root:
   ```bash
   # Create .env file
   # Windows: copy .env.example .env
   # Linux/Mac: cp .env.example .env
   ```
   
   Then edit `.env` with your Kalshi API credentials:
   ```env
   KALSHI_API_KEY=your_api_key_id_here
   KALSHI_API_SECRET=your_private_key_here
   KALSHI_API_BASE_URL=https://api.elections.kalshi.com/trade-api/v2
   MIN_PROFIT_PER_DAY=0.1
   MAX_POSITION_SIZE=1000
   MIN_PROFIT_CENTS=2
   ```
   
   > **💡 Tip**: Find your API credentials in your Kalshi account settings:
   > - **API Key ID** → use for `KALSHI_API_KEY`
   > - **Private Key** → use for `KALSHI_API_SECRET`

4. **Run the bot**
   ```bash
   python main.py
   ```

---

## 🚀 Cloud Deployment (Render)

Deploy the bot as a 24/7 background worker on Render with automatic capital management:

### Quick Deploy to Render

1. **Fork or push this repository to GitHub**

2. **Create a Render account** at [render.com](https://render.com)

3. **Create a new Background Worker**:
   - Click "New +" → "Background Worker"
   - Connect your GitHub repository
   - Render will auto-detect the `render.yaml` configuration

4. **Configure Environment Variables** in Render Dashboard:
   - `KALSHI_API_KEY` - Your Kalshi API Key ID
   - `KALSHI_API_SECRET` - Your Kalshi Private Key
   - `AUTO_EXECUTE_TRADES` - Set to `true` to enable auto-trading
   - All other variables have sensible defaults in `render.yaml`

5. **Deploy!**
   - Click "Create Background Worker"
   - The bot will start running continuously
   - View logs in the Render dashboard

### Key Configuration for Deployment

The bot is configured to:
- ✅ **Scan 1000 markets** every 5 minutes (maximum coverage)
- ✅ **Auto-size trades** based on your Kalshi balance (5% per trade, 30% total exposure)
- ✅ **Run 24/7** with automatic restart on errors
- ✅ **Maintain $100 balance buffer** for safety

### Local Testing Before Deployment

Test the worker locally before deploying:
```bash
# Set AUTO_EXECUTE_TRADES=false for dry-run testing
python worker.py
```

---

## 📖 Usage Guide

### Interactive Menu (Recommended)

Simply run `python main.py` without any arguments to launch the interactive menu:

```
======================================================================
  KALSHI ARBITRAGE TRADING BOT - Interactive Menu
======================================================================

Select an option (Use ↑↓ arrows, Enter to select):
→ 📊 Single Scan (All Opportunities)
  📈 Scan Spread Trading Opportunities Only
  🎯 Scan Probability Arbitrage Opportunities Only
  🔄 Continuous Monitoring Mode
  ⚙️  Configure Settings
  ❌ Exit
```

### Menu Options Explained

#### 📊 **Single Scan (All Opportunities)**
Performs a comprehensive one-time scan of markets, identifying both probability arbitrage and spread trading opportunities. Perfect for quick market analysis.

**Configuration prompts:**
- Number of markets to scan (default: 100)
- Display all opportunities or just top 10
- Enable automatic trade execution (⚠️ use with caution)

#### 📈 **Scan Spread Trading Opportunities Only**
Focuses exclusively on immediate spread trading opportunities where you can buy low and sell high instantly.

**Configuration prompts:**
- Number of markets to scan
- Display preferences
- Auto-execution option

#### 🎯 **Scan Probability Arbitrage Opportunities Only**
Analyzes markets specifically for probability arbitrage where contract probabilities deviate from expected values.

**Configuration prompts:**
- Number of markets to scan
- Display preferences

#### 🔄 **Continuous Monitoring Mode**
Runs the bot in continuous mode, periodically scanning markets for new opportunities. Ideal for long-term monitoring and automated trading strategies.

**Configuration prompts:**
- Scan interval in seconds (default: 300 = 5 minutes)
- Number of markets per scan iteration
- Auto-execution option
- Maximum number of scans (or unlimited)

#### ⚙️ **Configure Settings**
Adjust bot configuration parameters such as minimum liquidity requirements.

---

## 🧠 How It Works

### 1. Probability Arbitrage Detection

Probability arbitrage occurs when the combined YES and NO contract probabilities don't equal 100%, indicating a market inefficiency.

**Example Scenario:**
- YES contracts trading at **52¢**
- NO contracts trading at **50¢**
- **Total: 102%** → 2% arbitrage opportunity

**How it works:**
1. Fetches active markets from Kalshi API
2. Calculates total probability (YES price + NO price)
3. Identifies markets where total ≠ 100%
4. Calculates gross profit and net profit (after fees)
5. Ranks opportunities by profit per day based on expiration date

### 2. Spread Trading Detection

Spread trading opportunities arise when orderbook bid prices exceed ask prices, enabling simultaneous buy and sell execution for instant profit.

**Example Scenario:**
- Best bid: **43¢** (highest price buyers are willing to pay)
- Best ask: **42¢** (lowest price sellers are willing to accept)
- **Profit: 1¢ per contract** (minus trading fees)

**How it works:**
1. Scans orderbooks for profitable spreads
2. Identifies cases where bid > ask
3. Calculates net profit after fees
4. Optionally executes trades automatically

### Comparison & Recommendations

The bot intelligently compares both opportunity types and provides recommendations:
- **Spread Trading**: Instant profit, no waiting required
- **Probability Arbitrage**: Time-based profit, requires holding until expiration

---

## 🏗️ Architecture

The codebase follows a clean, modular architecture with clear separation of concerns:

### Core Modules

- **`main.py`** - Main orchestration layer with interactive menu system
- **`worker.py`** - Background worker for continuous 24/7 operation (cloud deployment)
- **`src/market_api.py`** - Professional API client with rate limiting and error handling
- **`src/capital_manager.py`** - Dynamic position sizing based on portfolio balance
- **`src/opportunity_analyzer.py`** - Advanced market analysis for probability arbitrage detection
- **`src/execution_engine.py`** - Orderbook analysis and trade execution system
- **`src/cost_calculator.py`** - Comprehensive fee calculation engine

### Design Principles

- **Modular Design**: Each module has a single, well-defined responsibility
- **Error Resilience**: Comprehensive error handling with graceful degradation
- **Type Safety**: Full type hints throughout for better IDE support
- **Configuration Management**: Environment-based configuration with sensible defaults
- **Production Ready**: Safe defaults, comprehensive logging, and thorough testing

---

## 💰 Fee Structure

The bot uses an accurate approximation of Kalshi's tiered fee structure:

| Contract Price Range | Fee Rate |
|---------------------|----------|
| Near 50¢ (40-60¢) | ~3.5% (highest) |
| Medium (30-40¢, 60-70¢) | ~3.0% |
| Low-Medium (20-30¢, 70-80¢) | ~2.5% |
| Low (10-20¢, 80-90¢) | ~2.0% |
| Extremes (0-10¢, 90-100¢) | ~1.0% (lowest) |

**Additional Considerations:**
- **Maker orders** (limit orders): 50% fee discount
- **Taker orders** (market orders): Full fee rate

> **Note**: Actual fees may vary. Check Kalshi's official fee schedule for precise values.

---

## 📊 Example Output

```
======================================================================
SPREAD TRADING OPPORTUNITIES: Found 3 profitable opportunities!
======================================================================

[1] ============================================================
Market: Will Bitcoin reach $50,000 by end of month?
Ticker: BTC-50K-JAN
Side: YES
Buy Price: 42¢
Sell Price: 43¢
Spread: 1¢
Quantity: 100 contracts

Profit Analysis:
  Gross Profit: $1.00
  Net Profit (after fees): $0.85
  Profit per Contract: $0.0085
============================================================

======================================================================
PROBABILITY ARBITRAGE OPPORTUNITIES: Found 2 profitable opportunities!
======================================================================

[1] ============================================================
Market: Will Bitcoin reach $50,000 by end of month?
Ticker: BTC-50K-JAN
Total Probability: 102.5%
Deviation from 100%: 2.50%
Expiration: 2024-01-31 23:59:59
Days to Expiration: 16.50

Profit Analysis:
  Gross Profit: $25.00
  Net Profit (after fees): $22.50
  Profit per Day: $1.36

Recommended Trades:
  1. SELL 100 contracts of BTC-50K-JAN-YES at 52¢ (side: yes)
  2. SELL 100 contracts of BTC-50K-JAN-NO at 50¢ (side: no)
============================================================
```

---

## ⚙️ Configuration

### Environment Variables

You can customize the bot's behavior by editing your `.env` file:

#### Required Credentials
| Variable | Description | Default |
|----------|-------------|---------|
| `KALSHI_API_KEY` | Your Kalshi API Key ID | Required |
| `KALSHI_API_SECRET` | Your Kalshi Private Key | Required |
| `KALSHI_API_BASE_URL` | Kalshi API endpoint | `https://api.elections.kalshi.com/trade-api/v2` |

#### Capital Management (NEW)
| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_CAPITAL_PER_TRADE_PCT` | Max % of capital per trade | `0.05` (5%) |
| `MAX_TOTAL_EXPOSURE_PCT` | Max % of capital exposed total | `0.30` (30%) |
| `MIN_BALANCE_BUFFER` | Minimum balance buffer | `100.0` ($100) |

#### Trading Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `MIN_PROFIT_PER_DAY` | Minimum profit per day for arbitrage | `0.1` ($0.10) |
| `MAX_POSITION_SIZE` | Maximum contracts per trade | `1000` |
| `MIN_PROFIT_CENTS` | Minimum profit in cents per contract | `2` |
| `MIN_LIQUIDITY` | Minimum liquidity in cents | `10000` ($100) |

#### Background Worker Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `AUTO_EXECUTE_TRADES` | Enable auto-trading | `false` |
| `MARKET_SCAN_LIMIT` | Markets to scan per iteration | `1000` |
| `SCAN_INTERVAL_SECONDS` | Time between scans | `300` (5 min) |

### Smart Defaults

The bot automatically calculates minimum profitable opportunities based on actual trading fees. Any opportunity with positive net profit (after fees) will be considered, ensuring you don't miss profitable opportunities even if they're very small.

---

## ⚠️ Important Notes & Warnings

### Safety First

- **⚠️ Auto-Execute Warning**: Enabling auto-execute in the interactive menu will automatically place trades using real money. Use with extreme caution and test thoroughly first. Always monitor your account and positions.

- **API Access**: You need valid Kalshi API credentials to use this bot. Ensure your credentials are correctly configured in the `.env` file.

- **Market Hours**: Kalshi operates nearly 24/7 with occasional maintenance windows.

- **Risk Management**: 
  - Arbitrage opportunities may be fleeting and require quick execution
  - Ensure markets have sufficient liquidity before executing trades
  - Test thoroughly with small positions before scaling up

- **Order Execution**: Limit orders are used by default for safety. Market orders may execute at worse prices but provide instant execution.

### Best Practices

1. **Start Small**: Begin by scanning a small number of markets (10-50) with low liquidity thresholds to test
2. **Dry Run First**: Use the interactive menu and disable auto-execute to see opportunities first
3. **Monitor Closely**: Watch output and verify behavior matches expectations
4. **Understand Risks**: Trading involves risk - only trade what you can afford to lose

---

## 🧪 Testing & Validation

Before using with real money:

1. **Dry Run**: Use the interactive menu and select options without enabling auto-execute to see opportunities
   ```bash
   python main.py
   ```

2. **Small Test**: Start with limited markets (10-50) and low liquidity thresholds using the interactive menu

3. **Monitor Output**: Watch the output and verify behavior matches expectations

4. **Gradual Scaling**: Gradually increase limits and liquidity as you gain confidence

---

## 📝 Disclaimer

**This bot is for educational and informational purposes only.**

Trading involves risk, and past performance does not guarantee future results. Always:
- Understand the risks involved
- Test thoroughly before using real money
- Monitor your positions regularly
- Comply with Kalshi's terms of service
- Consult with financial advisors if needed

The authors and contributors are not responsible for any financial losses incurred through the use of this software.

---

## 👤 Author

**vladmeer**

Built with Python 3.8+, demonstrating production-ready software engineering practices.

### Contact

- **Telegram**: [@vladmeer67](https://t.me/vladmeer67)
- **X (Twitter)**: [@vladmeer67](https://x.com/vladmeer67)
- **GitHub**: [@vladmeer](https://github.com/vladmeer)

---

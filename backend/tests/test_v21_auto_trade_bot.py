import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

BACKEND = Path(__file__).parents[1]
sys.path.insert(0, str(BACKEND))

from app import v21_demo  # noqa: E402


class AutoTradeBotTests(unittest.TestCase):
    def test_scan_100_symbols_and_filter_invalid_symbols(self):
        symbols = []
        tickers = []
        for index in range(105):
            symbol = f"COIN{index}USDT"
            symbols.append({"symbol": symbol, "baseAsset": f"COIN{index}", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT"})
            tickers.append({"symbol": symbol, "quoteVolume": str(1_000_000 + index), "lastPrice": "100", "priceChangePercent": "1"})
        symbols.extend([
            {"symbol": "USDCUSDT", "baseAsset": "USDC", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT"},
            {"symbol": "BADUSDT", "baseAsset": "BAD", "status": "BREAK", "contractType": "PERPETUAL", "quoteAsset": "USDT"},
            {"symbol": "BADUSD", "baseAsset": "BAD", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USD"},
        ])
        result = v21_demo.dynamic_auto_universe({"symbols": symbols}, tickers, v21_demo.DEFAULT_SETTINGS)
        self.assertEqual(len(result), 100)
        self.assertNotIn("USDCUSDT", result)
        self.assertNotIn("BADUSDT", result)
        self.assertNotIn("BADUSD", result)

    def test_default_universe_ignores_legacy_fixed_24_coin_allowlist(self):
        symbols = []
        tickers = []
        for index in range(30):
            symbol = f"COIN{index}USDT"
            symbols.append({"symbol": symbol, "baseAsset": f"COIN{index}", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT"})
            tickers.append({"symbol": symbol, "quoteVolume": str(1_000_000 + index), "lastPrice": "100", "priceChangePercent": "1"})
        result = v21_demo.dynamic_auto_universe({"symbols": symbols}, tickers, v21_demo.DEFAULT_SETTINGS)
        self.assertEqual(len(result), 30)
        self.assertEqual(result[0], "COIN29USDT")
        self.assertTrue(all(symbol in result for symbol in ("COIN0USDT", "COIN1USDT", "COIN29USDT")))

    def test_daily_loss_thresholds_and_deduplication(self):
        state = v21_demo.initial_state()
        state["risk"]["daily_base_balance"] = 1000.0
        state["journal"] = [{"kind": "FILL", "created_at": v21_demo.now_iso(), "realized_pnl": -50.0, "verified_realized": True}]
        result = v21_demo.refresh_daily_risk_state(state, 1000.0)
        self.assertEqual(result["loss_pct"], 5.0)
        self.assertEqual(state["notifications"]["unread"], 1)
        v21_demo.refresh_daily_risk_state(state, 1000.0)
        self.assertEqual(state["notifications"]["unread"], 1)

    def test_daily_loss_20_pauses_without_closing_existing(self):
        state = v21_demo.initial_state()
        state["auto"].update({"enabled": True, "status": "ON"})
        state["risk"]["daily_base_balance"] = 1000.0
        state["journal"] = [{"kind": "FILL", "created_at": v21_demo.now_iso(), "realized_pnl": -200.0, "verified_realized": True}]
        result = v21_demo.refresh_daily_risk_state(state, 1000.0)
        self.assertTrue(result["paused"])
        self.assertEqual(state["auto"]["pause_reason"], "DAILY_LOSS_20")
        self.assertEqual(len(state["notifications"]["seen"]), 4)

    def test_rotation_keeps_losing_position_and_only_returns_auto_safe_symbols(self):
        snapshot = {"positions": [
            {"symbol": "BTCUSDT", "unrealized_pnl": -2.0},
            {"symbol": "ETHUSDT", "unrealized_pnl": 1.0},
        ]}
        plans = {
            "auto-btc": {"symbol": "BTCUSDT", "source": "AUTO_SCANNER", "position_status": "OPEN"},
            "auto-eth": {"symbol": "ETHUSDT", "source": "AUTO_SCANNER", "position_status": "OPEN"},
            "manual-sol": {"symbol": "SOLUSDT", "source": "MANUAL", "position_status": "OPEN"},
        }
        self.assertEqual(v21_demo.safe_rotation_symbols(snapshot, {"SOLUSDT"}, plans), ["ETHUSDT"])

    def test_live_mode_rejected_and_testnet_host_remains_only_execution_host(self):
        source = (BACKEND / "app" / "binance_demo.py").read_text(encoding="utf-8")
        self.assertIn('DEMO_REST_BASE = "https://demo-fapi.binance.com"', source)
        self.assertNotIn('https://fapi.binance.com', source)
        self.assertIn('source="AUTO_SCANNER"', (BACKEND / "app" / "v21_demo.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

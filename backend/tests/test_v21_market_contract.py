import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

BACKEND = Path(__file__).parents[1]
sys.path.insert(0, str(BACKEND))

from app import v21_demo  # noqa: E402


class V21MarketContractTests(unittest.TestCase):
    def test_market_universe_uses_authoritative_demo_filters(self):
        exchange_info = {"symbols": [
            {"symbol": "BTCUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT"},
            {"symbol": "ETHUSDT", "status": "BREAK", "contractType": "PERPETUAL", "quoteAsset": "USDT"},
            {"symbol": "DOGEUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT"},
            {"symbol": "ETHUSD", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USD"},
            {"symbol": "BTCUSDT_240628", "status": "TRADING", "contractType": "CURRENT_QUARTER", "quoteAsset": "USDT"},
        ]}
        tickers = [
            {"symbol": "BTCUSDT", "lastPrice": "100", "priceChangePercent": "1", "quoteVolume": "10"},
            {"symbol": "DOGEUSDT", "lastPrice": "0.1", "priceChangePercent": "2", "quoteVolume": "20"},
        ]
        client = SimpleNamespace(public_get=AsyncMock(side_effect=[exchange_info, tickers]))
        application = SimpleNamespace(state=SimpleNamespace(http=object()))
        with patch.object(v21_demo, "market_client_for", return_value=client):
            result = asyncio.run(v21_demo.auto_trade_market_universe(application))
        self.assertEqual([item["symbol"] for item in result], ["DOGEUSDT", "BTCUSDT"])
        self.assertTrue(all(item["symbol"] in v21_demo.AUTO_TRADE_SYMBOL_SET for item in result))

    def test_frontend_uses_backend_contract_without_twelve_limit(self):
        source = (BACKEND.parent / "frontend" / "src" / "TestnetFirstApp.tsx").read_text(encoding="utf-8")
        self.assertIn("/v21/markets", source)
        self.assertNotIn("/markets?limit=12", source)
        self.assertIn("marketQuery", source)

    def test_demo_and_live_hosts_remain_separate(self):
        source = (BACKEND / "app" / "v21_demo.py").read_text(encoding="utf-8")
        self.assertIn("demo_only", source)
        self.assertNotIn("https://fapi.binance.com", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
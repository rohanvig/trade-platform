from typing import Any

BTC_INDEX_PAYLOAD: dict[str, Any] = {
    "jsonrpc": "2.0",
    "result": {
        "index_price": 68435.12,
        "estimated_delivery_price": 68420.50,
    },
}

ETH_INDEX_PAYLOAD: dict[str, Any] = {
    "jsonrpc": "2.0",
    "result": {
        "index_price": 3520.75,
        "estimated_delivery_price": 3518.00,
    },
}

# 12 consecutive 1H ticks starting at 2026-11-01 00:00:00 UTC (1761955200000 ms)
# 3 complete 4-hour buckets: [00:00, 04:00), [04:00, 08:00), [08:00, 12:00)
BASE_TS = 1761955200000
TICKS_1H = [BASE_TS + (i * 3600 * 1000) for i in range(12)]
OPENS_1H = [68000.0 + (i * 100.0) for i in range(12)]
HIGHS_1H = [o + 250.0 for o in OPENS_1H]
LOWS_1H = [o - 150.0 for o in OPENS_1H]
CLOSES_1H = [o + 50.0 for o in OPENS_1H]
VOLUMES_1H = [100.0 + (i * 10.0) for i in range(12)]

CHART_DATA_1H_PAYLOAD: dict[str, Any] = {
    "jsonrpc": "2.0",
    "result": {
        "status": "ok",
        "ticks": TICKS_1H,
        "open": OPENS_1H,
        "high": HIGHS_1H,
        "low": LOWS_1H,
        "close": CLOSES_1H,
        "volume": VOLUMES_1H,
    },
}

TICKS_1D = [BASE_TS + (i * 86400 * 1000) for i in range(10)]
OPENS_1D = [65000.0 + (i * 500.0) for i in range(10)]
HIGHS_1D = [o + 1000.0 for o in OPENS_1D]
LOWS_1D = [o - 800.0 for o in OPENS_1D]
CLOSES_1D = [o + 300.0 for o in OPENS_1D]
VOLUMES_1D = [1500.0 + (i * 50.0) for i in range(10)]

CHART_DATA_1D_PAYLOAD: dict[str, Any] = {
    "jsonrpc": "2.0",
    "result": {
        "status": "ok",
        "ticks": TICKS_1D,
        "open": OPENS_1D,
        "high": HIGHS_1D,
        "low": LOWS_1D,
        "close": CLOSES_1D,
        "volume": VOLUMES_1D,
    },
}

# Active instruments with multiple expiries (2026-12-25 and 2027-01-29)
# 2026-12-25 08:00:00 UTC = 1798185600000
# 2027-01-29 08:00:00 UTC = 1801209600000
EXPIRY_1_TS = 1798185600000
EXPIRY_2_TS = 1801209600000

BTC_INSTRUMENTS_PAYLOAD: dict[str, Any] = {
    "jsonrpc": "2.0",
    "result": [
        {
            "instrument_name": "BTC-25DEC26-100000-C",
            "strike": 100000.0,
            "option_type": "call",
            "expiration_timestamp": EXPIRY_1_TS,
            "contract_size": 1.0,
            "settlement_currency": "BTC",
            "quote_currency": "BTC",
            "state": "open",
            "is_active": True,
        },
        {
            "instrument_name": "BTC-25DEC26-100000-P",
            "strike": 100000.0,
            "option_type": "put",
            "expiration_timestamp": EXPIRY_1_TS,
            "contract_size": 1.0,
            "settlement_currency": "BTC",
            "quote_currency": "BTC",
            "state": "open",
            "is_active": True,
        },
        {
            "instrument_name": "BTC-25DEC26-120000-C",
            "strike": 120000.0,
            "option_type": "call",
            "expiration_timestamp": EXPIRY_1_TS,
            "contract_size": 1.0,
            "settlement_currency": "BTC",
            "quote_currency": "BTC",
            "state": "open",
            "is_active": True,
        },
        {
            "instrument_name": "BTC-29JAN27-100000-C",
            "strike": 100000.0,
            "option_type": "call",
            "expiration_timestamp": EXPIRY_2_TS,
            "contract_size": 1.0,
            "settlement_currency": "BTC",
            "quote_currency": "BTC",
            "state": "open",
            "is_active": True,
        },
        # Inactive / Closed contract - must be excluded
        {
            "instrument_name": "BTC-25DEC26-90000-C",
            "strike": 90000.0,
            "option_type": "call",
            "expiration_timestamp": EXPIRY_1_TS,
            "contract_size": 1.0,
            "settlement_currency": "BTC",
            "quote_currency": "BTC",
            "state": "closed",
            "is_active": False,
        },
    ],
}

BTC_BOOK_SUMMARY_PAYLOAD: dict[str, Any] = {
    "jsonrpc": "2.0",
    "result": [
        {
            "instrument_name": "BTC-25DEC26-100000-C",
            "mark_price": 0.045,
            "bid_price": 0.043,
            "ask_price": 0.047,
            "mark_iv": 62.4,
            "open_interest": 1542.0,
            "volume_usd": 450000.0,
        },
        {
            "instrument_name": "BTC-25DEC26-100000-P",
            "mark_price": 0.038,
            "bid_price": 0.036,
            "ask_price": 0.040,
            "mark_iv": 59.8,
            "open_interest": 980.0,
            "volume_usd": 280000.0,
        },
        # BTC-25DEC26-120000-C is illiquid with null bid/ask
        {
            "instrument_name": "BTC-25DEC26-120000-C",
            "mark_price": 0.012,
            "bid_price": None,
            "ask_price": None,
            "mark_iv": 70.1,
            "open_interest": 45.0,
            "volume_usd": 1200.0,
        },
        {
            "instrument_name": "BTC-29JAN27-100000-C",
            "mark_price": 0.065,
            "bid_price": 0.062,
            "ask_price": 0.068,
            "mark_iv": 64.0,
            "open_interest": 620.0,
            "volume_usd": 150000.0,
        },
    ],
}

ETH_INSTRUMENTS_PAYLOAD: dict[str, Any] = {
    "jsonrpc": "2.0",
    "result": [
        {
            "instrument_name": "ETH-25DEC26-3500-C",
            "strike": 3500.0,
            "option_type": "call",
            "expiration_timestamp": EXPIRY_1_TS,
            "contract_size": 1.0,
            "settlement_currency": "ETH",
            "quote_currency": "ETH",
            "state": "open",
        },
        {
            "instrument_name": "ETH-25DEC26-3500-P",
            "strike": 3500.0,
            "option_type": "put",
            "expiration_timestamp": EXPIRY_1_TS,
            "contract_size": 1.0,
            "settlement_currency": "ETH",
            "quote_currency": "ETH",
            "state": "open",
        },
    ],
}

ETH_BOOK_SUMMARY_PAYLOAD: dict[str, Any] = {
    "jsonrpc": "2.0",
    "result": [
        {
            "instrument_name": "ETH-25DEC26-3500-C",
            "mark_price": 0.052,
            "bid_price": 0.050,
            "ask_price": 0.054,
            "mark_iv": 66.5,
            "open_interest": 1200.0,
            "volume_usd": 120000.0,
        },
        {
            "instrument_name": "ETH-25DEC26-3500-P",
            "mark_price": 0.048,
            "bid_price": 0.046,
            "ask_price": 0.050,
            "mark_iv": 64.2,
            "open_interest": 850.0,
            "volume_usd": 95000.0,
        },
    ],
}


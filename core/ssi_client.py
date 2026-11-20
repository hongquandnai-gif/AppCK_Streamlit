# ========================= core/ssi_client.py =========================
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from typing import Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import websocket

from core.constants import (
    HARDCODED_HOSE_INDUSTRIES_MAPPING,
    INDEX_SYMBOLS,
    is_penny_stock,
)

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def vn_now() -> datetime:
    return datetime.now(VN_TZ)


def vn_today() -> date:
    return vn_now().date()


SSI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://iboard.ssi.com.vn",
    "Referer": "https://iboard.ssi.com.vn/",
}

ALL_INDEX_SYMBOLS = set(INDEX_SYMBOLS) | {
    "VNINDEX", "VN30", "HNX", "UPCOM", "VNMID", "VNSML", "VNSMALL",
    "HNXINDEX", "HNXUPCOMINDEX", "VNMIDCAP", "VNSMALLCAP", "VN100", "VNALL",
}

SSI_INDEX_ALIASES: Dict[str, List[str]] = {
    "VNINDEX": ["VNINDEX"],
    "VN30": ["VN30"],
    "HNX": ["HNXINDEX", "HNXIndex", "HNX"],
    "HNXINDEX": ["HNXINDEX", "HNXIndex", "HNX"],
    "UPCOM": ["HNXUPCOMINDEX", "HNXUpcomIndex", "UPCOM"],
    "HNXUPCOMINDEX": ["HNXUPCOMINDEX", "HNXUpcomIndex", "UPCOM"],
    "VNMID": ["VNMID", "VNMidcap"],
    "VNSMALL": ["VNSML", "VNSmallcap", "VNSMALL"],
    "VNSML": ["VNSML", "VNSmallcap", "VNSMALL"],
}

VNDIRECT_INDEX_MAP: Dict[str, str] = {
    "VNINDEX": "VNINDEX",
    "VN30": "VN30",
    "HNX": "HNX",
    "HNXINDEX": "HNX",
    "UPCOM": "UPCOM",
    "HNXUPCOMINDEX": "UPCOM",
    "VNMID": "VNMID",
    "VNSMALL": "VNSML",
    "VNSML": "VNSML",
}

VNDIRECT_FIRST_INDICES = {"VNMID", "VNSMALL", "VNSML"}

WS_INDEX_CANONICAL_MIRROR: Dict[str, List[str]] = {
    "HNXINDEX": ["HNX", "HNXINDEX"],
    "HNXUPCOMINDEX": ["UPCOM", "HNXUPCOMINDEX"],
    "VNMIDCAP": ["VNMID"],
    "VNMID": ["VNMID"],
    "VNSML": ["VNSMALL", "VNSML"],
    "VNSMALLCAP": ["VNSMALL", "VNSML"],
}

_RESOLVED_SSI_SYMBOL: Dict[str, str] = {}


# ==============================================================================
# 1. LẤY DANH SÁCH MÃ & BẢNG GIÁ NHANH TỪ SSI IBOARD
# ==============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ssi_stock_list(exchange: str = "hose") -> Dict[str, dict]:
    url = f"https://iboard-query.ssi.com.vn/stock/exchange/{exchange.lower()}"
    stock_dict: Dict[str, dict] = {}
    try:
        resp = requests.get(url, headers=SSI_HEADERS, timeout=10)
        if resp.status_code == 200:
            payload = resp.json()
            items = payload.get("data", []) if isinstance(payload, dict) else []
            for item in items:
                sym = str(item.get("stockSymbol") or item.get("code") or "").strip().upper()
                if len(sym) == 3 and sym.isalpha():
                    ind = HARDCODED_HOSE_INDUSTRIES_MAPPING.get(
                        sym,
                        "Penny" if is_penny_stock(sym) else (item.get("industryName") or "Khác")
                    )
                    stock_dict[sym] = {
                        "symbol": sym,
                        "companyName": item.get("companyNameVi") or item.get("companyNameEn") or sym,
                        "industry": ind,
                        "exchange": exchange.upper(),
                        "refPrice": float(item.get("refPrice") or 0) / 1000.0,
                        "ceiling": float(item.get("ceiling") or 0) / 1000.0,
                        "floor": float(item.get("floor") or 0) / 1000.0,
                    }
    except Exception:
        pass

    if not stock_dict:
        for sym, ind in HARDCODED_HOSE_INDUSTRIES_MAPPING.items():
            if ind != "Chỉ số" and len(sym) == 3:
                stock_dict[sym] = {
                    "symbol": sym,
                    "companyName": sym,
                    "industry": ind,
                    "exchange": "HOSE",
                    "refPrice": 0.0,
                    "ceiling": 0.0,
                    "floor": 0.0,
                }
    return stock_dict


def fetch_ssi_realtime_board(exchange: str = "hose") -> Dict[str, dict]:
    """Lấy snapshot toàn bộ bảng giá hiện tại từ SSI iBoard làm nền cho Treemap Realtime."""
    url = f"https://iboard-query.ssi.com.vn/stock/exchange/{exchange.lower()}"
    board: Dict[str, dict] = {}
    try:
        resp = requests.get(url, headers=SSI_HEADERS, timeout=10)
        if resp.status_code == 200:
            items = resp.json().get("data", [])
            for item in items:
                sym = str(item.get("stockSymbol") or item.get("code") or "").strip().upper()
                if len(sym) == 3 and sym.isalpha():
                    ref = float(item.get("refPrice") or 0) / 1000.0
                    last = float(item.get("matchedPrice") or item.get("lastPrice") or ref * 1000.0) / 1000.0
                    vol = float(item.get("nmTotalTradedQty") or item.get("totalVolume") or 0)
                    if last <= 0:
                        last = ref
                    pct = ((last - ref) / ref * 100.0) if ref > 0 else 0.0
                    board[sym] = {
                        "symbol": sym,
                        "last": last,
                        "ref": ref,
                        "delta": last - ref,
                        "pct": pct,
                        "volume": vol,
                        "time": vn_now().strftime("%H:%M:%S"),
                    }
    except Exception:
        pass
    return board


# ==============================================================================
# 2. SSI WEBSOCKET REALTIME STREAM MANAGER (LƯU TICK + CHUỖI NẾN 1 PHÚT LIỀN MẠCH)
# ==============================================================================
class SSIWebSocketManager:
    WS_URL = "wss://iboard-pushstream.ssi.com.vn/realtime"

    def __init__(self):
        self._lock = threading.Lock()
        self._live_ticks: Dict[str, dict] = {}
        self._minute_bars: Dict[str, Dict[datetime, dict]] = {}
        self._bar_date: date = vn_today()
        self._subscribed: set[str] = set()
        self._ws: Optional[websocket.WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._connected = False
        self._last_msg_time: Optional[datetime] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def last_update(self) -> Optional[datetime]:
        return self._last_msg_time

    def start(self, symbols: Optional[List[str]] = None):
        if symbols:
            self._subscribed.update([s.upper().strip() for s in symbols if s])
        if self._running and self._thread and self._thread.is_alive():
            self.subscribe(list(self._subscribed))
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        self._connected = False

    def subscribe(self, symbols: List[str]):
        clean_syms = [s.upper().strip() for s in symbols if s]
        with self._lock:
            new_syms = [s for s in clean_syms if s not in self._subscribed]
            self._subscribed.update(clean_syms)
        if self._ws and self._connected and new_syms:
            self._send_sub_payload(new_syms)

    def _send_sub_payload(self, symbols: List[str]):
        if not self._ws:
            return
        try:
            stock_syms = [s for s in symbols if s not in ALL_INDEX_SYMBOLS]
            idx_syms = [s for s in symbols if s in ALL_INDEX_SYMBOLS]

            for i in range(0, len(stock_syms), 150):
                chunk = stock_syms[i:i + 150]
                msg_stock = {
                    "type": "sub",
                    "topic": "stockRealtimeByListV2",
                    "variables": chunk,
                    "component": "priceTableEquities",
                }
                self._ws.send(json.dumps(msg_stock))

            if idx_syms:
                expanded_idx = []
                for s in idx_syms:
                    expanded_idx.extend(SSI_INDEX_ALIASES.get(s, [s]))
                msg_idx = {
                    "type": "sub",
                    "topic": "indexRealtimeByList",
                    "variables": sorted(list(set(expanded_idx))),
                    "component": "indexBar",
                }
                self._ws.send(json.dumps(msg_idx))
        except Exception:
            pass

    def _on_open(self, ws):
        self._connected = True
        with self._lock:
            syms = list(self._subscribed)
        if syms:
            self._send_sub_payload(syms)

    def _on_message(self, ws, message: str):
        self._last_msg_time = vn_now()
        try:
            if message.startswith("{"):
                data = json.loads(message)
                payload = data.get("data") or data
                if isinstance(payload, dict):
                    self._parse_dict_tick(payload)
                elif isinstance(payload, list):
                    for item in payload:
                        if isinstance(item, dict):
                            self._parse_dict_tick(item)
            elif "|" in message:
                self._parse_pipe_tick(message)
        except Exception:
            pass

    def _store_tick_locked(self, sym: str, tick_obj: dict):
        now_dt = vn_now()
        today_d = now_dt.date()
        if today_d != self._bar_date:
            self._minute_bars.clear()
            self._bar_date = today_d

        minute_ts = now_dt.replace(second=0, microsecond=0, tzinfo=None)
        px = float(tick_obj["last"])
        vol = float(tick_obj.get("volume") or 0.0)

        targets = set([sym] + WS_INDEX_CANONICAL_MIRROR.get(sym, []))
        for t_sym in targets:
            self._live_ticks[t_sym] = dict(tick_obj, symbol=t_sym)

            bars = self._minute_bars.setdefault(t_sym, {})
            if minute_ts in bars:
                b = bars[minute_ts]
                b["High"] = max(b["High"], px)
                b["Low"] = min(b["Low"], px)
                b["Close"] = px
                if vol > 0:
                    b["Volume"] = vol
            else:
                bars[minute_ts] = {
                    "Open": px,
                    "High": px,
                    "Low": px,
                    "Close": px,
                    "Volume": vol,
                }

    def _parse_dict_tick(self, item: dict):
        sym = str(item.get("stockSymbol") or item.get("indexId") or item.get("sym") or "").upper().strip()
        if not sym:
            return

        is_idx = sym in ALL_INDEX_SYMBOLS
        div = 1.0 if is_idx else 1000.0

        raw_last = item.get("matchedPrice") or item.get("indexValue") or item.get("lastPrice") or item.get("c")
        raw_ref = item.get("refPrice") or item.get("prevIndexValue") or item.get("r")
        raw_vol = item.get("nmTotalTradedQty") or item.get("totalVolume") or item.get("v")

        if raw_last is None:
            return

        last_f = float(raw_last)
        last_val = last_f / div if (last_f > 500 and not is_idx) else last_f

        if is_idx and last_val < 50.0:
            return

        ref_val = None
        if raw_ref is not None:
            ref_f = float(raw_ref)
            ref_val = ref_f / div if (ref_f > 500 and not is_idx) else ref_f
            if is_idx and ref_val < 50.0:
                ref_val = None

        with self._lock:
            prev = self._live_ticks.get(sym, {})
            if ref_val is None:
                ref_val = prev.get("ref")
            delta = (last_val - ref_val) if (ref_val and ref_val > 0) else 0.0
            pct = (delta / ref_val * 100.0) if (ref_val and ref_val > 0) else 0.0

            tick_obj = {
                "symbol": sym,
                "last": last_val,
                "ref": ref_val,
                "delta": delta,
                "pct": pct,
                "volume": float(raw_vol) if raw_vol is not None else prev.get("volume", 0.0),
                "time": vn_now().strftime("%H:%M:%S"),
            }
            self._store_tick_locked(sym, tick_obj)

    def _parse_pipe_tick(self, raw: str):
        parts = raw.split("|")
        if len(parts) < 5:
            return
        header = parts[0]
        sym = header.split("#")[-1].strip().upper()
        if not sym:
            return
        is_idx = sym in ALL_INDEX_SYMBOLS
        div = 1.0 if is_idx else 1000.0

        try:
            nums = []
            for p in parts[1:15]:
                try:
                    val = float(p)
                    if val > 0:
                        nums.append(val)
                except ValueError:
                    continue
            if nums:
                last_val = nums[0] / div if (nums[0] > 500 and not is_idx) else nums[0]
                if is_idx and last_val < 50.0:
                    return
                with self._lock:
                    prev = self._live_ticks.get(sym, {})
                    ref_val = prev.get("ref")
                    delta = (last_val - ref_val) if ref_val else 0.0
                    pct = (delta / ref_val * 100.0) if ref_val else 0.0
                    tick_obj = {
                        "symbol": sym,
                        "last": last_val,
                        "ref": ref_val,
                        "delta": delta,
                        "pct": pct,
                        "volume": prev.get("volume", 0.0),
                        "time": vn_now().strftime("%H:%M:%S"),
                    }
                    self._store_tick_locked(sym, tick_obj)
        except Exception:
            pass

    def _on_error(self, ws, error):
        self._connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        self._connected = False

    def _run_loop(self):
        while self._running:
            try:
                self._ws = websocket.WebSocketApp(
                    self.WS_URL,
                    header=[f"{k}: {v}" for k, v in SSI_HEADERS.items()],
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self._ws.run_forever(ping_interval=25, ping_timeout=10)
            except Exception:
                self._connected = False
            if self._running:
                time.sleep(3)

    def get_snapshot(self, symbols: Optional[List[str]] = None) -> Dict[str, dict]:
        with self._lock:
            if not symbols:
                return dict(self._live_ticks)
            return {s: dict(self._live_ticks[s]) for s in symbols if s in self._live_ticks}

    def get_minute_bars_df(self, symbol: str) -> pd.DataFrame:
        sym_u = symbol.upper().strip()
        with self._lock:
            if self._bar_date != vn_today() or sym_u not in self._minute_bars:
                return pd.DataFrame()
            bars = self._minute_bars[sym_u]
            if not bars:
                return pd.DataFrame()
            df = pd.DataFrame.from_dict(bars, orient="index").sort_index()
            df.index.name = "Time"
            return df


@st.cache_resource
def get_ssi_ws_manager() -> SSIWebSocketManager:
    mgr = SSIWebSocketManager()
    hose_syms = [s for s, ind in HARDCODED_HOSE_INDUSTRIES_MAPPING.items() if ind != "Chỉ số"]
    mgr.start(["VNINDEX", "VN30", "HNX", "UPCOM", "VNMID", "VNSMALL"] + hose_syms)
    return mgr


# ==============================================================================
# 3. API LẤY DỮ LIỆU OHLCV LỊCH SỬ & INTRADAY (SSI iBoard + FALLBACK VNDIRECT)
# ==============================================================================
def _parse_tv_payload(data: dict, symbol: str) -> pd.DataFrame:
    if not data or "t" not in data or len(data["t"]) == 0:
        return pd.DataFrame()
    df = pd.DataFrame({
        "Time": pd.to_datetime(data["t"], unit="s", utc=True)
        .tz_convert(VN_TZ)
        .tz_localize(None),
        "Open": pd.to_numeric(data["o"], errors="coerce"),
        "High": pd.to_numeric(data["h"], errors="coerce"),
        "Low": pd.to_numeric(data["l"], errors="coerce"),
        "Close": pd.to_numeric(data["c"], errors="coerce"),
        "Volume": pd.to_numeric(data["v"], errors="coerce"),
    }).dropna(subset=["Close"])

    df = df.set_index("Time").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    if df.empty:
        return df

    sym_u = symbol.upper()
    if sym_u in ALL_INDEX_SYMBOLS:
        if float(df["Close"].median()) < 50.0:
            return pd.DataFrame()
    elif float(df["Close"].median()) > 500.0:
        for col in ["Open", "High", "Low", "Close"]:
            df[col] = df[col] / 1000.0

    return df


def _fetch_vndirect_ohlcv(sym_u: str, resolution: str, t_from: int, t_to: int) -> pd.DataFrame:
    vnd_sym = VNDIRECT_INDEX_MAP.get(sym_u)
    if not vnd_sym:
        return pd.DataFrame()
    vnd_url = (
        f"https://dchart-api.vndirect.com.vn/dchart/history"
        f"?symbol={vnd_sym}&resolution={resolution}&from={t_from}&to={t_to}"
    )
    try:
        resp = requests.get(vnd_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        if resp.status_code == 200:
            return _parse_tv_payload(resp.json(), sym_u)
    except Exception:
        pass
    return pd.DataFrame()


def fetch_ssi_ohlcv(
    symbol: str,
    start_date: date,
    end_date: date,
    resolution: str = "D",
) -> pd.DataFrame:
    sym_u = symbol.upper().strip()
    dt_from = datetime.combine(start_date, datetime.min.time(), tzinfo=VN_TZ)
    dt_to = datetime.combine(end_date, datetime.max.time(), tzinfo=VN_TZ)
    t_from, t_to = int(dt_from.timestamp()), int(dt_to.timestamp())

    if sym_u in VNDIRECT_FIRST_INDICES:
        df_vnd = _fetch_vndirect_ohlcv(sym_u, resolution, t_from, t_to)
        if not df_vnd.empty:
            return df_vnd

    candidates = SSI_INDEX_ALIASES.get(sym_u, [sym_u])
    if sym_u in _RESOLVED_SSI_SYMBOL:
        resolved = _RESOLVED_SSI_SYMBOL[sym_u]
        candidates = [resolved] + [c for c in candidates if c != resolved]

    for cand in candidates:
        url = (
            f"https://iboard-api.ssi.com.vn/statistics/charts/history"
            f"?resolution={resolution}&symbol={cand}&from={t_from}&to={t_to}"
        )
        try:
            resp = requests.get(url, headers=SSI_HEADERS, timeout=12)
            if resp.status_code == 200:
                raw = resp.json()
                data = raw.get("data", raw) if isinstance(raw, dict) else {}
                df = _parse_tv_payload(data, sym_u)
                if not df.empty:
                    _RESOLVED_SSI_SYMBOL[sym_u] = cand
                    return df
        except Exception:
            continue

    if sym_u in VNDIRECT_INDEX_MAP and sym_u not in VNDIRECT_FIRST_INDICES:
        df_vnd = _fetch_vndirect_ohlcv(sym_u, resolution, t_from, t_to)
        if not df_vnd.empty:
            return df_vnd

    return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_ssi_ohlcv_cached(
    symbol: str,
    start_date: date,
    end_date: date,
    resolution: str = "D",
) -> pd.DataFrame:
    return fetch_ssi_ohlcv(symbol, start_date, end_date, resolution)


# ==============================================================================
# 4. TẢI HÀNG LOẠT SONG SONG KÈM CACHE TTL TRONG RAM
# ==============================================================================
_BATCH_CACHE: Dict[tuple, tuple[float, Dict[str, pd.DataFrame]]] = {}
_BATCH_CACHE_LOCK = threading.Lock()
_BATCH_CACHE_TTL = 900
_BATCH_CACHE_MAX_ITEMS = 8


def clear_batch_cache() -> None:
    with _BATCH_CACHE_LOCK:
        _BATCH_CACHE.clear()


def fetch_batch_ohlcv_ssi(
    symbols: List[str],
    start_date: date,
    end_date: date,
    resolution: str = "D",
    max_workers: int = 16,
    _progress_cb: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, pd.DataFrame]:
    unique_syms = sorted(list(set(symbols)))
    total = len(unique_syms)
    if total == 0:
        return {}

    cache_key = (tuple(unique_syms), start_date, end_date, resolution)
    now_ts = time.time()

    with _BATCH_CACHE_LOCK:
        cached = _BATCH_CACHE.get(cache_key)
        if cached and (now_ts - cached[0]) < _BATCH_CACHE_TTL:
            cached_data = {k: v.copy() for k, v in cached[1].items()}
        else:
            cached_data = None

    if cached_data is not None:
        if _progress_cb:
            _progress_cb(total, total)
        return cached_data

    results: Dict[str, pd.DataFrame] = {}
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {
            pool.submit(fetch_ssi_ohlcv, sym, start_date, end_date, resolution): sym
            for sym in unique_syms
        }
        for fut in as_completed(future_map):
            sym = future_map[fut]
            try:
                df = fut.result()
                if df is not None and not df.empty:
                    results[sym] = df
            except Exception:
                pass
            done += 1
            if _progress_cb:
                _progress_cb(done, total)

    with _BATCH_CACHE_LOCK:
        if len(_BATCH_CACHE) >= _BATCH_CACHE_MAX_ITEMS:
            oldest_key = min(_BATCH_CACHE, key=lambda k: _BATCH_CACHE[k][0])
            _BATCH_CACHE.pop(oldest_key, None)
        _BATCH_CACHE[cache_key] = (now_ts, results)

    return {k: v.copy() for k, v in results.items()}

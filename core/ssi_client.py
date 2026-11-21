# ========================= core/ssi_client.py =========================
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple
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


def is_vn_market_hours() -> bool:
    """Kiểm tra đang trong khung giờ giao dịch chứng khoán VN (T2-T6, 08:50 đến 15:10)."""
    now = vn_now()
    if now.weekday() >= 5:
        return False
    hhmm = now.hour * 100 + now.minute
    return 850 <= hhmm <= 1510


SSI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://iboard.ssi.com.vn",
    "Referer": "https://iboard.ssi.com.vn/",
}

MAIN_INDEX_LIST = ["VNINDEX", "VN30", "HNX", "UPCOM", "VNMID", "VNSMALL"]

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
_RESOLVED_SSI_LOCK = threading.Lock()


def _safe_float(val, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    try:
        f = float(val)
        return f if f == f else default
    except (TypeError, ValueError):
        return default


def _first_positive(*vals) -> Optional[float]:
    for v in vals:
        f = _safe_float(v, default=-1.0)
        if f > 0.0:
            return f
    return None


def _first_non_negative(*vals) -> Optional[float]:
    for v in vals:
        if v is None or v == "":
            continue
        f = _safe_float(v, default=-1.0)
        if f >= 0.0:
            return f
    return None


# ==============================================================================
# 1. DANH SÁCH MÃ & BẢNG GIÁ REALTIME TOÀN SÀN TỪ SSI IBOARD
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
                if not isinstance(item, dict):
                    continue
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
                        "refPrice": _to_thousand_vnd(item.get("refPrice")),
                        "ceiling": _to_thousand_vnd(item.get("ceiling")),
                        "floor": _to_thousand_vnd(item.get("floor")),
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


def _to_thousand_vnd(val) -> float:
    v = _safe_float(val, default=0.0)
    return (v / 1000.0) if v >= 500.0 else v


def fetch_ssi_realtime_board(exchange: str = "hose") -> Dict[str, dict]:
    """
    Lấy toàn bộ bảng giá khớp lệnh trực tiếp của ~400 mã sàn HOSE trong 1 request (~0.25s).
    Đọc đầy đủ matchedPrice / expectedMatchedPrice (ATO/ATC) / nmTotalTradedQty.
    """
    url = f"https://iboard-query.ssi.com.vn/stock/exchange/{exchange.lower()}"
    board: Dict[str, dict] = {}
    try:
        resp = requests.get(url, headers=SSI_HEADERS, timeout=10)
        if resp.status_code == 200:
            payload = resp.json()
            items = payload.get("data", []) if isinstance(payload, dict) else []
            ts_str = vn_now().strftime("%H:%M:%S")
            for item in items:
                if not isinstance(item, dict):
                    continue
                sym = str(item.get("stockSymbol") or item.get("code") or "").strip().upper()
                if len(sym) != 3 or not sym.isalpha():
                    continue

                ref_raw = _first_positive(item.get("refPrice"), item.get("priorClosePrice"))
                ref = _to_thousand_vnd(ref_raw) if ref_raw is not None else 0.0
                last_raw = _first_positive(
                    item.get("matchedPrice"),
                    item.get("expectedMatchedPrice"),
                    item.get("lastPrice"),
                    item.get("closePrice"),
                )
                last = _to_thousand_vnd(last_raw) if last_raw is not None else ref

                vol = _first_non_negative(
                    item.get("nmTotalTradedQty"),
                    item.get("totalTradedQty"),
                    item.get("stockVol"),
                    item.get("totalVolume"),
                )
                vol = vol if vol is not None else 0.0
                val_vnd = _safe_float(item.get("nmTotalTradedValue"), default=0.0)
                delta = (last - ref) if (ref > 0 and last > 0) else 0.0
                pct_raw = item.get("priceChangePercent")
                if pct_raw is not None and pct_raw != "" and ref > 0:
                    try:
                        pct = float(pct_raw)
                        if pct != pct:
                            pct = (delta / ref * 100.0)
                    except (TypeError, ValueError):
                        pct = (delta / ref * 100.0)
                else:
                    pct = (delta / ref * 100.0) if ref > 0 else 0.0

                board[sym] = {
                    "symbol": sym,
                    "last": last,
                    "ref": ref,
                    "delta": delta,
                    "pct": pct,
                    "volume": vol,
                    "value_bil": (val_vnd / 1e9) if val_vnd > 1e6 else (last * vol / 1e6),
                    "time": ts_str,
                }
    except Exception:
        pass
    return board


# ==============================================================================
# 2. SSI WEBSOCKET + BACKGROUND SYNC MANAGER (KHÔNG CHẶN UI STREAMLIT)
# ==============================================================================
class SSIWebSocketManager:
    WS_URL = "wss://iboard-pushstream.ssi.com.vn/realtime"

    def __init__(self):
        self._lock = threading.Lock()
        self._live_ticks: Dict[str, dict] = {}
        self._live_board: Dict[str, dict] = {}
        self._board_updated_at: Optional[datetime] = None

        # Cache trong RAM cho 6 chỉ số: {sym: {"df_1m": DataFrame, "df_d": DataFrame, "updated_at": datetime}}
        self._index_cache: Dict[str, dict] = {}
        self._minute_bars: Dict[str, Dict[datetime, dict]] = {}
        self._last_cum_vol: Dict[str, float] = {}
        self._bar_date: date = vn_today()
        self._subscribed: set[str] = set()

        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._running = False
        self._connected = False
        self._last_msg_time: Optional[datetime] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def last_update(self) -> Optional[datetime]:
        return self._board_updated_at or self._last_msg_time

    def start(self, symbols: Optional[List[str]] = None):
        if self._running:
            if symbols:
                self.subscribe(symbols)
            return

        if symbols:
            with self._lock:
                self._subscribed.update([s.upper().strip() for s in symbols if s])

        self._running = True
        self._ws_thread = threading.Thread(target=self._run_ws_loop, daemon=True)
        self._ws_thread.start()

        self._poll_thread = threading.Thread(target=self._run_background_sync_loop, daemon=True)
        self._poll_thread.start()

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

    # ---------------- LUỒNG NỀN ĐỒNG BỘ BẢNG GIÁ & 6 CHỈ SỐ ----------------
    def refresh_board_now(self) -> Dict[str, dict]:
        """Đồng bộ ngay toàn bộ bảng giá HOSE từ SSI vào RAM."""
        board = fetch_ssi_realtime_board("hose")
        if board:
            now_dt = vn_now()
            with self._lock:
                self._live_board = board
                self._board_updated_at = now_dt
                for sym, item in board.items():
                    self._live_ticks[sym] = dict(item)
        return self.get_live_board()

    def refresh_indices_now(self, symbols: Optional[List[str]] = None) -> None:
        """Đồng bộ song song dữ liệu 1m + D của 6 chỉ số vào RAM (không khóa UI)."""
        target_syms = symbols or MAIN_INDEX_LIST
        today_d = vn_today()

        def _load_one(sym: str) -> Tuple[str, pd.DataFrame, pd.DataFrame]:
            df_1m = fetch_ssi_ohlcv(sym, today_d - timedelta(days=6), today_d, "1")
            df_d = fetch_ssi_ohlcv(sym, today_d - timedelta(days=25), today_d, "D")
            return sym, df_1m, df_d

        with ThreadPoolExecutor(max_workers=max(1, min(len(target_syms), 8))) as pool:
            futs = [pool.submit(_load_one, s) for s in target_syms]
            now_dt = vn_now()
            for fut in as_completed(futs):
                try:
                    sym, df_1m, df_d = fut.result()
                    if not df_1m.empty or not df_d.empty:
                        with self._lock:
                            self._index_cache[sym] = {
                                "df_1m": df_1m,
                                "df_d": df_d,
                                "updated_at": now_dt,
                            }
                except Exception:
                    pass

    def _run_background_sync_loop(self):
        """Chạy ngầm liên tục: 5s cập nhật bảng giá HOSE, 15s cập nhật 6 chỉ số."""
        cycle = 0
        while self._running:
            try:
                self.refresh_board_now()
                # Chu kỳ đầu tiên tải ngay 6 chỉ số, sau đó 15s/lần trong giờ giao dịch
                if cycle == 0 or cycle % 3 == 0:
                    self.refresh_indices_now(MAIN_INDEX_LIST)
            except Exception:
                pass

            cycle += 1
            sleep_sec = 5 if is_vn_market_hours() else 30
            for _ in range(sleep_sec):
                if not self._running:
                    break
                time.sleep(1)

    def get_live_board(self) -> Dict[str, dict]:
        with self._lock:
            return {k: dict(v) for k, v in self._live_board.items()}

    def get_index_data(self, symbol: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        sym_u = symbol.upper().strip()
        with self._lock:
            entry = self._index_cache.get(sym_u)
            if not entry:
                return pd.DataFrame(), pd.DataFrame()
            return entry["df_1m"].copy(), entry["df_d"].copy()

    def ensure_indices_loaded(self, symbols: List[str]) -> None:
        with self._lock:
            missing = [s for s in symbols if s not in self._index_cache]
        if missing:
            self.refresh_indices_now(missing)

    # ---------------- LUỒNG WEBSOCKET PUSHSTREAM ----------------
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
        except Exception:
            pass

    def _store_tick_locked(self, sym: str, tick_obj: dict):
        now_dt = vn_now()
        today_d = now_dt.date()
        if today_d != self._bar_date:
            self._minute_bars.clear()
            self._last_cum_vol.clear()
            self._bar_date = today_d

        minute_ts = now_dt.replace(second=0, microsecond=0, tzinfo=None)
        px = float(tick_obj["last"])
        cum_vol = float(tick_obj.get("volume") or 0.0)

        targets = set([sym] + WS_INDEX_CANONICAL_MIRROR.get(sym, []))
        for t_sym in targets:
            self._live_ticks[t_sym] = dict(tick_obj, symbol=t_sym)
            if t_sym in self._live_board:
                old_board = self._live_board[t_sym]
                old_vol = float(old_board.get("volume") or 0.0)
                new_vol = cum_vol if cum_vol > 0 else old_vol
                old_val_bil = float(old_board.get("value_bil") or 0.0)
                if new_vol > old_vol and px > 0:
                    new_val_bil = old_val_bil + ((new_vol - old_vol) * px / 1e6)
                else:
                    new_val_bil = old_val_bil if old_val_bil > 0 else (px * new_vol / 1e6)
                old_board.update({
                    "last": px,
                    "delta": tick_obj["delta"],
                    "pct": tick_obj["pct"],
                    "volume": new_vol,
                    "value_bil": new_val_bil,
                    "time": tick_obj["time"],
                })

            delta_vol = 0.0
            if cum_vol > 0:
                prev_cum = self._last_cum_vol.get(t_sym)
                if prev_cum is not None and cum_vol >= prev_cum:
                    delta_vol = cum_vol - prev_cum
                self._last_cum_vol[t_sym] = cum_vol

            bars = self._minute_bars.setdefault(t_sym, {})
            if minute_ts in bars:
                b = bars[minute_ts]
                b["High"] = max(b["High"], px)
                b["Low"] = min(b["Low"], px)
                b["Close"] = px
                if delta_vol > 0:
                    b["Volume"] += delta_vol
            else:
                bars[minute_ts] = {"Open": px, "High": px, "Low": px, "Close": px, "Volume": delta_vol}

    def _parse_dict_tick(self, item: dict):
        sym = str(
            item.get("stockSymbol")
            or item.get("indexId")
            or item.get("indexCode")
            or item.get("sym")
            or item.get("code")
            or ""
        ).upper().strip()
        if not sym:
            return

        is_idx = sym in ALL_INDEX_SYMBOLS
        div = 1.0 if is_idx else 1000.0

        last_f = _first_positive(
            item.get("matchedPrice"),
            item.get("expectedMatchedPrice"),
            item.get("indexValue"),
            item.get("lastPrice"),
            item.get("c"),
        )
        if last_f is None:
            return

        last_val = last_f / div if (last_f >= 500.0 and not is_idx) else last_f
        if last_val <= 0.0 or (is_idx and last_val < 50.0):
            return

        ref_f = _first_positive(
            item.get("refPrice"),
            item.get("priorClosePrice"),
            item.get("prevIndexValue"),
            item.get("r"),
        )
        ref_val = None
        if ref_f is not None:
            ref_val = ref_f / div if (ref_f >= 500.0 and not is_idx) else ref_f
            if is_idx and ref_val < 50.0:
                ref_val = None

        raw_vol = _first_non_negative(
            item.get("nmTotalTradedQty"),
            item.get("totalTradedQty"),
            item.get("totalVolume"),
            item.get("v"),
        )

        with self._lock:
            prev = self._live_ticks.get(sym, {})
            if ref_val is None:
                ref_val = prev.get("ref") or self._live_board.get(sym, {}).get("ref")
            if ref_val is not None and float(ref_val) <= 0:
                ref_val = None
            delta = (last_val - ref_val) if ref_val else 0.0
            pct = (delta / ref_val * 100.0) if ref_val else 0.0

            tick_obj = {
                "symbol": sym,
                "last": last_val,
                "ref": ref_val,
                "delta": delta,
                "pct": pct,
                "volume": raw_vol if raw_vol is not None else prev.get("volume", 0.0),
                "time": vn_now().strftime("%H:%M:%S"),
            }
            self._store_tick_locked(sym, tick_obj)

    def _on_error(self, ws, error):
        self._connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        self._connected = False

    def _run_ws_loop(self):
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
    mgr.start(MAIN_INDEX_LIST + hose_syms)
    return mgr


# ==============================================================================
# 3. API LẤY DỮ LIỆU OHLCV LỊCH SỬ & INTRADAY (SSI iBoard + FALLBACK VNDIRECT)
# ==============================================================================
def _parse_tv_payload(data: dict, symbol: str, resolution: str = "D") -> pd.DataFrame:
    if not isinstance(data, dict) or not data.get("t"):
        return pd.DataFrame()
    t_arr = data.get("t")
    if not isinstance(t_arr, list) or len(t_arr) == 0:
        return pd.DataFrame()

    n = len(t_arr)
    for k in ("o", "h", "l", "c"):
        arr = data.get(k)
        if not isinstance(arr, list) or len(arr) != n:
            return pd.DataFrame()

    v_arr = data.get("v")
    if not isinstance(v_arr, list) or len(v_arr) != n:
        v_arr = [0.0] * n

    df = pd.DataFrame({
        "Time": pd.to_datetime(t_arr, unit="s", utc=True)
        .tz_convert(VN_TZ)
        .tz_localize(None),
        "Open": pd.to_numeric(data["o"], errors="coerce"),
        "High": pd.to_numeric(data["h"], errors="coerce"),
        "Low": pd.to_numeric(data["l"], errors="coerce"),
        "Close": pd.to_numeric(data["c"], errors="coerce"),
        "Volume": pd.to_numeric(v_arr, errors="coerce"),
    }).dropna(subset=["Time", "Close"])

    if df.empty:
        return df

    df["Open"] = df["Open"].fillna(df["Close"])
    df["High"] = df["High"].fillna(df["Close"])
    df["Low"] = df["Low"].fillna(df["Close"])
    df["Volume"] = df["Volume"].fillna(0.0)

    df = df.set_index("Time").sort_index()
    if str(resolution).upper() in ("D", "1D", "W", "1W", "M", "1M"):
        df.index = df.index.normalize()
    df = df[~df.index.duplicated(keep="last")]
    if df.empty:
        return df

    sym_u = symbol.upper()
    if sym_u in ALL_INDEX_SYMBOLS:
        if float(df["Close"].median()) < 50.0:
            return pd.DataFrame()
    elif float(df["Close"].median()) >= 500.0:
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
            return _parse_tv_payload(resp.json(), sym_u, resolution=resolution)
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
    if not sym_u or start_date > end_date:
        return pd.DataFrame()

    dt_from = datetime.combine(start_date, datetime.min.time(), tzinfo=VN_TZ)
    dt_to = datetime.combine(end_date, datetime.max.time(), tzinfo=VN_TZ)
    t_from, t_to = int(dt_from.timestamp()), int(dt_to.timestamp())

    if sym_u in VNDIRECT_FIRST_INDICES:
        df_vnd = _fetch_vndirect_ohlcv(sym_u, resolution, t_from, t_to)
        if not df_vnd.empty:
            return df_vnd

    candidates = list(SSI_INDEX_ALIASES.get(sym_u, [sym_u]))
    with _RESOLVED_SSI_LOCK:
        resolved = _RESOLVED_SSI_SYMBOL.get(sym_u)
    if resolved:
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
                df = _parse_tv_payload(data, sym_u, resolution=resolution)
                if not df.empty:
                    with _RESOLVED_SSI_LOCK:
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
    unique_syms = sorted(list(set(str(s).strip().upper() for s in symbols if s)))
    total = len(unique_syms)
    if total == 0 or start_date > end_date:
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
    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
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

    if results:
        with _BATCH_CACHE_LOCK:
            if len(_BATCH_CACHE) >= _BATCH_CACHE_MAX_ITEMS:
                oldest_key = min(_BATCH_CACHE, key=lambda k: _BATCH_CACHE[k][0])
                _BATCH_CACHE.pop(oldest_key, None)
            _BATCH_CACHE[cache_key] = (time.time(), results)

    return {k: v.copy() for k, v in results.items()}

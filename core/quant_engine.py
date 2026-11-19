# ========================= core/quant_engine.py =========================
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.constants import HARDCODED_HOSE_INDUSTRIES_MAPPING, is_penny_stock


# ==============================================================================
# 1. PHÁT HIỆN MÔ HÌNH VCP & ĐÁNH GIÁ CHU KỲ MINERVINI
# ==============================================================================
def detect_vcp_pattern(data: pd.DataFrame, current_date: date, lookback_days: int = 150) -> Optional[dict]:
    sub = data[
        (data.index.date <= current_date)
        & (data.index.date >= (current_date - timedelta(days=lookback_days)))
    ].copy()
    if len(sub) < 35:
        return None

    closes = sub["Close"].values
    dates = sub.index.values
    highs = sub["High"].values if "High" in sub.columns else closes
    lows = sub["Low"].values if "Low" in sub.columns else closes

    reversal_pct = 0.03
    swings = []
    current_mode = "peak"
    extreme_val = highs[0]
    extreme_date = dates[0]

    for i in range(1, len(closes)):
        if current_mode == "peak":
            if highs[i] >= extreme_val:
                extreme_val = highs[i]
                extreme_date = dates[i]
            elif extreme_val > 0 and (extreme_val - lows[i]) / extreme_val >= reversal_pct:
                swings.append(("peak", extreme_date, extreme_val))
                current_mode = "valley"
                extreme_val = lows[i]
                extreme_date = dates[i]
        else:
            if lows[i] <= extreme_val:
                extreme_val = lows[i]
                extreme_date = dates[i]
            elif extreme_val > 0 and (highs[i] - extreme_val) / extreme_val >= reversal_pct:
                swings.append(("valley", extreme_date, extreme_val))
                current_mode = "peak"
                extreme_val = highs[i]
                extreme_date = dates[i]

    swings.append((current_mode, extreme_date, extreme_val))

    clean_swings = []
    for s in swings:
        if not clean_swings:
            clean_swings.append(s)
        elif clean_swings[-1][0] == s[0]:
            if s[0] == "peak" and s[2] > clean_swings[-1][2]:
                clean_swings[-1] = s
            elif s[0] == "valley" and s[2] < clean_swings[-1][2]:
                clean_swings[-1] = s
        else:
            clean_swings.append(s)

    contractions = []
    for i in range(len(clean_swings) - 1):
        if clean_swings[i][0] == "peak" and clean_swings[i + 1][0] == "valley":
            p_val = clean_swings[i][2]
            v_val = clean_swings[i + 1][2]
            if p_val > 0:
                depth = ((p_val - v_val) / p_val) * 100.0
                contractions.append({"peak_val": p_val, "valley_val": v_val, "depth": depth})

    if len(contractions) < 2:
        return None

    for num_c in [4, 3, 2]:
        if len(contractions) >= num_c:
            cand = contractions[-num_c:]
            depths = [c["depth"] for c in cand]
            valleys = [c["valley_val"] for c in cand]

            is_contracting = all(depths[i] > depths[i + 1] for i in range(len(depths) - 1))
            higher_lows = all(valleys[i] <= valleys[i + 1] * 1.015 for i in range(len(valleys) - 1))
            tight_finish = depths[-1] <= 8.5

            if is_contracting and higher_lows and tight_finish:
                pivot = cand[-1]["peak_val"]
                curr_price = closes[-1]
                pct_from_pivot = ((curr_price - pivot) / pivot) * 100.0 if pivot > 0 else 0.0

                if 0 <= pct_from_pivot <= 5.0:
                    status = "🟢 Điểm Mua Chuẩn (<= 5%)"
                elif pct_from_pivot > 5.0:
                    status = f"⚠️ Quá Điểm Mua (+{pct_from_pivot:.1f}%)"
                else:
                    status = f"⏳ Chờ Pivot ({pct_from_pivot:.1f}%)"

                return {
                    "is_vcp": True,
                    "buy_point": float(pivot),
                    "ranges": [round(float(d), 1) for d in depths],
                    "pct_from_pivot": float(pct_from_pivot),
                    "status": status,
                    "num_contractions": num_c,
                }
    return None


def evaluate_stock_phase(tk: dict) -> Tuple[str, str, str]:
    close = tk.get("Close", 0.0)
    ma50 = tk.get("MA50", np.nan)
    ma200 = tk.get("MA200", np.nan)
    ma200_20d = tk.get("MA200_20D_ago", np.nan)
    ma200_slope = ((ma200 - ma200_20d) / ma200_20d * 100.0) if (pd.notna(ma200) and pd.notna(ma200_20d) and ma200_20d > 0) else 0.0
    pct_from_peak = tk.get("Pct_From_Peak", -100.0)
    pct_from_bottom = tk.get("Pct_From_Bottom", 0.0)

    if pd.isna(ma50) or pd.isna(ma200):
        return "CHƯA ĐỦ DỮ LIỆU MA200", "#64748b", "Cổ phiếu chưa có đủ lịch sử 200 phiên để phân loại chu kỳ."

    if close > ma50 and ma50 > ma200 and close > ma200 and ma200_slope >= 0:
        if pct_from_bottom >= 25 and pct_from_peak >= -25:
            return (
                "GIAI ĐOẠN 2 (TĂNG TỐC - UPTREND MẠNH)",
                "#059669",
                "Đạt chuẩn Stage 2 Minervini: Cấu trúc xu hướng hoàn hảo, MA dốc lên, sát đỉnh 52 tuần. Ưu tiên MUA.",
            )
        return (
            "GIAI ĐOẠN 2 (ĐANG TRONG XU HƯỚNG TĂNG)",
            "#10b981",
            "Nằm trên MA50 & MA200 dốc lên. Cổ phiếu đang trong chu kỳ tăng giá.",
        )

    if close < ma200 and ma50 < ma200:
        return (
            "GIAI ĐOẠN 4 (SUY THOÁI - DOWNTREND)",
            "#dc2626",
            "Xu hướng giảm dài hạn (Stage 4). TUYỆT ĐỐI KHÔNG BẮT ĐÁY!",
        )

    if close < ma200 and close < ma50:
        return (
            "CHUYỂN GIAO SANG GIAI ĐOẠN 4",
            "#ea580c",
            "Giá xuyên thủng MA200 và MA50, cảnh báo rủi ro cao rơi vào chu kỳ giảm.",
        )

    if pct_from_peak >= -25 and (close < ma50 or abs(ma200_slope) < 0.5):
        return (
            "GIAI ĐOẠN 3 (PHÂN PHỐI - TẠO ĐỈNH)",
            "#d97706",
            "Biến động lỏng lẻo gần đỉnh, mất mốc MA50, MA200 phẳng ra. Ưu tiên chốt lời.",
        )

    if abs(ma200_slope) <= 1.0 and abs(close - ma200) / (ma200 if ma200 > 0 else 1) <= 0.15:
        return (
            "GIAI ĐOẠN 1 (TÍCH LŨY - TẠO ĐÁY)",
            "#2563eb",
            "Giá dao động biên hẹp quanh MA200 đang phẳng. Đưa vào danh sách theo dõi.",
        )

    if close > ma200:
        return (
            "CHUYỂN GIAO (GIAI ĐOẠN 1 SANG 2)",
            "#7c3aed",
            "Giá bứt lên trên MA200, các đường trung bình ngắn hạn đang chuẩn bị Golden Cross.",
        )
    return "GIAI ĐOẠN 4 (SUY THOÁI)", "#dc2626", "Xu hướng giảm chi phối, giá nằm dưới MA200."


# ==============================================================================
# 2. ĐẾM NGÀY PHÂN PHỐI (DD / STALL / CHURN) & STATE MACHINE FTD
# ==============================================================================
def compute_distribution_days_core(
    df: pd.DataFrame,
    window: int = 25,
    cancel_rebound_pct: float = 5.0,
    near_high_lookback: int = 25,
    w_dd: float = 1.0,
    w_stall: float = 0.7,
    w_churn: float = 0.5,
    include_churn: bool = True,
    return_details: bool = False,
):
    if df is None or df.empty or len(df) < 2:
        if return_details:
            return 0, 0, 0, 0.0, pd.DataFrame(columns=["type"])
        return 0, 0, 0, 0.0

    work = df.copy()
    if "Pct" not in work.columns:
        work["Pct"] = work["Close"].pct_change() * 100.0
    elif work["Pct"].abs().max() < 1.5:
        work["Pct"] = work["Pct"] * 100.0

    work["vol_up"] = work["Volume"] > work["Volume"].shift(1)
    rng = (work["High"] - work["Low"]).replace(0, np.nan)
    work["close_pos"] = (work["Close"] - work["Low"]) / rng
    lookback = max(int(window), int(near_high_lookback))
    roll_max = work["Close"].rolling(lookback, min_periods=1).max()
    work["pct_below_high"] = (roll_max - work["Close"]) / roll_max.replace(0, np.nan) * 100.0
    work["vol_surge"] = work["Volume"] >= (work["Volume"].rolling(10, min_periods=2).mean() * 1.3)

    tail = work.iloc[-window:].copy()
    main_mask = (tail["Pct"] <= -0.2) & tail["vol_up"].fillna(False)
    stall_mask = (
        (tail["Pct"] >= 0.0) & (tail["Pct"] <= 0.4)
        & tail["vol_up"].fillna(False)
        & (tail["close_pos"] <= 0.5)
    )
    churn_mask = (
        (tail["Pct"] >= -0.1) & (tail["Pct"] <= 0.5)
        & tail["vol_up"].fillna(False)
        & tail["vol_surge"].fillna(False)
        & (tail["pct_below_high"] <= 2.0)
    )

    final_labels = {}
    closes = tail["Close"].values
    dates = tail.index
    n = len(tail)
    is_m, is_s, is_c = main_mask.values, stall_mask.values, churn_mask.values
    rebound_pct = cancel_rebound_pct * 100.0 if 0 < cancel_rebound_pct < 1.0 else float(cancel_rebound_pct)

    for i in range(n):
        if not (is_m[i] or is_s[i] or (include_churn and is_c[i])):
            continue
        base = closes[i]
        fut_max = np.max(closes[i + 1:]) if i + 1 < n else base
        if fut_max >= base * (1.0 + rebound_pct / 100.0):
            continue

        d = dates[i]
        if is_m[i]:
            final_labels[d] = "DD"
        elif is_s[i]:
            final_labels[d] = "STALL"
        elif include_churn and is_c[i]:
            final_labels[d] = "CHURN"

    cnt_dd = sum(1 for v in final_labels.values() if v == "DD")
    cnt_stall = sum(1 for v in final_labels.values() if v == "STALL")
    cnt_churn = sum(1 for v in final_labels.values() if v == "CHURN")
    risk_score = (cnt_dd * w_dd) + (cnt_stall * w_stall) + ((cnt_churn * w_churn) if include_churn else 0.0)

    if return_details:
        dt = (
            pd.DataFrame([{"Date": k, "type": v} for k, v in final_labels.items()])
            .set_index("Date")
            .sort_index()
            if final_labels else pd.DataFrame(columns=["type"])
        )
        return cnt_dd, cnt_stall, cnt_churn, risk_score, dt

    return cnt_dd, cnt_stall, cnt_churn, risk_score


def get_target_exposure_from_risk(
    risk_score: float, t_low: float = 3.0, t_med: float = 5.0, t_high: float = 7.0, t_crit: float = 9.0
) -> float:
    if risk_score < t_low:
        return 1.0
    if risk_score < t_med:
        return 0.7
    if risk_score < t_high:
        return 0.5
    if risk_score < t_crit:
        return 0.3
    return 0.0


def evaluate_market_ftd_step(
    state: dict, close_idx: float, low_idx: float, vol_idx: float,
    prev_close: float, prev_vol: float, vol_ma20: float,
    use_ftd: bool = True, ftd_mode: int = 0
) -> dict:
    hist_peak = state.get("historical_peak", 0.0)
    ref_peak = state.get("reference_peak", 0.0)
    is_confirmed_uptrend = state.get("is_confirmed_uptrend", True)
    rally_attempt_count = state.get("rally_attempt_count", 0)
    rally_low = state.get("rally_low", float("inf"))
    market_phase = state.get("market_phase", "Uptrend")

    pct_change = (close_idx - prev_close) / prev_close if prev_close > 0 else 0.0

    if close_idx > hist_peak:
        hist_peak = close_idx
    if close_idx > ref_peak:
        ref_peak = close_idx
        is_confirmed_uptrend = True
        rally_attempt_count = 0

    actual_drawdown = (close_idx - hist_peak) / hist_peak if hist_peak > 0 else 0.0
    ref_drawdown = (close_idx - ref_peak) / ref_peak if ref_peak > 0 else 0.0

    if is_confirmed_uptrend:
        if (rally_low < float("inf") and close_idx < rally_low) or ref_drawdown <= -0.08:
            is_confirmed_uptrend = False
            market_phase = "Correction" if actual_drawdown > -0.15 else "Bear Market"
            rally_attempt_count = 0
            rally_low = low_idx
        elif ref_drawdown > -0.05:
            if market_phase != "Confirmed Uptrend (FTD)" or actual_drawdown >= -0.02:
                market_phase = "Uptrend"
        else:
            market_phase = "Pullback"
    else:
        market_phase = "Correction" if actual_drawdown > -0.15 else "Bear Market"
        if low_idx < rally_low:
            rally_low = low_idx
            rally_attempt_count = 0

        if rally_attempt_count == 0:
            if close_idx > prev_close:
                rally_attempt_count = 1
        else:
            rally_attempt_count += 1
            if use_ftd and rally_attempt_count >= 4 and pct_change >= 0.012:
                is_advanced = (ftd_mode == 0)
                vol_ok = (vol_idx > prev_vol and vol_idx > vol_ma20) if is_advanced else (vol_idx > prev_vol)
                if vol_ok:
                    is_confirmed_uptrend = True
                    market_phase = "Confirmed Uptrend (FTD)"
                    ref_peak = close_idx

    state.update({
        "historical_peak": hist_peak,
        "reference_peak": ref_peak,
        "is_confirmed_uptrend": is_confirmed_uptrend,
        "rally_attempt_count": rally_attempt_count,
        "rally_low": rally_low,
        "market_phase": market_phase,
        "actual_drawdown": actual_drawdown,
    })
    return state


# ==============================================================================
# 3. CHẠY QUÉT MINERVINI & RS RATING TOÀN SÀN
# ==============================================================================
def run_minervini_screener(
    raw_map: Dict[str, pd.DataFrame], start_date: date, end_date: date, min_rs: int = 70
) -> Tuple[Dict[str, pd.DataFrame], List[dict], pd.DataFrame, dict]:
    proc_map: Dict[str, pd.DataFrame] = {}
    latest_rows = []

    for sym, df in raw_map.items():
        if sym == "VNINDEX" or len(df) < 60:
            continue
        df = df.sort_index().copy()
        df["MA50"] = df["Close"].rolling(50, min_periods=30).mean()
        df["MA150"] = df["Close"].rolling(150, min_periods=80).mean()
        df["MA200"] = df["Close"].rolling(200, min_periods=100).mean()
        df["MA200_20D_ago"] = df["MA200"].shift(20)
        df["Peak_52W"] = df["Close"].rolling(252, min_periods=80).max()
        df["Bottom_52W"] = df["Close"].rolling(252, min_periods=80).min()
        df["Pct_From_Peak"] = ((df["Close"] - df["Peak_52W"]) / df["Peak_52W"].replace(0, np.nan)) * 100.0
        df["Pct_From_Bottom"] = ((df["Close"] - df["Bottom_52W"]) / df["Bottom_52W"].replace(0, np.nan)) * 100.0
        df["Is_Bottoming"] = (df["Pct_From_Bottom"] <= 10).astype(int)

        c = df["Close"]
        df["Momentum"] = (
            (c / c.shift(63) - 1).fillna(0) * 0.4
            + (c / c.shift(126) - 1).fillna(0) * 0.3
            + (c / c.shift(252) - 1).fillna(0) * 0.3
        ) * 100.0
        proc_map[sym] = df

        sub = df[df.index.date <= end_date]
        if not sub.empty:
            row = sub.iloc[-1].to_dict()
            row["Symbol"] = sym
            latest_rows.append(row)

    if not latest_rows:
        return proc_map, [], pd.DataFrame(), {"peak_price": 0.0, "peak_date": None, "pct_drop": 0.0}

    df_latest = pd.DataFrame(latest_rows)
    df_latest["RS_Rating"] = (df_latest["Momentum"].rank(pct=True, na_option="bottom") * 99).fillna(0).astype(int) + 1
    rs_map = dict(zip(df_latest["Symbol"], df_latest["RS_Rating"]))
    for sym, rs in rs_map.items():
        proc_map[sym]["RS_Rating"] = rs

    screened = []
    for _, r in df_latest.iterrows():
        sym = r["Symbol"]
        c, ma50, ma150, ma200, ma200_20 = r["Close"], r["MA50"], r["MA150"], r["MA200"], r["MA200_20D_ago"]
        rs, pct_peak, pct_bot = r["RS_Rating"], r["Pct_From_Peak"], r["Pct_From_Bottom"]

        if (
            pd.notna(ma50) and pd.notna(ma150) and pd.notna(ma200) and pd.notna(ma200_20)
            and (c > ma50 > ma150 > ma200 and ma200 > ma200_20)
            and (pct_bot >= 25 and pct_peak >= -25 and rs >= min_rs)
        ):
            vcp_res = detect_vcp_pattern(proc_map[sym], end_date, lookback_days=150)
            phase_title, _, _ = evaluate_stock_phase(r)
            screened.append({
                "Mã CP": sym,
                "Ngành": HARDCODED_HOSE_INDUSTRIES_MAPPING.get(sym, "Khác"),
                "Giá": round(float(c), 2),
                "RS Rating": int(rs),
                "Chu Kỳ": phase_title.split("(")[0].strip(),
                "% Đỉnh 52T": round(float(pct_peak), 1),
                "Mô Hình VCP": f"{vcp_res['num_contractions']}T ({' -> '.join([str(x)+'%' for x in vcp_res['ranges']])})" if vcp_res else "—",
                "Pivot": round(float(vcp_res["buy_point"]), 2) if vcp_res else np.nan,
                "Trạng Thái Pivot": vcp_res["status"] if vcp_res else "Chưa hình thành",
            })

    screened.sort(key=lambda x: x["RS Rating"], reverse=True)

    common_dates = sorted(list(set().union(*[df.index for df in proc_map.values()])))
    common_dates = [d for d in common_dates if start_date <= d.date() <= end_date]
    breadth_records = []
    for d in common_dates:
        n_tot = n_above200 = n_bot = 0
        prices = []
        for df in proc_map.values():
            if d in df.index:
                row_d = df.loc[d]
                n_tot += 1
                prices.append(row_d["Close"])
                if pd.notna(row_d["MA200"]) and row_d["Close"] > row_d["MA200"]:
                    n_above200 += 1
                if row_d.get("Is_Bottoming", 0) == 1:
                    n_bot += 1
        if n_tot > 0:
            breadth_records.append({
                "Date": d,
                "Avg_Price": float(np.mean(prices)),
                "Pct_Above_MA200": (n_above200 / n_tot) * 100.0,
                "Pct_Bottoming": (n_bot / n_tot) * 100.0,
            })

    df_breadth = pd.DataFrame(breadth_records).set_index("Date") if breadth_records else pd.DataFrame()
    stats_summary = {"peak_price": 0.0, "peak_date": None, "pct_drop": 0.0}
    if not df_breadth.empty:
        peak_idx = df_breadth["Avg_Price"].idxmax()
        peak_val = float(df_breadth.loc[peak_idx, "Avg_Price"])
        last_val = float(df_breadth["Avg_Price"].iloc[-1])
        pct_drop = ((peak_val - last_val) / peak_val) * 100.0 if peak_val > 0 else 0.0
        stats_summary = {"peak_price": peak_val, "peak_date": peak_idx, "pct_drop": pct_drop}

    return proc_map, screened, df_breadth, stats_summary


# ==============================================================================
# 4. ENGINE BACKTEST HYBRID (ĐẦY ĐỦ TOP SECTOR + TAKE PROFIT + SNAPSHOTS)
# ==============================================================================
def _precalc_sector_ranks(data_map: Dict[str, pd.DataFrame], common_dates: list, top_n: int) -> dict:
    sec_to_syms: dict = {}
    for sym, sec in HARDCODED_HOSE_INDUSTRIES_MAPPING.items():
        if sec not in ["Chỉ số", "Penny", "Khác"] and not is_penny_stock(sym):
            sec_to_syms.setdefault(sec, []).append(sym)

    strength_status = {}
    for sym, df in data_map.items():
        if sym == "VNINDEX" or "MA50" not in df.columns:
            continue
        cond = (df["Close"] > df["MA20"]) & (df["Close"] > df["MA50"])
        strength_status[sym] = cond.reindex(common_dates, fill_value=False)

    daily_top = {}
    for d in common_dates:
        sec_scores = []
        for sec, syms in sec_to_syms.items():
            valid_syms = [s for s in syms if s in strength_status]
            if not valid_syms:
                continue
            ratio = sum(1 for s in valid_syms if strength_status[s].loc[d]) / len(valid_syms)
            sec_scores.append((sec, ratio))
        sec_scores.sort(key=lambda x: x[1], reverse=True)
        daily_top[d] = set([x[0] for x in sec_scores[:top_n]])
    return daily_top


def run_hybrid_backtest(raw_map: Dict[str, pd.DataFrame], p: dict) -> dict:
    data_map = {}
    momentum_dict = {}
    above_ma200_dict = {}
    bottoming_dict = {}
    ma_exit = p["ma_exit"]

    for sym, df in raw_map.items():
        if len(df) < 60:
            continue
        df = df.sort_index().copy()
        c = df["Close"]
        df["Pct"] = c.pct_change() * 100.0
        df["MA10"] = c.rolling(10, min_periods=5).mean()
        df["MA_Exit"] = c.rolling(ma_exit, min_periods=10).mean()
        df["MA20"] = c.rolling(20, min_periods=15).mean()
        df["MA50"] = c.rolling(50, min_periods=30).mean()
        df["MA150"] = c.rolling(150, min_periods=80).mean()
        df["MA200"] = c.rolling(200, min_periods=100).mean()
        df["MA200_20D_ago"] = df["MA200"].shift(20)
        df["VolMA10"] = df["Volume"].rolling(10, min_periods=5).mean()
        df["VolMA20"] = df["Volume"].rolling(20, min_periods=10).mean()

        if sym == "VNINDEX":
            data_map[sym] = df
            continue

        hl_range = (df["High"] - df["Low"]).replace(0, np.nan)
        df["Close_Pos"] = ((c - df["Low"]) / hl_range).fillna(0.5)
        df["Peak_52W"] = c.rolling(252, min_periods=80).max()
        df["Bottom_52W"] = c.rolling(252, min_periods=80).min()
        df["Pct_From_Peak"] = ((c - df["Peak_52W"]) / df["Peak_52W"].replace(0, np.nan)) * 100.0
        df["Pct_From_Bottom"] = ((c - df["Bottom_52W"]) / df["Bottom_52W"].replace(0, np.nan)) * 100.0
        df["Is_Bottoming"] = (df["Pct_From_Bottom"] <= 12.0).astype(float)
        df["Momentum"] = (
            (c / c.shift(63) - 1.0).fillna(0.0) * 0.4
            + (c / c.shift(126) - 1.0).fillna(0.0) * 0.3
            + (c / c.shift(252) - 1.0).fillna(0.0) * 0.3
        ) * 100.0

        momentum_dict[sym] = df["Momentum"]
        above_ma200_dict[sym] = (c > df["MA200"]).astype(float).where(df["MA200"].notna(), np.nan)
        bottoming_dict[sym] = df["Is_Bottoming"]
        data_map[sym] = df

    if momentum_dict:
        mom_df = pd.DataFrame(momentum_dict)
        rs_df = (mom_df.rank(axis=1, pct=True, na_option="bottom") * 99.0).fillna(0.0).astype(int) + 1
        for sym in momentum_dict:
            data_map[sym]["RS_Rating"] = rs_df[sym]

    breadth_df = pd.DataFrame()
    if above_ma200_dict:
        breadth_df["Pct_Above_MA200"] = pd.DataFrame(above_ma200_dict).mean(axis=1, skipna=True) * 100.0
        breadth_df["Pct_Bottoming"] = pd.DataFrame(bottoming_dict).mean(axis=1, skipna=True) * 100.0
        breadth_df["Breadth_Peak10"] = breadth_df["Pct_Above_MA200"].rolling(10, min_periods=2).max()

    cash = float(p["initial_capital"])
    initial_capital = cash
    max_pos = p["max_positions"]
    max_per_sector = p["max_per_sector"]
    fee = p["fee_rate"]
    stop_loss = p["stop_loss"]
    take_profit = p["take_profit"]
    use_take_profit = p["use_take_profit"]
    min_vol = p["min_vol"]
    t_plus = int(np.ceil(p["t_plus"]))
    min_rs = p["min_rs"]
    entry_mode = p["entry_mode"]
    max_pivot_pct = p["max_pivot_pct"]
    vol_mult = p["vol_mult"]
    use_power_play = p["use_power_play"]
    filter_top_sectors = p.get("filter_top_sectors", False)
    top_sectors_n = p.get("top_sectors", 5)

    use_dd_shield = p["use_dd_shield"]
    use_top_climax = p["use_top_climax"]
    climax_breadth_thresh = p["climax_breadth_thresh"]
    use_bottom_fishing = p["use_bottom_fishing"]
    panic_ma200_thresh = p["panic_ma200_thresh"]
    panic_bot52_thresh = p["panic_bot52_thresh"]

    vnindex_df = data_map.get("VNINDEX")
    tradable_symbols = [s for s in p["symbols"] if s != "VNINDEX" and s in data_map]
    all_dates = sorted(list(set().union(*[df.index for df in data_map.values()])))
    all_dates = [d for d in all_dates if p["start_date"] <= d.date() <= p["end_date"]]

    if not all_dates:
        return {}

    daily_top_sectors_map = _precalc_sector_ranks(data_map, all_dates, top_sectors_n) if filter_top_sectors else {}

    holdings, pending_stocks, pending_cash = {}, [], []
    trades_history, closed_trades, equity_history, daily_snapshots = [], [], [], []
    total_days = len(all_dates)
    was_in_panic_zone = False
    panic_cooldown_days = 0

    for day_idx, current_date in enumerate(all_dates):
        rem_cash = []
        for item in pending_cash:
            if day_idx >= item[0]:
                cash += item[1]
            else:
                rem_cash.append(item)
        pending_cash = rem_cash

        rem_stocks = []
        for item in pending_stocks:
            arrival_idx, sym, qty, price, buy_date, sec, trade_tag, is_bottom_bet = item
            if day_idx >= arrival_idx:
                if sym in holdings:
                    old = holdings[sym]
                    new_qty = old["qty"] + qty
                    new_price = ((old["qty"] * old["price"]) + (qty * price)) / new_qty
                    holdings[sym].update({"qty": new_qty, "price": new_price, "last_price": price})
                else:
                    holdings[sym] = {
                        "qty": qty, "price": price, "last_price": price,
                        "date": buy_date, "is_power_play": False,
                        "vcp_tag": trade_tag, "is_bottom_bet": is_bottom_bet,
                    }
            else:
                rem_stocks.append(item)
        pending_stocks = rem_stocks

        cnt_dd, risk_score = 0, 0.0
        if vnindex_df is not None and not vnindex_df.empty:
            idx_pos = int(vnindex_df.index.get_indexer([current_date], method="pad")[0])
            if idx_pos >= 25:
                cnt_dd, _, _, risk_score = compute_distribution_days_core(
                    vnindex_df.iloc[:idx_pos + 1], window=25,
                    cancel_rebound_pct=p["dd_cancel_pct"],
                    w_dd=p["w_dd"], w_stall=p["w_stall"], include_churn=True,
                )

        pct_above_200 = prev_pct_above_200 = breadth_peak10 = 50.0
        pct_bottoming = 0.0
        if not breadth_df.empty and current_date in breadth_df.index:
            b_row = breadth_df.loc[current_date]
            pct_above_200 = float(b_row.get("Pct_Above_MA200", 50.0))
            pct_bottoming = float(b_row.get("Pct_Bottoming", 0.0))
            breadth_peak10 = float(b_row.get("Breadth_Peak10", pct_above_200))
            loc_b = int(breadth_df.index.get_indexer([current_date])[0])
            if loc_b > 0:
                prev_pct_above_200 = float(breadth_df.iloc[loc_b - 1].get("Pct_Above_MA200", pct_above_200))

        vni_above_ma20 = vni_above_ma50 = True
        vni_green_day = False
        if vnindex_df is not None and current_date in vnindex_df.index:
            v_row = vnindex_df.loc[current_date]
            v_c = float(v_row["Close"])
            vni_above_ma20 = bool(pd.isna(v_row.get("MA20")) or v_c >= v_row["MA20"])
            vni_above_ma50 = bool(pd.isna(v_row.get("MA50")) or v_c >= v_row["MA50"])
            vni_green_day = bool(float(v_row.get("Pct", 0.0)) >= 0.3)

        is_panic_zone_today = (pct_above_200 <= panic_ma200_thresh) and (pct_bottoming >= panic_bot52_thresh)
        if is_panic_zone_today:
            was_in_panic_zone = True
            panic_cooldown_days = 15
        elif panic_cooldown_days > 0:
            panic_cooldown_days -= 1
            if pct_above_200 >= 35.0:
                was_in_panic_zone = False
                panic_cooldown_days = 0
        else:
            was_in_panic_zone = False

        can_bottom_fish = (
            use_bottom_fishing
            and (is_panic_zone_today or was_in_panic_zone)
            and (vni_green_day or pct_above_200 > prev_pct_above_200)
        )
        is_euphoria_top = (
            use_top_climax
            and (breadth_peak10 >= climax_breadth_thresh)
            and (pct_above_200 < breadth_peak10 - 2.0)
            and (risk_score >= 3.5 or not vni_above_ma20)
        )

        target_exposure = 1.0
        if use_dd_shield:
            target_exposure = get_target_exposure_from_risk(
                risk_score, p["t_low"], p["t_med"], p["t_high"], p["t_crit"]
            )
            if not vni_above_ma50 and cnt_dd >= 4:
                target_exposure = min(target_exposure, 0.25)
            elif not vni_above_ma20 and cnt_dd >= 5:
                target_exposure = min(target_exposure, 0.40)

        if is_euphoria_top:
            target_exposure = min(target_exposure, 0.50)
        if can_bottom_fish:
            target_exposure = max(target_exposure, 0.60)

        active_holdings_val = 0.0
        pending_holdings_val = 0.0
        to_sell = []

        for sym, pos in list(holdings.items()):
            df = data_map.get(sym)
            if df is None or current_date not in df.index:
                active_holdings_val += pos["qty"] * pos["last_price"] * 1000.0
                continue
            row = df.loc[current_date]
            curr_price = float(row["Close"])
            pos["last_price"] = curr_price
            active_holdings_val += pos["qty"] * curr_price * 1000.0

            pct_pnl = (curr_price - pos["price"]) / pos["price"]
            days_held = (current_date.date() - pos["date"]).days
            is_bot_bet = pos.get("is_bottom_bet", False)

            if use_power_play and not pos.get("is_power_play") and not is_bot_bet:
                if pct_pnl >= 0.20 and days_held <= 15:
                    pos["is_power_play"] = True

            reason = None
            if is_bot_bet:
                if pct_pnl <= -0.05:
                    reason = f"Cắt lỗ Bắt đáy ({pct_pnl * 100:.1f}%)"
                elif pct_pnl >= 0.15:
                    reason = f"Chốt lời Bắt đáy (+{pct_pnl * 100:.1f}%)"
                elif pd.notna(row.get("MA10")) and curr_price < row["MA10"] and days_held >= 3:
                    reason = f"Gãy MA10 Bắt đáy ({pct_pnl * 100:+.1f}%)"
            else:
                if pct_pnl <= -stop_loss:
                    reason = f"Cắt lỗ ({pct_pnl * 100:.1f}%)"
                elif is_euphoria_top and pct_pnl >= 0.12 and pd.notna(row.get("MA10")) and curr_price < row["MA10"]:
                    reason = f"Bán Đỉnh Hưng Phấn <MA10 (+{pct_pnl * 100:.1f}%)"
                elif use_take_profit and pct_pnl >= take_profit and not pos.get("is_power_play"):
                    reason = f"Chốt lời mục tiêu (+{pct_pnl * 100:.1f}%)"
                else:
                    use_ma50_trail = pos.get("is_power_play") and days_held < 56
                    trend_line = row["MA50"] if use_ma50_trail else row["MA_Exit"]
                    if pd.notna(trend_line) and curr_price < trend_line:
                        exit_name = "MA50 (PP)" if use_ma50_trail else f"MA{ma_exit}"
                        reason = f"Gãy {exit_name} ({pct_pnl * 100:+.1f}%)"

            if reason:
                to_sell.append((sym, curr_price, reason))

        for item in pending_stocks:
            df = data_map.get(item[1])
            price = float(df.loc[current_date]["Close"]) if (df is not None and current_date in df.index) else float(item[3])
            pending_holdings_val += item[2] * price * 1000.0

        for sym, price, reason in to_sell:
            qty = holdings[sym]["qty"]
            buy_price = holdings[sym]["price"]
            proceeds = qty * price * 1000.0 * (1.0 - fee)
            cost_basis = qty * buy_price * 1000.0
            settle_idx = min(day_idx + t_plus, total_days - 1)
            pending_cash.append((settle_idx, proceeds))
            active_holdings_val -= qty * price * 1000.0
            vcp_note = holdings[sym].get("vcp_tag", "")
            pp_note = " [PP]" if holdings[sym].get("is_power_play") else ""
            trades_history.append({
                "Ngày": current_date.strftime("%d/%m/%Y"), "Mã": sym, "Lệnh": "SELL",
                "Giá": round(price, 2), "KL": qty, "Lãi/Lỗ": round(proceeds - cost_basis, 0),
                "Ghi chú": f"{vcp_note}{pp_note} (T+{t_plus})".strip(), "Lý do": reason,
            })
            closed_trades.append({
                "Mã": sym, "Ngày Mua": holdings[sym]["date"].strftime("%d/%m/%Y"),
                "Ngày Bán": current_date.strftime("%d/%m/%Y"),
                "Giá Mua": round(buy_price, 2), "Giá Bán": round(price, 2), "KL": qty,
                "Lãi/Lỗ": round(proceeds - cost_basis, 0),
                "% Lãi/Lỗ": round((price - buy_price) / buy_price * 100.0, 2),
                "Lý do": f"{reason} | {vcp_note}" if vcp_note else reason,
            })
            del holdings[sym]

        total_stock_val = active_holdings_val + pending_holdings_val
        pending_cash_val = sum(x[1] for x in pending_cash)
        total_nav = cash + pending_cash_val + total_stock_val
        target_equity_val = total_nav * target_exposure

        if use_dd_shield and total_stock_val > target_equity_val * 1.05 and active_holdings_val > 0:
            keep_ratio = 0.0 if target_exposure == 0.0 else (target_equity_val / total_stock_val)
            for sym, pos in list(holdings.items()):
                if keep_ratio > 0 and pos.get("is_power_play", False):
                    continue
                current_qty = pos["qty"]
                target_qty = int(current_qty * keep_ratio)
                sell_qty = current_qty - target_qty
                if sell_qty > 0:
                    price = pos["last_price"]
                    proceeds = sell_qty * price * 1000.0 * (1.0 - fee)
                    cost_basis = sell_qty * pos["price"] * 1000.0
                    settle_idx = min(day_idx + t_plus, total_days - 1)
                    pending_cash.append((settle_idx, proceeds))
                    total_stock_val -= sell_qty * price * 1000.0
                    active_holdings_val -= sell_qty * price * 1000.0
                    pending_cash_val += proceeds
                    trim_reason = "Bán Đỉnh Hưng Phấn" if is_euphoria_top else f"Hạ Tỷ Trọng PP (Risk={risk_score:.1f})"
                    if target_qty > 0:
                        holdings[sym]["qty"] = target_qty
                        note_txt = f"Hạ {100 * (1.0 - keep_ratio):.0f}% (T+{t_plus})"
                    else:
                        del holdings[sym]
                        note_txt = f"Thoát hết (T+{t_plus})"
                    trades_history.append({
                        "Ngày": current_date.strftime("%d/%m/%Y"), "Mã": sym, "Lệnh": "SELL",
                        "Giá": round(price, 2), "KL": sell_qty, "Lãi/Lỗ": round(proceeds - cost_basis, 0),
                        "Ghi chú": note_txt, "Lý do": trim_reason,
                    })
                    closed_trades.append({
                        "Mã": sym, "Ngày Mua": pos["date"].strftime("%d/%m/%Y"),
                        "Ngày Bán": current_date.strftime("%d/%m/%Y"),
                        "Giá Mua": round(pos["price"], 2), "Giá Bán": round(price, 2), "KL": sell_qty,
                        "Lãi/Lỗ": round(proceeds - cost_basis, 0),
                        "% Lãi/Lỗ": round((price - pos["price"]) / pos["price"] * 100.0, 2),
                        "Lý do": trim_reason,
                    })

        current_symbols = set(holdings.keys()) | set([x[1] for x in pending_stocks])
        allow_normal_vcp_buy = (not is_euphoria_top) and vni_above_ma20 and (target_exposure >= 0.5)

        if (allow_normal_vcp_buy or can_bottom_fish) and total_stock_val < target_equity_val and len(current_symbols) < max_pos and cash >= 10_000_000:
            allowed_sectors = daily_top_sectors_map.get(current_date, set()) if filter_top_sectors else None
            sec_counts = {}
            for s in current_symbols:
                sec = HARDCODED_HOSE_INDUSTRIES_MAPPING.get(s, "Khác")
                sec_counts[sec] = sec_counts.get(sec, 0) + 1

            candidates = []
            cur_date_obj = current_date.date()
            for sym in tradable_symbols:
                if sym in current_symbols:
                    continue
                sec = HARDCODED_HOSE_INDUSTRIES_MAPPING.get(sym, "Khác")
                if sec_counts.get(sec, 0) >= max_per_sector:
                    continue
                df = data_map.get(sym)
                if df is None or current_date not in df.index:
                    continue
                row = df.loc[current_date]
                c, vol = float(row["Close"]), float(row["Volume"])
                vol_ma20 = float(row.get("VolMA20", 0) or 0.0)
                vol_ma10 = float(row.get("VolMA10", 0) or 0.0)
                rs = int(row.get("RS_Rating", 0) or 0)
                if vol < min_vol or vol_ma20 <= 0 or c <= 0:
                    continue

                if allow_normal_vcp_buy:
                    if allowed_sectors is not None and sec not in allowed_sectors:
                        continue
                    if (vol / vol_ma20) < vol_mult or float(row.get("Close_Pos", 0.5)) < 0.5:
                        continue
                    ma50, ma150, ma200, ma200_20 = row.get("MA50"), row.get("MA150"), row.get("MA200"), row.get("MA200_20D_ago")
                    if (
                        pd.notna(ma50) and pd.notna(ma150) and pd.notna(ma200) and pd.notna(ma200_20)
                        and (c > ma50 > ma150 > ma200 and ma200 > ma200_20)
                        and (float(row.get("Pct_From_Bottom", 0)) >= 25.0 and float(row.get("Pct_From_Peak", -100)) >= -25.0 and rs >= min_rs)
                    ):
                        vcp_res = detect_vcp_pattern(df, cur_date_obj, lookback_days=150)
                        is_valid_vcp_buy = False
                        trade_tag = "Stage2 Trend"
                        priority = 1
                        if vcp_res is not None and -1.5 <= vcp_res["pct_from_pivot"] <= max_pivot_pct:
                            is_valid_vcp_buy = True
                            priority = 3
                            ranges_str = "->".join([f"{x:.0f}%" for x in vcp_res["ranges"]])
                            trade_tag = f"VCP {vcp_res['num_contractions']}T ({ranges_str})"
                        if entry_mode == 0 and not is_valid_vcp_buy:
                            continue
                        elif entry_mode == 1 and not is_valid_vcp_buy:
                            high_20 = df["Close"].loc[:current_date].iloc[-20:].max()
                            if c < high_20:
                                continue
                            trade_tag = "Stage2 Breakout 20D"
                            priority = 2
                        candidates.append((sym, priority * 1000.0 + rs * 5.0 + (vol / vol_ma20), c, sec, rs, trade_tag, False))
                elif can_bottom_fish:
                    if (
                        rs >= max(65, min_rs - 5) and float(row.get("Pct", 0.0)) >= 2.5
                        and float(row.get("Close_Pos", 0.0)) >= 0.6 and pd.notna(row.get("MA10")) and c > row["MA10"]
                        and vol_ma10 > 0 and (vol / vol_ma10) >= 1.2
                    ):
                        candidates.append((sym, 500.0 + rs * 5.0 + (vol / vol_ma10), c, sec, rs, f"Bắt Đáy Hoảng Loạn (MA200={pct_above_200:.0f}%)", True))

            candidates.sort(key=lambda x: x[1], reverse=True)
            buy_pow = target_equity_val - total_stock_val
            slots = max_pos - len(current_symbols)
            for i in range(min(slots, len(candidates))):
                if buy_pow < 10_000_000 or cash < 10_000_000:
                    break
                sym, _, price, sec, rs_val, trade_tag, is_bot_bet = candidates[i]
                if sec_counts.get(sec, 0) >= max_per_sector:
                    continue
                alloc_amt = min(cash, total_nav / max_pos, buy_pow)
                qty = int((alloc_amt // (price * 1000.0 * (1.0 + fee))) // 100) * 100
                cost = qty * price * 1000.0 * (1.0 + fee)
                if qty > 0 and cash >= cost:
                    cash -= cost
                    settle_idx = min(day_idx + t_plus, total_days - 1)
                    pending_stocks.append((settle_idx, sym, qty, price, cur_date_obj, sec, trade_tag, is_bot_bet))
                    pending_holdings_val += qty * price * 1000.0
                    total_stock_val += qty * price * 1000.0
                    buy_pow -= qty * price * 1000.0
                    sec_counts[sec] = sec_counts.get(sec, 0) + 1
                    trades_history.append({
                        "Ngày": current_date.strftime("%d/%m/%Y"), "Mã": sym, "Lệnh": "BUY",
                        "Giá": round(price, 2), "KL": qty, "Lãi/Lỗ": 0,
                        "Ghi chú": f"Hàng về T+{t_plus}", "Lý do": f"{trade_tag} | RS={rs_val}",
                    })

        pending_cash_val = sum(x[1] for x in pending_cash)
        total_stock_val = active_holdings_val + pending_holdings_val
        total_nav = cash + pending_cash_val + total_stock_val
        actual_exposure_pct = (total_stock_val / total_nav * 100.0) if total_nav > 0 else 0.0

        equity_history.append({
            "Date": current_date,
            "NAV": total_nav,
            "Exposure": actual_exposure_pct,
            "Breadth200": pct_above_200,
            "Risk": risk_score,
            "IsPanic": is_panic_zone_today,
            "IsClimax": is_euphoria_top,
        })

        all_hold_strs = []
        for s, d in holdings.items():
            tag = "(Đáy)" if d.get("is_bottom_bet") else ("(PP)" if d.get("is_power_play") else "")
            all_hold_strs.append(f"{s}{tag}")
        for p_stk in pending_stocks:
            if p_stk[1] not in [x.split("(")[0] for x in all_hold_strs]:
                all_hold_strs.append(f"{p_stk[1]}(T+)")

        daily_snapshots.append({
            "Ngày": current_date.strftime("%d/%m/%Y"),
            "Tổng NAV": round(total_nav, 0),
            "Tiền Mặt": round(cash, 0),
            "Tiền Chờ Về": round(pending_cash_val, 0),
            "Giá Trị CP": round(total_stock_val, 0),
            "Risk Score": round(risk_score, 1),
            "% > MA200": round(pct_above_200, 1),
            "Danh Mục Nắm Giữ": ", ".join(sorted(list(set(all_hold_strs)))),
        })

    equity_df = pd.DataFrame(equity_history).set_index("Date")
    if equity_df.empty:
        return {}

    final_nav = float(equity_df["NAV"].iloc[-1])
    profit = final_nav - initial_capital
    days = (all_dates[-1] - all_dates[0]).days
    cagr = (final_nav / initial_capital) ** (365.0 / days) - 1.0 if days > 0 and initial_capital > 0 else 0.0
    peak = equity_df["NAV"].cummax()
    max_dd = float(((equity_df["NAV"] - peak) / peak).min()) * 100.0
    win_trades = sum(1 for t in closed_trades if t["Lãi/Lỗ"] > 0)
    win_rate = (win_trades / len(closed_trades) * 100.0) if closed_trades else 0.0

    return {
        "stats": {
            "Initial": initial_capital, "Final": final_nav, "Profit": profit,
            "Profit %": (profit / initial_capital) * 100.0 if initial_capital > 0 else 0.0,
            "Max DD": max_dd, "Total Trades": len(closed_trades),
            "Win Rate": win_rate, "CAGR": cagr * 100.0,
        },
        "equity": equity_df,
        "trades": pd.DataFrame(trades_history),
        "closed": pd.DataFrame(closed_trades),
        "snapshots": pd.DataFrame(daily_snapshots),
    }

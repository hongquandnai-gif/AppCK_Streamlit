# ========================= main.py =========================
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from core.constants import (
    HARDCODED_HOSE_INDUSTRIES_MAPPING,
    INDUSTRY_GROUPS,
    MA_COLORS,
    MA_WINDOWS,
    get_symbols_by_industry,
    is_penny_stock,
)
from core.quant_engine import (
    compute_distribution_days_core,
    detect_vcp_pattern,
    evaluate_market_ftd_step,
    evaluate_stock_phase,
    get_target_exposure_from_risk,
    run_hybrid_backtest,
    run_minervini_screener,
)
from core.ssi_client import (
    fetch_batch_ohlcv_ssi,
    fetch_ssi_ohlcv,
    fetch_ssi_stock_list,
    get_ssi_ws_manager,
    vn_now,
    vn_today,
)

# ==============================================================================
# CẤU HÌNH TRANG & CSS TỐI ƯU DASHBOARD
# ==============================================================================
st.set_page_config(
    page_title="V11 PRO - Phân Tích Cổ Phiếu & SSI WebSocket",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 1rem; max-width: 98%; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #0284c7;
        padding: 10px 14px;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    .ws-badge-on {
        background-color: #dcfce7; color: #166534; padding: 4px 12px;
        border-radius: 999px; font-weight: 700; font-size: 13px;
    }
    .ws-badge-off {
        background-color: #fee2e2; color: #991b1b; padding: 4px 12px;
        border-radius: 999px; font-weight: 700; font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# Khởi động SSI WebSocket Manager & Tải danh sách mã SSI
ws_mgr = get_ssi_ws_manager()
ssi_stocks_meta = fetch_ssi_stock_list("hose")
TODAY_VN = vn_today()


# ==============================================================================
# THANH ĐIỀU HƯỚNG ĐỈNH (TOP NAVIGATION BAR - 5 WORKSPACES)
# ==============================================================================
hdr_col1, hdr_col2 = st.columns([3, 1.3])
with hdr_col1:
    st.markdown("### 📊 V11 PRO — Hệ Thống Phân Tích Định Lượng & SSI Realtime")
with hdr_col2:
    vn_clock = vn_now().strftime("%d/%m/%Y %H:%M")
    ws_status_html = (
        f'<div style="text-align:right; padding-top:8px;">'
        f'<span class="ws-badge-on">🟢 SSI WS ({len(ssi_stocks_meta)} mã) • {vn_clock}</span>'
        f'</div>'
        if ws_mgr.is_connected else
        f'<div style="text-align:right; padding-top:8px;">'
        f'<span class="ws-badge-off">🟡 SSI WS Reconnecting • {vn_clock}</span>'
        f'</div>'
    )
    st.markdown(ws_status_html, unsafe_allow_html=True)

workspace = st.radio(
    "Workspace",
    [
        "🌐 Toàn Cảnh Thị Trường",
        "🧭 Sóng Ngành & Dòng Tiền",
        "🎯 Lọc Cổ Phiếu Đột Phá",
        "📈 Phân Tích Biểu Đồ",
        "💼 Danh Mục & Backtest",
    ],
    horizontal=True,
    label_visibility="collapsed",
)
st.divider()


# ==============================================================================
# WORKSPACE 1: TOÀN CẢNH THỊ TRƯỜNG
# ==============================================================================
if workspace == "🌐 Toàn Cảnh Thị Trường":
    t1, t2, t3 = st.tabs([
        "⏱️ Chỉ Số Trực Tiếp (SSI Realtime)",
        "🗺️ Bản Đồ Nhiệt (Treemap)",
        "🩺 Sức Khỏe & Ngày Phân Phối",
    ])

    # --- SUB-TAB 1.1: CHỈ SỐ TRỰC TIẾP ---
    with t1:
        c1, c2, c3 = st.columns([1.2, 1.5, 3])
        with c1:
            idx_date = st.date_input("Ngày giao dịch", value=TODAY_VN, key="idx_live_date")
        with c2:
            selected_indices = st.multiselect(
                "Chọn chỉ số hiển thị",
                ["VNINDEX", "VN30", "HNX", "UPCOM"],
                default=["VNINDEX", "VN30", "HNX", "UPCOM"],
            )
        with c3:
            st.write("")
            if st.button("🔄 Làm mới dữ liệu Intraday & Đồng bộ WebSocket", type="primary"):
                ws_mgr.subscribe(selected_indices)
                st.cache_data.clear()

        if selected_indices:
            ws_mgr.subscribe(selected_indices)
            live_ticks = ws_mgr.get_snapshot(selected_indices)

            cols_kpi = st.columns(len(selected_indices))
            fig_idx = make_subplots(
                rows=2, cols=2,
                subplot_titles=selected_indices[:4],
                vertical_spacing=0.14, horizontal_spacing=0.08,
            )

            for i, sym in enumerate(selected_indices[:4]):
                df_1m = fetch_ssi_ohlcv(sym, idx_date - timedelta(days=5), idx_date, "1")
                df_d = fetch_ssi_ohlcv(sym, idx_date - timedelta(days=15), idx_date, "D")

                prev_close = None
                if not df_d.empty:
                    df_prev = df_d[df_d.index.date < idx_date]
                    if not df_prev.empty:
                        prev_close = float(df_prev["Close"].iloc[-1])

                last_px = delta = pct = vol = 0.0
                if not df_1m.empty:
                    last_day = df_1m.index[-1].date()
                    df_day = df_1m[df_1m.index.date == last_day]
                    last_px = float(df_day["Close"].iloc[-1])
                    vol = float(df_day["Volume"].sum())
                    if prev_close:
                        delta = last_px - prev_close
                        pct = (delta / prev_close) * 100.0

                    if sym in live_ticks and live_ticks[sym].get("last"):
                        last_px = float(live_ticks[sym]["last"])
                        if prev_close:
                            delta = last_px - prev_close
                            pct = (delta / prev_close) * 100.0

                    r_idx, c_idx = (i // 2) + 1, (i % 2) + 1
                    line_col = "#10b981" if delta >= 0 else "#ef4444"
                    fig_idx.add_trace(
                        go.Scatter(
                            x=df_day.index, y=df_day["Close"],
                            mode="lines", name=sym, line=dict(color=line_col, width=2),
                        ),
                        row=r_idx, col=c_idx,
                    )
                    if prev_close:
                        fig_idx.add_hline(
                            y=prev_close, line_dash="dash", line_color="#64748b",
                            row=r_idx, col=c_idx,
                        )

                with cols_kpi[i]:
                    st.metric(
                        label=f"{sym} (KL: {vol:,.0f})",
                        value=f"{last_px:,.2f}",
                        delta=f"{delta:+.2f} ({pct:+.2f}%)",
                    )

            fig_idx.update_layout(height=540, showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_idx, width="stretch")

    # --- SUB-TAB 1.2: BẢN ĐỒ NHIỆT TREEMAP ---
    with t2:
        col_tm1, col_tm2 = st.columns([1.2, 4])
        with col_tm1:
            tm_date = st.date_input("Ngày bản đồ nhiệt", value=TODAY_VN, key="tm_date")
        with col_tm2:
            st.write("")
            run_tm = st.button("🗺️ Tạo Bản Đồ Nhiệt Dòng Tiền", type="primary")

        if run_tm:
            all_syms = [s for s, ind in HARDCODED_HOSE_INDUSTRIES_MAPPING.items() if ind != "Chỉ số"]
            prog = st.progress(0, text="Đang tải dữ liệu toàn sàn từ SSI...")
            raw_map = fetch_batch_ohlcv_ssi(
                all_syms, tm_date - timedelta(days=10), tm_date, "D",
                progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
            )
            prog.empty()

            rows_tm = []
            for sym, df in raw_map.items():
                sub = df[df.index.date <= tm_date]
                if len(sub) >= 2:
                    c_now = float(sub["Close"].iloc[-1])
                    c_prev = float(sub["Close"].iloc[-2])
                    vol = float(sub["Volume"].iloc[-1])
                    if vol > 0 and c_prev > 0:
                        pct = (c_now - c_prev) / c_prev * 100.0
                        ind = "Penny" if is_penny_stock(sym) else HARDCODED_HOSE_INDUSTRIES_MAPPING.get(sym, "Khác")
                        rows_tm.append({
                            "Mã": sym, "Ngành": ind,
                            "GTGD (Tỷ)": round(c_now * vol / 1e6, 2),
                            "% Thay đổi": round(pct, 2),
                            "Giá": round(c_now, 2),
                        })

            if rows_tm:
                df_tm = pd.DataFrame(rows_tm)
                fig_tm = px.treemap(
                    df_tm,
                    path=[px.Constant("HOSE"), "Ngành", "Mã"],
                    values="GTGD (Tỷ)",
                    color="% Thay đổi",
                    color_continuous_scale=["#0284c7", "#ef4444", "#f59e0b", "#10b981", "#9333ea"],
                    color_continuous_midpoint=0.0,
                    hover_data=["Giá", "% Thay đổi", "GTGD (Tỷ)"],
                )
                fig_tm.update_layout(height=680, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_tm, width="stretch")
            else:
                st.warning("Không có dữ liệu giao dịch trong ngày đã chọn.")

    # --- SUB-TAB 1.3: SỨC KHỎE & NGÀY PHÂN PHỐI ---
    with t3:
        c1, c2, c3, c4 = st.columns(4)
        ma_date = c1.date_input("Ngày phân tích", value=TODAY_VN, key="ma_date")
        dd_win = c2.number_input("Cửa sổ DD (phiên)", 10, 60, 25)
        cancel_reb = c3.number_input("Xóa DD khi hồi (%)", 3.0, 15.0, 6.0, step=0.5)
        scan_sec = c4.checkbox("Quét sức mạnh ngành (>MA20)", value=True)

        if st.button("🩺 Phân Tích Sức Khỏe Thị Trường", type="primary"):
            idx_map = fetch_batch_ohlcv_ssi(
                ["VNINDEX", "VN30", "HNX", "UPCOM"],
                ma_date - timedelta(days=365), ma_date, "D", max_workers=4,
            )
            st.subheader("📋 Tổng Hợp Ngày Phân Phối & Rủi Ro")
            for idx_name in ["VNINDEX", "VN30", "HNX", "UPCOM"]:
                df_i = idx_map.get(idx_name)
                if df_i is not None and not df_i.empty:
                    dd, stall, churn, score, details = compute_distribution_days_core(
                        df_i, window=int(dd_win), cancel_rebound_pct=float(cancel_reb), return_details=True
                    )
                    dd_dates = ", ".join([d.strftime("%d/%m") for d in details[details["type"] == "DD"].index]) if not details.empty else "—"
                    extra = ""
                    if idx_name == "VNINDEX":
                        alloc = get_target_exposure_from_risk(score) * 100
                        extra = f" | **Risk Score: `{score:.1f}` → Tỷ trọng mục tiêu: `{alloc:.0f}%`**"
                    st.info(f"**{idx_name}**: Phân phối **{dd}** ({dd_dates}) | Stalling **{stall}** | Churning **{churn}**{extra}")

            if scan_sec:
                syms = [s for s, ind in HARDCODED_HOSE_INDUSTRIES_MAPPING.items() if ind not in ("Chỉ số", "Penny") and not is_penny_stock(s)]
                prog = st.progress(0, text="Đang quét sức mạnh các nhóm ngành...")
                sec_dfs = fetch_batch_ohlcv_ssi(
                    syms, ma_date - timedelta(days=150), ma_date, "D",
                    progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
                )
                prog.empty()

                sec_groups: dict = {}
                for s, df_s in sec_dfs.items():
                    if len(df_s) >= 55:
                        ind = HARDCODED_HOSE_INDUSTRIES_MAPPING.get(s, "Khác")
                        c_last = df_s["Close"].iloc[-1]
                        ma20 = df_s["Close"].rolling(20).mean().iloc[-1]
                        ma50 = df_s["Close"].rolling(50).mean().iloc[-1]
                        g = sec_groups.setdefault(ind, {"tot": 0, "a20": 0, "b50": 0})
                        g["tot"] += 1
                        if c_last > ma20:
                            g["a20"] += 1
                        if c_last < ma50:
                            g["b50"] += 1

                col_l, col_w = st.columns(2)
                lead_rows = [
                    {"Ngành": k, "% > MA20": round(v["a20"] / v["tot"] * 100, 1), "Số mã": v["tot"]}
                    for k, v in sec_groups.items() if v["tot"] > 0 and (v["a20"] / v["tot"]) > 0.5
                ]
                weak_rows = [
                    {"Ngành": k, "% < MA50": round(v["b50"] / v["tot"] * 100, 1), "Số mã": v["tot"]}
                    for k, v in sec_groups.items() if v["tot"] > 0 and (v["b50"] / v["tot"]) > 0.5
                ]
                with col_l:
                    st.markdown("#### 🔥 Nhóm Ngành DẪN DẮT (> 50% mã trên MA20)")
                    st.dataframe(pd.DataFrame(lead_rows).sort_values("% > MA20", ascending=False) if lead_rows else pd.DataFrame(), width="stretch", hide_index=True)
                with col_w:
                    st.markdown("#### ❄️ Nhóm Ngành SUY YẾU (> 50% mã dưới MA50)")
                    st.dataframe(pd.DataFrame(weak_rows).sort_values("% < MA50", ascending=False) if weak_rows else pd.DataFrame(), width="stretch", hide_index=True)


# ==============================================================================
# WORKSPACE 2: SÓNG NGÀNH & DÒNG TIỀN
# ==============================================================================
elif workspace == "🧭 Sóng Ngành & Dòng Tiền":
    t_ma, t_mf = st.tabs(["🧭 Xu Hướng MA Ngành", "💸 Dòng Tiền Ngành (Money Flow)"])

    with t_ma:
        c1, c2, c3 = st.columns([2, 1.5, 2])
        ind_choice = c1.selectbox("Nhóm ngành", [g for g in INDUSTRY_GROUPS if g != "Chỉ số"])
        ma_asof = c2.date_input("Ngày tra cứu", value=TODAY_VN, key="sec_ma_date")
        c3.write("")
        if c3.button("🔄 Quét Xu Hướng MA", type="primary"):
            syms = get_symbols_by_industry(ind_choice, exclude_penny=(ind_choice == "Tất cả ngành"))
            prog = st.progress(0)
            dfs = fetch_batch_ohlcv_ssi(
                syms, ma_asof - timedelta(days=400), ma_asof, "D",
                progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
            )
            prog.empty()

            if ind_choice == "Tất cả ngành":
                groups = {}
                for s, df_s in dfs.items():
                    if len(df_s) >= 50:
                        ind = HARDCODED_HOSE_INDUSTRIES_MAPPING.get(s, "Khác")
                        c_now = float(df_s["Close"].iloc[-1])
                        ma20 = float(df_s["Close"].rolling(20).mean().iloc[-1])
                        ma50 = float(df_s["Close"].rolling(50).mean().iloc[-1])
                        g = groups.setdefault(ind, {"tot": 0, "a20": 0, "b50": 0})
                        g["tot"] += 1
                        if c_now > ma20:
                            g["a20"] += 1
                        if c_now < ma50:
                            g["b50"] += 1
                rows = []
                for ind, g in groups.items():
                    pct_s = round(g["a20"] / g["tot"] * 100, 1)
                    pct_w = round(g["b50"] / g["tot"] * 100, 1)
                    lbl = "DẪN DẮT" if pct_s >= 50 else ("YẾU" if pct_w >= 50 else "TRUNG LẬP")
                    rows.append({"Ngành": ind, "Phân loại": lbl, "% Mạnh (>MA20)": pct_s, "% Yếu (<MA50)": pct_w, "Tổng mã": g["tot"]})
                st.dataframe(pd.DataFrame(rows).sort_values("% Mạnh (>MA20)", ascending=False), width="stretch", hide_index=True)
            else:
                rows = []
                for s, df_s in dfs.items():
                    if not df_s.empty:
                        c_now = float(df_s["Close"].iloc[-1])
                        c_prev = float(df_s["Close"].iloc[-2]) if len(df_s) >= 2 else c_now
                        item = {"Mã": s, "Giá": round(c_now, 2), "% Thay đổi": round((c_now / c_prev - 1) * 100, 2)}
                        for w in MA_WINDOWS:
                            if len(df_s) >= w:
                                mv = float(df_s["Close"].rolling(w).mean().iloc[-1])
                                stt = "TRÊN" if c_now > mv else "DƯỚI"
                                item[f"MA{w}"] = f"{stt} ({mv:,.2f})"
                            else:
                                item[f"MA{w}"] = "—"
                        rows.append(item)
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    with t_mf:
        c1, c2, c3, c4 = st.columns([1.2, 1, 1.5, 1.2])
        mf_date = c1.date_input("Ngày kết thúc", value=TODAY_VN, key="mf_date")
        mf_days = c2.number_input("Số phiên", 3, 60, 10)
        mf_method = c3.selectbox("Phương pháp", ["ΔP × Vol (VNĐ)", "Signed TP × Vol (VNĐ)", "CMF × GTGD (VNĐ)"])
        c4.write("")
        if c4.button("💸 Phân Tích Dòng Tiền", type="primary"):
            syms = [s for s, ind in HARDCODED_HOSE_INDUSTRIES_MAPPING.items() if ind != "Chỉ số"]
            prog = st.progress(0)
            dfs = fetch_batch_ohlcv_ssi(
                syms, mf_date - timedelta(days=int(mf_days) * 2 + 15), mf_date, "D",
                progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
            )
            prog.empty()

            per_ind: dict = {}
            for sym, df_s in dfs.items():
                sub = df_s[df_s.index.date <= mf_date]
                if len(sub) < int(mf_days) + 1:
                    continue
                sub = sub.iloc[-(int(mf_days) + 1):].copy()
                hl = (sub["High"] - sub["Low"]).replace(0, np.nan)
                sub["PrevClose"] = sub["Close"].shift(1)
                sub["TP"] = (sub["High"] + sub["Low"] + sub["Close"]) / 3.0
                sub["PrevTP"] = sub["TP"].shift(1)
                sub["MF_mult"] = (((sub["Close"] - sub["Low"]) - (sub["High"] - sub["Close"])) / hl).fillna(0.0)

                calc = sub.iloc[1:]
                vol = calc["Volume"].astype(float)
                tv = float((calc["Close"] * 1000.0 * vol).sum())
                dp_vol = float(((calc["Close"] - calc["PrevClose"]) * 1000.0 * vol).sum())
                stpv = float((np.sign(calc["TP"] - calc["PrevTP"]) * calc["TP"] * 1000.0 * vol).sum())
                cmf_r = float((calc["MF_mult"] * vol).sum() / vol.sum()) if vol.sum() > 0 else 0.0
                pct = float(sub["Close"].iloc[-1] / sub["Close"].iloc[0] - 1.0) * 100.0

                ind = "Penny" if is_penny_stock(sym) else HARDCODED_HOSE_INDUSTRIES_MAPPING.get(sym, "Khác")
                g = per_ind.setdefault(ind, {"dp": 0.0, "stp": 0.0, "cmf_num": 0.0, "tv": 0.0, "pcts": [], "cnt": 0})
                g["dp"] += dp_vol
                g["stp"] += stpv
                g["cmf_num"] += cmf_r * tv
                g["tv"] += tv
                g["pcts"].append(pct)
                g["cnt"] += 1

            rows_mf = []
            for ind, g in per_ind.items():
                net_vnd = g["dp"] if "ΔP" in mf_method else (g["stp"] if "Signed" in mf_method else g["cmf_num"])
                rows_mf.append({
                    "Ngành": ind,
                    "Dòng tiền ròng (Tỷ VNĐ)": round(net_vnd / 1e9, 2),
                    "Tổng GTGD (Tỷ VNĐ)": round(g["tv"] / 1e9, 2),
                    "CMF (N phiên)": round(g["cmf_num"] / g["tv"], 3) if g["tv"] > 0 else 0.0,
                    "% Giá TB": round(float(np.mean(g["pcts"])), 2),
                    "Số mã": g["cnt"],
                })
            df_mf = pd.DataFrame(rows_mf).sort_values("Dòng tiền ròng (Tỷ VNĐ)", ascending=False)
            st.dataframe(df_mf, width="stretch", hide_index=True)


# ==============================================================================
# WORKSPACE 3: LỌC CỔ PHIẾU ĐỘT PHÁ (RADAR EOD + MINERVINI VCP + GAINERS)
# ==============================================================================
elif workspace == "🎯 Lọc Cổ Phiếu Đột Phá":
    t_radar, t_min, t_gain = st.tabs([
        "🏆 Radar Xếp Hạng EOD (FTD)",
        "⚡ Minervini & VCP Pro",
        "🚀 Lọc CP Tăng Mạnh",
    ])

    # --- SUB-TAB 3.1: RADAR EOD ---
    with t_radar:
        c1, c2, c3, c4 = st.columns([1, 1, 1.5, 1.5])
        ma_f = c1.number_input("MA Nhanh", 5, 50, 20)
        ma_m = c2.number_input("MA Trung", 20, 100, 50)
        min_v = c3.number_input("Min Volume", 0, 10_000_000, 100_000, step=50_000)
        c4.write("")
        if c4.button("📡 Quét Thị Trường EOD", type="primary"):
            syms = get_symbols_by_industry("Tất cả ngành", exclude_penny=True) + ["VNINDEX"]
            prog = st.progress(0)
            dfs = fetch_batch_ohlcv_ssi(
                syms, TODAY_VN - timedelta(days=350), TODAY_VN, "D",
                progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
            )
            prog.empty()

            vni = dfs.get("VNINDEX")
            if vni is not None and not vni.empty:
                vni["VolMA20"] = vni["Volume"].rolling(20).mean()
                ftd_state = {"historical_peak": 0.0, "reference_peak": 0.0, "is_confirmed_uptrend": True, "rally_attempt_count": 0, "rally_low": float("inf"), "market_phase": "Uptrend"}
                for i in range(len(vni)):
                    r = vni.iloc[i]
                    p_c = float(vni["Close"].iloc[i - 1]) if i > 0 else float(r["Close"])
                    p_v = float(vni["Volume"].iloc[i - 1]) if i > 0 else float(r["Volume"])
                    ftd_state = evaluate_market_ftd_step(
                        ftd_state, float(r["Close"]), float(r["Low"]), float(r["Volume"]),
                        p_c, p_v, float(r["VolMA20"] or 0)
                    )
                _, _, _, risk_sc = compute_distribution_days_core(vni, window=25)
                tgt_exp = 0.0 if not ftd_state["is_confirmed_uptrend"] else get_target_exposure_from_risk(risk_sc) * 100

                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Trạng thái thị trường", ftd_state["market_phase"])
                k2.metric("Tỷ trọng khuyến nghị", f"{tgt_exp:.0f}%")
                k3.metric("Độ sâu điều chỉnh", f"{ftd_state['actual_drawdown'] * 100:.1f}%")
                k4.metric("Điểm Rủi Ro (Risk Score)", f"{risk_sc:.1f}")

            stk_rows = []
            for sym, df_s in dfs.items():
                if sym == "VNINDEX" or len(df_s) < 200:
                    continue
                c = float(df_s["Close"].iloc[-1])
                v = float(df_s["Volume"].iloc[-1])
                maf = float(df_s["Close"].rolling(int(ma_f)).mean().iloc[-1])
                mam = float(df_s["Close"].rolling(int(ma_m)).mean().iloc[-1])
                mas = float(df_s["Close"].rolling(200).mean().iloc[-1])
                vma = float(df_s["Volume"].rolling(int(ma_f)).mean().iloc[-1])
                if c > maf and v > min_v and vma > 0:
                    full = (c > maf > mam > mas)
                    v_sc = v / vma
                    sig = "ĐẠT (Full)" if (full and v_sc > 1.0) else ("Chờ Vol" if full else "Nổ Vol (Hồi)")
                    stk_rows.append({
                        "Mã CP": sym, "Ngành": HARDCODED_HOSE_INDUSTRIES_MAPPING.get(sym, "Khác"),
                        "Giá": round(c, 2), "Volume": int(v), "Hệ số Vol": round(v_sc, 2), "Tín Hiệu": sig,
                    })
            st.dataframe(pd.DataFrame(stk_rows).sort_values(["Tín Hiệu", "Hệ số Vol"], ascending=[True, False]).head(50), width="stretch", hide_index=True)

    # --- SUB-TAB 3.2: MINERVINI & VCP PRO ---
    with t_min:
        c1, c2, c3, c4 = st.columns([1.2, 1.2, 1, 1.5])
        min_start = c1.date_input("Từ ngày", value=TODAY_VN - timedelta(days=365), key="min_s")
        min_end = c2.date_input("Đến ngày", value=TODAY_VN, key="min_e")
        min_rs = c3.number_input("RS Rating tối thiểu", 50, 99, 70)
        c4.write("")
        if c4.button("🚀 Quét Siêu Cổ Phiếu Minervini & VCP", type="primary"):
            syms = get_symbols_by_industry("Tất cả ngành", exclude_penny=True)
            prog = st.progress(0, text="Đang tải dữ liệu và tính RS Rating toàn sàn...")
            raw_m = fetch_batch_ohlcv_ssi(
                syms, min_start - timedelta(days=450), min_end, "D",
                progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
            )
            prog.empty()
            proc_map, screened, df_breadth = run_minervini_screener(raw_m, min_start, min_end, int(min_rs))
            st.session_state["min_proc_map"] = proc_map
            st.session_state["min_screened"] = screened
            st.session_state["min_breadth"] = df_breadth

        if "min_screened" in st.session_state:
            screened = st.session_state["min_screened"]
            proc_map = st.session_state["min_proc_map"]
            df_breadth = st.session_state["min_breadth"]

            st.subheader(f"🏆 Danh Sách Cổ Phiếu Đạt Chuẩn Stage 2 ({len(screened)} mã)")
            st.dataframe(pd.DataFrame(screened), width="stretch", hide_index=True)

            if proc_map:
                st.markdown("---")
                st.subheader("🔍 Chẩn Đoán Chu Kỳ & Cấu Trúc VCP Chi Tiết")
                diag_sym = st.selectbox("Chọn mã kiểm tra", sorted(list(proc_map.keys())))
                df_d = proc_map[diag_sym]
                latest = df_d.iloc[-1].to_dict()
                p_title, p_col, p_desc = evaluate_stock_phase(latest)
                vcp = detect_vcp_pattern(df_d, min_end)

                col_info, col_chart = st.columns([1.2, 2.8])
                with col_info:
                    st.markdown(f"**Trạng thái:** :{'green' if '2' in p_title else 'orange'}[{p_title}]")
                    st.write(p_desc)
                    if vcp:
                        st.success(f"**Mô hình VCP {vcp['num_contractions']}T:** {' -> '.join([str(x)+'%' for x in vcp['ranges']])}\n\n**Pivot:** `{vcp['buy_point']:,.2f}` ({vcp['status']})")
                    st.write(f"- **RS Rating:** `{latest.get('RS_Rating', 0)} / 99`")
                    st.write(f"- **Giá / MA50 / MA200:** `{latest['Close']:,.2f}` / `{latest['MA50']:,.2f}` / `{latest['MA200']:,.2f}`")
                    st.write(f"- **Cách đỉnh 52T:** `{latest['Pct_From_Peak']:+.1f}%`")

                with col_chart:
                    sub_p = df_d.tail(150)
                    fig_vcp = go.Figure()
                    fig_vcp.add_trace(go.Candlestick(
                        x=sub_p.index, open=sub_p["Open"], high=sub_p["High"],
                        low=sub_p["Low"], close=sub_p["Close"], name=diag_sym,
                    ))
                    for ma_col, col_hex in [("MA50", "#f97316"), ("MA150", "#8b5cf6"), ("MA200", "#ef4444")]:
                        fig_vcp.add_trace(go.Scatter(x=sub_p.index, y=sub_p[ma_col], name=ma_col, line=dict(color=col_hex, width=1.4)))
                    if vcp:
                        fig_vcp.add_hline(y=vcp["buy_point"], line_dash="dot", line_color="#8b5cf6", annotation_text=f"Pivot: {vcp['buy_point']:,.2f}")
                    fig_vcp.update_layout(height=420, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=25, b=10))
                    st.plotly_chart(fig_vcp, width="stretch")

            if not df_breadth.empty:
                st.markdown("---")
                st.subheader("🌊 Độ Rộng Thị Trường (% Mã > MA200 & % Dò Đáy 52 Tuần)")
                fig_br = make_subplots(specs=[[{"secondary_y": True}]])
                fig_br.add_trace(go.Scatter(x=df_breadth.index, y=df_breadth["Avg_Price"], name="Giá TB HOSE", line=dict(color="#0284c7", width=2)), secondary_y=False)
                fig_br.add_trace(go.Scatter(x=df_breadth.index, y=df_breadth["Pct_Above_MA200"], name="% > MA200", line=dict(color="#f59e0b", width=1.8)), secondary_y=True)
                fig_br.add_trace(go.Scatter(x=df_breadth.index, y=df_breadth["Pct_Bottoming"], name="% Sát đáy 52T", line=dict(color="#ef4444", dash="dot")), secondary_y=True)
                fig_br.update_layout(height=360, margin=dict(l=10, r=10, t=25, b=10))
                st.plotly_chart(fig_br, width="stretch")

    # --- SUB-TAB 3.3: LỌC CP TĂNG MẠNH ---
    with t_gain:
        c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1.5, 1, 1.2])
        g_start = c1.date_input("Từ ngày", value=TODAY_VN - timedelta(days=30), key="g_s")
        g_end = c2.date_input("Đến ngày", value=TODAY_VN, key="g_e")
        g_ind = c3.selectbox("Nhóm ngành", INDUSTRY_GROUPS, key="g_ind")
        g_top = c4.selectbox("Top hiển thị", [10, 20, 30, 50], index=1)
        c5.write("")
        if c5.button("🚀 Lọc Cổ Phiếu", type="primary"):
            syms = get_symbols_by_industry(g_ind, exclude_penny=(g_ind == "Tất cả ngành"))
            prog = st.progress(0)
            dfs = fetch_batch_ohlcv_ssi(
                syms, g_start - timedelta(days=7), g_end, "D",
                progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
            )
            prog.empty()
            g_rows = []
            for sym, df_s in dfs.items():
                sub = df_s[(df_s.index.date >= g_start) & (df_s.index.date <= g_end)]
                if len(sub) >= 2:
                    c0, cl = float(sub["Close"].iloc[0]), float(sub["Close"].iloc[-1])
                    hmax, lmin = float(sub["High"].max()), float(sub["Low"].min())
                    g_rows.append({
                        "Mã CP": sym,
                        "Ngành": HARDCODED_HOSE_INDUSTRIES_MAPPING.get(sym, "Khác"),
                        "% Thay đổi": round((cl - c0) / c0 * 100, 2),
                        "% Hồi từ đáy": round((cl - lmin) / lmin * 100, 2),
                        "% Giảm từ đỉnh": round((cl - hmax) / hmax * 100, 2),
                        "Ngày đạt đỉnh": sub["High"].idxmax().strftime("%Y-%m-%d"),
                    })
            if g_rows:
                df_g = pd.DataFrame(g_rows)
                df_g["Điểm kết hợp"] = df_g["% Hồi từ đáy"] + df_g["% Giảm từ đỉnh"]
                st.dataframe(df_g.sort_values("Điểm kết hợp", ascending=False).head(g_top), width="stretch", hide_index=True)


# ==============================================================================
# WORKSPACE 4: PHÂN TÍCH BIỂU ĐỒ (EOD + INTRADAY + BẢNG GIÁ WEBSOCKET)
# ==============================================================================
elif workspace == "📈 Phân Tích Biểu Đồ":
    t_eod, t_intra = st.tabs(["📉 Biểu Đồ Kỹ Thuật (EOD)", "⚡ Khớp Lệnh Trong Phiên & Bảng Giá SSI"])

    with t_eod:
        c1, c2, c3, c4 = st.columns([1.5, 1.2, 1.2, 1.5])
        ind_sel = c1.selectbox("Nhóm ngành", INDUSTRY_GROUPS, key="hist_ind")
        sym_list = get_symbols_by_industry(ind_sel, exclude_penny=False)
        sym_sel = c2.selectbox("Mã cổ phiếu", sym_list, index=sym_list.index("FPT") if "FPT" in sym_list else 0)
        h_start = c3.date_input("Từ ngày", value=TODAY_VN - timedelta(days=365), key="h_s")
        h_end = c4.date_input("Đến ngày", value=TODAY_VN, key="h_e")

        ma_sel = st.multiselect("Đường trung bình (MA)", [10, 20, 50, 100, 200], default=[10, 20, 50])
        show_ath = st.checkbox("Hiển thị Đỉnh lịch sử (ATH)", value=True)

        df_hist = fetch_ssi_ohlcv(sym_sel, h_start - timedelta(days=365), h_end, "D")
        if not df_hist.empty:
            for p in ma_sel:
                df_hist[f"MA{p}"] = df_hist["Close"].rolling(p).mean()
            plot_df = df_hist[df_hist.index.date >= h_start]

            fig_c = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.03)
            fig_c.add_trace(
                go.Candlestick(
                    x=plot_df.index, open=plot_df["Open"], high=plot_df["High"],
                    low=plot_df["Low"], close=plot_df["Close"], name=sym_sel,
                ),
                row=1, col=1,
            )
            for p in ma_sel:
                fig_c.add_trace(
                    go.Scatter(x=plot_df.index, y=plot_df[f"MA{p}"], name=f"MA{p}", line=dict(color=MA_COLORS.get(p, "#0284c7"), width=1.4)),
                    row=1, col=1,
                )
            if show_ath:
                ath_val = float(df_hist["High"].max())
                fig_c.add_hline(y=ath_val, line_dash="dash", line_color="#9333ea", annotation_text=f"ATH: {ath_val:,.2f}", row=1, col=1)

            vol_colors = ["#10b981" if c >= o else "#ef4444" for c, o in zip(plot_df["Close"], plot_df["Open"])]
            fig_c.add_trace(go.Bar(x=plot_df.index, y=plot_df["Volume"], marker_color=vol_colors, name="Volume"), row=2, col=1)
            fig_c.update_layout(height=620, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=25, b=10))
            st.plotly_chart(fig_c, width="stretch")

    with t_intra:
        c1, c2, c3 = st.columns([1.2, 1.2, 1.2])
        in_sym = c1.text_input("Nhập mã cổ phiếu", value="FPT").strip().upper()
        in_date = c2.date_input("Ngày khớp lệnh", value=TODAY_VN, key="in_date")
        in_tf = c3.selectbox("Khung nến", ["1", "5", "15", "60"], format_func=lambda x: f"{x} phút")

        if in_sym:
            ws_mgr.subscribe([in_sym])
            tick = ws_mgr.get_snapshot([in_sym]).get(in_sym)
            if tick:
                st.success(f"⚡ **SSI Realtime ({in_sym})**: Giá khớp `{tick['last']:,.2f}` | Thay đổi `{tick['delta']:+.2f} ({tick['pct']:+.2f}%)` | Cập nhật lúc `{tick['time']}`")

            df_in = fetch_ssi_ohlcv(in_sym, in_date, in_date, in_tf)
            if not df_in.empty:
                col_tbl, col_ch = st.columns([1.2, 2.8])
                with col_tbl:
                    st.dataframe(df_in.iloc[::-1], height=480, width="stretch")
                with col_ch:
                    fig_in = go.Figure(data=[go.Candlestick(
                        x=df_in.index, open=df_in["Open"], high=df_in["High"],
                        low=df_in["Low"], close=df_in["Close"], name=in_sym,
                    )])
                    fig_in.update_layout(height=480, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=20, b=10))
                    st.plotly_chart(fig_in, width="stretch")
            else:
                st.info("Chưa có dữ liệu khớp lệnh trong ngày đã chọn.")


# ==============================================================================
# WORKSPACE 5: DANH MỤC NẮM GIỮ & BACKTEST HYBRID
# ==============================================================================
elif workspace == "💼 Danh Mục & Backtest":
    t_port, t_bt = st.tabs(["📘 Danh Mục Nắm Giữ", "🧪 Backtest Chiến Lược Hybrid"])

    # --- SUB-TAB 5.1: DANH MỤC NẮM GIỮ ---
    with t_port:
        port_file = Path("portfolio.json")
        if "portfolio_data" not in st.session_state:
            if port_file.exists():
                st.session_state["portfolio_data"] = json.loads(port_file.read_text(encoding="utf-8"))
            else:
                st.session_state["portfolio_data"] = []

        with st.expander("➕ Thêm vị thế mới vào danh mục", expanded=False):
            ac1, ac2, ac3, ac4, ac5 = st.columns([1, 1.2, 1, 1, 1.5])
            new_sym = ac1.text_input("Mã CP", placeholder="VD: FPT").strip().upper()
            new_bdate = ac2.date_input("Ngày mua", value=TODAY_VN)
            new_bpx = ac3.number_input("Giá mua (nghìn)", 0.0, 1000.0, 0.0, step=0.1)
            new_qty = ac4.number_input("Khối lượng", 0, 10_000_000, 100, step=100)
            new_note = ac5.text_input("Ghi chú")
            if st.button("💾 Lưu vị thế"):
                if new_sym and new_qty > 0:
                    st.session_state["portfolio_data"].append({
                        "symbol": new_sym,
                        "buy_date": new_bdate.isoformat(),
                        "buy_price": new_bpx,
                        "qty": int(new_qty),
                        "note": new_note,
                    })
                    port_file.write_text(json.dumps(st.session_state["portfolio_data"], ensure_ascii=False, indent=2), encoding="utf-8")
                    st.rerun()

        cash_vnd = st.number_input("Tiền mặt khả dụng (VNĐ)", 0.0, 1e12, 0.0, step=10_000_000.0)
        holdings = st.session_state["portfolio_data"]

        if holdings:
            syms_p = list(set([h["symbol"] for h in holdings]))
            ws_mgr.subscribe(syms_p)
            live_p = ws_mgr.get_snapshot(syms_p)
            hist_p = fetch_batch_ohlcv_ssi(syms_p, TODAY_VN - timedelta(days=300), TODAY_VN, "D")

            rows_p = []
            tot_cost = tot_val = 0.0
            for h in holdings:
                sym = h["symbol"]
                bp = float(h["buy_price"])
                qty = int(h["qty"])
                df_h = hist_p.get(sym)

                last_px = bp
                ma20 = ma50 = None
                if df_h is not None and not df_h.empty:
                    last_px = float(df_h["Close"].iloc[-1])
                    ma20 = float(df_h["Close"].rolling(20).mean().iloc[-1])
                    ma50 = float(df_h["Close"].rolling(50).mean().iloc[-1])

                if sym in live_p and live_p[sym].get("last"):
                    last_px = float(live_p[sym]["last"])

                pl_vnd = (last_px - bp) * qty * 1000.0
                pl_pct = ((last_px / bp - 1.0) * 100.0) if bp > 0 else 0.0
                tot_cost += bp * qty * 1000.0
                tot_val += last_px * qty * 1000.0

                reco = "NẮM GIỮ"
                if pl_pct <= -7.0:
                    reco = "🛑 CẮT LỖ (Vi phạm -7%)"
                elif ma50 and last_px < ma50:
                    reco = "⚠️ GÃY MA50 - HẠ TỶ TRỌNG"
                elif pl_pct >= 25.0:
                    reco = "💰 CHỐT LỜI (>25%)"
                elif ma20 and last_px < ma20 and pl_pct > 0:
                    reco = "🔒 KHÓA LÃI (<MA20)"

                rows_p.append({
                    "Mã": sym, "Ngày mua": h["buy_date"], "Giá mua": bp, "KL": qty,
                    "Giá hiện tại": round(last_px, 2), "Lãi/Lỗ (VNĐ)": round(pl_vnd, 0),
                    "% Lãi/Lỗ": round(pl_pct, 2), "Khuyến nghị tự động": reco, "Ghi chú": h.get("note", ""),
                })

            nav_all = tot_val + cash_vnd
            tot_pl = tot_val - tot_cost
            k1, k2, k3 = st.columns(3)
            k1.metric("Tổng Lãi / Lỗ", f"{tot_pl:,.0f} VNĐ", f"{(tot_pl / tot_cost * 100) if tot_cost > 0 else 0:+.2f}%")
            k2.metric("Giá trị Cổ phiếu", f"{tot_val:,.0f} VNĐ")
            k3.metric("Tổng NAV (Gồm tiền mặt)", f"{nav_all:,.0f} VNĐ")

            st.dataframe(pd.DataFrame(rows_p), width="stretch", hide_index=True)
        else:
            st.info("Danh mục đang trống. Nhấn '➕ Thêm vị thế mới' ở trên để bắt đầu theo dõi.")

    # --- SUB-TAB 5.2: BACKTEST HYBRID ---
    with t_bt:
        col_cfg, col_res = st.columns([1.1, 2.9])
        with col_cfg:
            st.markdown("#### ⚙️ Tham Số Kiểm Thử")
            bt_ind = st.selectbox("Vũ trụ cổ phiếu", [g for g in INDUSTRY_GROUPS if g != "Chỉ số"], key="bt_ind")
            bt_cap = st.number_input("Vốn ban đầu (VNĐ)", 10_000_000.0, 1e12, 1_000_000_000.0, step=100_000_000.0)
            bt_start = st.date_input("Từ ngày", value=date(2024, 10, 17), key="bt_s")
            bt_end = st.date_input("Đến ngày", value=TODAY_VN, key="bt_e")

            c_a, c_b = st.columns(2)
            bt_max_pos = c_a.number_input("Số mã max", 1, 20, 5)
            bt_max_sec = c_b.number_input("Max/Ngành", 1, 10, 2)
            bt_sl = c_a.number_input("Cắt lỗ (%)", 1.0, 30.0, 7.0, step=0.5)
            bt_ma_exit = c_b.number_input("MA chặn", 5, 200, 20)
            bt_fee = c_a.number_input("Phí+Thuế (%)", 0.0, 5.0, 0.15, step=0.05)
            bt_tplus = c_b.number_input("Chu kỳ T+", 0.0, 5.0, 2.5, step=0.5)

            bt_mode = st.selectbox(
                "Chế độ điểm mua",
                [0, 1, 2],
                index=1,
                format_func=lambda x: ["1. Chuẩn VCP Pivot (2T-4T)", "2. VCP hoặc Breakout 20P", "3. Mọi mã Stage 2 + Nổ Vol"][x],
            )
            bt_rs = st.number_input("RS Min", 50, 99, 70, key="bt_rs")
            bt_vol_mult = st.number_input("Hệ số Vol", 0.5, 5.0, 1.2, step=0.1)
            bt_min_vol = st.number_input("Min Volume", 0, 10_000_000, 1_000_000, step=100_000)

            bt_pp = st.checkbox("Power Play (Giữ MA50 khi lãi ≥ 20%)", value=True)
            bt_dd_shield = st.checkbox("Lá chắn Ngày Phân Phối", value=True)
            bt_climax = st.checkbox("Bán Đỉnh Hưng Phấn (>80% MA200)", value=True)
            bt_bot_fish = st.checkbox("Bắt Đáy Hoảng Loạn (Downtrend)", value=True)

            run_bt_btn = st.button("🚀 CHẠY BACKTEST HYBRID", type="primary", width="stretch")

        with col_res:
            if run_bt_btn:
                target_syms = get_symbols_by_industry(bt_ind, exclude_penny=(bt_ind == "Tất cả ngành"))
                all_hose = get_symbols_by_industry("Tất cả ngành", exclude_penny=True)
                fetch_syms = sorted(list(set(all_hose + target_syms + ["VNINDEX"])))

                prog = st.progress(0, text="Đang tải dữ liệu lịch sử toàn sàn từ SSI...")
                raw_bt = fetch_batch_ohlcv_ssi(
                    fetch_syms, bt_start - timedelta(days=450), bt_end, "D",
                    progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
                )
                prog.empty()

                params = {
                    "symbols": target_syms, "initial_capital": bt_cap,
                    "fee_rate": bt_fee / 100.0, "t_plus": bt_tplus,
                    "max_positions": int(bt_max_pos), "max_per_sector": int(bt_max_sec),
                    "stop_loss": bt_sl / 100.0, "ma_exit": int(bt_ma_exit),
                    "start_date": bt_start, "end_date": bt_end,
                    "entry_mode": int(bt_mode), "min_rs": int(bt_rs),
                    "max_pivot_pct": 5.0, "vol_mult": float(bt_vol_mult),
                    "min_vol": int(bt_min_vol), "use_take_profit": False,
                    "take_profit": 0.25, "use_power_play": bt_pp,
                    "use_dd_shield": bt_dd_shield, "w_dd": 1.0, "w_stall": 0.7,
                    "dd_cancel_pct": 5.0, "t_low": 3, "t_med": 5, "t_high": 7, "t_crit": 9,
                    "use_top_climax": bt_climax, "climax_breadth_thresh": 80.0,
                    "use_bottom_fishing": bt_bot_fish, "panic_ma200_thresh": 20.0, "panic_bot52_thresh": 70.0,
                }
                st.session_state["bt_result"] = run_hybrid_backtest(raw_bt, params)

            if "bt_result" in st.session_state and st.session_state["bt_result"]:
                res = st.session_state["bt_result"]
                s = res["stats"]
                eq = res["equity"]

                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Lãi / Lỗ Ròng", f"{s['Profit']:,.0f} đ", f"{s['Profit %']:+.2f}%")
                m2.metric("CAGR / Năm", f"{s['CAGR']:+.2f}%")
                m3.metric("Tỷ Lệ Thắng", f"{s['Win Rate']:.1f}%", f"{s['Total Trades']} lệnh")
                m4.metric("Tài Sản Cuối", f"{s['Final']:,.0f} đ")
                m5.metric("Max Drawdown", f"{s['Max DD']:.2f}%")

                fig_eq = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
                fig_eq.add_trace(go.Scatter(x=eq.index, y=eq["NAV"], name="Tổng NAV", line=dict(color="#0284c7", width=2)), row=1, col=1)
                fig_eq.add_trace(go.Scatter(x=eq.index, y=eq["Exposure"], name="% Tỷ trọng CP", fill="tozeroy", line=dict(color="#10b981", width=1)), row=2, col=1)
                fig_eq.add_trace(go.Scatter(x=eq.index, y=eq["Breadth200"], name="% Mã > MA200", line=dict(color="#f59e0b", dash="dash")), row=2, col=1)
                fig_eq.update_layout(height=460, margin=dict(l=10, r=10, t=25, b=10))
                st.plotly_chart(fig_eq, width="stretch")

                sub_t1, sub_t2 = st.tabs(["📝 Sổ Lệnh Chi Tiết", "✅ Deal Đã Đóng"])
                with sub_t1:
                    st.dataframe(res["trades"].iloc[::-1] if not res["trades"].empty else pd.DataFrame(), width="stretch", hide_index=True)
                with sub_t2:
                    st.dataframe(res["closed"].iloc[::-1] if not res["closed"].empty else pd.DataFrame(), width="stretch", hide_index=True)

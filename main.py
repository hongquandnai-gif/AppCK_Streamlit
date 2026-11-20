# ========================= main.py =========================
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components

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
    clear_batch_cache,
    fetch_batch_ohlcv_ssi,
    fetch_ssi_ohlcv_cached,
    fetch_ssi_stock_list,
    get_ssi_ws_manager,
    vn_now,
    vn_today,
)

# ==============================================================================
# 1. CẤU HÌNH TRANG & CSS MODERN DASHBOARD V11 PRO (CHỐNG GIẬT MỜ LIVE)
# ==============================================================================
st.set_page_config(
    page_title="V11 PRO - Phân Tích Cổ Phiếu & SSI WebSocket",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    /* Tắt hoàn toàn hiệu ứng giật mờ (dimming) khi fragment cập nhật Live */
    [data-stale="true"],
    div[data-stale="true"],
    div[data-testid="element-container"][data-stale="true"],
    div[data-testid="stVerticalBlock"][data-stale="true"] {
        opacity: 1 !important;
        filter: none !important;
        transition: none !important;
    }
    div[data-testid="stStatusWidget"] {
        visibility: hidden !important;
    }

    .stApp {
        background-color: #f1f5f9;
    }
    .block-container {
        padding-top: 3.1rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 98.5% !important;
    }

    /* Thanh Header V11 Pro */
    .v11-header {
        background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
        padding: 12px 20px;
        border-radius: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.15);
    }
    .v11-title {
        color: #38bdf8;
        font-size: 18px;
        font-weight: 800;
        letter-spacing: 0.4px;
        margin: 0;
    }
    .v11-subtitle {
        color: #94a3b8;
        font-size: 12px;
        font-weight: 500;
        margin-left: 10px;
    }
    .ws-badge-on {
        background-color: rgba(16, 185, 129, 0.16);
        color: #34d399;
        padding: 5px 14px;
        border-radius: 999px;
        font-weight: 700;
        font-size: 12.5px;
        border: 1px solid rgba(16, 185, 129, 0.45);
    }
    .ws-badge-off {
        background-color: rgba(239, 68, 68, 0.16);
        color: #fca5a5;
        padding: 5px 14px;
        border-radius: 999px;
        font-weight: 700;
        font-size: 12.5px;
        border: 1px solid rgba(239, 68, 68, 0.45);
    }

    /* Nút bấm phẳng */
    button[kind="primary"] {
        background-color: #0284c7 !important;
        border-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(2, 132, 199, 0.25);
    }
    button[kind="primary"]:hover {
        background-color: #0369a1 !important;
        border-color: #0369a1 !important;
    }
    button[kind="secondary"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #334155 !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }
    button[kind="secondary"]:hover {
        background-color: #e2e8f0 !important;
        border-color: #94a3b8 !important;
        color: #0f172a !important;
    }

    /* Thẻ KPI Cards */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #0284c7;
        padding: 10px 14px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 12px !important;
        font-weight: 700 !important;
        color: #64748b !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 20px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
    }

    /* Sub-tabs */
    div[data-testid="stTabs"] button[data-baseweb="tab"] {
        font-weight: 700 !important;
        font-size: 14px !important;
        padding: 8px 18px !important;
        border-radius: 8px 8px 0 0 !important;
    }

    /* Bảng dữ liệu */
    div[data-testid="stDataFrame"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 4px;
    }

    /* Chú thích 7 màu Treemap */
    .tm-legend-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        align-items: center;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 8px 12px;
        margin: 6px 0 10px 0;
        font-size: 12px;
        font-weight: 700;
    }
    .tm-chip {
        border-radius: 5px;
        padding: 3px 10px;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 2. HELPER BIỂU ĐỒ, LỌC NGÀY/GIỜ NGHỈ, LIVE CANDLE, DYNAMIC OHLC & MÀU SẮC
# ==============================================================================
ALL_MAIN_INDICES = ["VNINDEX", "VN30", "HNX", "UPCOM", "VNMID", "VNSMALL"]


def _auto_df_height(df: pd.DataFrame, row_px: int = 35, header_px: int = 38) -> int:
    """Tự động giãn chiều cao bảng theo đúng số dòng để cuộn mượt toàn trang."""
    if df is None or df.empty:
        return 120
    return int(len(df) * row_px + header_px + 4)


def get_vn_treemap_color(pct: float) -> str:
    if pct >= 6.5:
        return "#9333ea"   # Tím trần
    if pct >= 2.0:
        return "#059669"   # Xanh lá đậm
    if pct > 0.0:
        return "#10b981"   # Xanh lá tươi
    if pct == 0.0:
        return "#d97706"   # Vàng tham chiếu
    if pct <= -6.5:
        return "#0284c7"   # Xanh lơ sàn
    if pct <= -2.0:
        return "#dc2626"   # Đỏ đậm
    return "#ef4444"       # Đỏ nhạt


def build_vn_treemap(df_tm: pd.DataFrame) -> go.Figure:
    ids, labels, parents, values, colors, texts, hovers = [], [], [], [], [], [], []

    total_gtgd = float(df_tm["GTGD (Tỷ)"].sum())
    mkt_avg_pct = (
        float((df_tm["% Thay đổi"] * df_tm["GTGD (Tỷ)"]).sum() / total_gtgd)
        if total_gtgd > 0 else 0.0
    )

    ids.append("HOSE")
    labels.append("HOSE")
    parents.append("")
    values.append(0.0)
    colors.append("#0f172a")
    texts.append(f"<b>HOSE ({mkt_avg_pct:+.2f}%) • Tổng GTGD: {total_gtgd:,.0f} Tỷ</b>")
    hovers.append(
        f"<b>Toàn sàn HOSE</b><br>"
        f"Biến động BQ gia quyền: <b>{mkt_avg_pct:+.2f}%</b><br>"
        f"Tổng GTGD: <b>{total_gtgd:,.1f} Tỷ VNĐ</b><br>"
        f"Số mã khớp lệnh: {len(df_tm)}"
    )

    for ind, gdf in df_tm.groupby("Ngành"):
        sec_gtgd = float(gdf["GTGD (Tỷ)"].sum())
        if sec_gtgd <= 0:
            continue
        sec_pct = float((gdf["% Thay đổi"] * gdf["GTGD (Tỷ)"]).sum() / sec_gtgd)
        sec_id = f"SEC_{ind}"

        ids.append(sec_id)
        labels.append(str(ind))
        parents.append("HOSE")
        values.append(0.0)
        colors.append("#1e293b")
        texts.append(f"<b>{ind}</b> ({sec_pct:+.2f}%)")
        hovers.append(
            f"<b>Ngành {ind}</b><br>"
            f"Biến động BQ: <b>{sec_pct:+.2f}%</b><br>"
            f"Tổng GTGD: <b>{sec_gtgd:,.1f} Tỷ VNĐ</b><br>"
            f"Số mã: {len(gdf)}"
        )

        for row in gdf.to_dict("records"):
            sym = str(row["Mã"])
            pct = float(row["% Thay đổi"])
            gtgd = float(row["GTGD (Tỷ)"])
            px_val = float(row["Giá"])

            ids.append(f"{sec_id}_{sym}")
            labels.append(sym)
            parents.append(sec_id)
            values.append(gtgd)
            colors.append(get_vn_treemap_color(pct))
            texts.append(f"<b>{sym}</b><br>{pct:+.2f}%")
            hovers.append(
                f"<b>{sym}</b> ({ind})<br>"
                f"Giá đóng cửa: <b>{px_val:,.2f}</b><br>"
                f"Thay đổi: <b>{pct:+.2f}%</b><br>"
                f"GTGD: <b>{gtgd:,.2f} Tỷ VNĐ</b>"
            )

    fig = go.Figure(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            text=texts,
            textinfo="text",
            textposition="middle center",
            hovertext=hovers,
            hoverinfo="text",
            marker=dict(
                colors=colors,
                line=dict(width=1.2, color="#ffffff"),
                cornerradius=4,
            ),
            textfont=dict(color="#ffffff", size=13, family="Segoe UI, Arial, sans-serif"),
            pathbar=dict(visible=False),
            tiling=dict(packing="squarify", pad=3),
        )
    )
    fig.update_layout(
        height=700,
        margin=dict(l=4, r=4, t=6, b=4),
        paper_bgcolor="#ffffff",
        uirevision="treemap_keep",
    )
    return fig


def _filter_vn_trading_hours(df: pd.DataFrame) -> pd.DataFrame:
    """Loại bỏ các khung giờ ngoài phiên giao dịch VN (nghỉ trưa 11:31-12:59, trước 09:00, sau 15:05)."""
    if df.empty:
        return df
    hhmm = df.index.hour * 100 + df.index.minute
    mask = ((hhmm >= 900) & (hhmm <= 1130)) | ((hhmm >= 1300) & (hhmm <= 1505))
    filtered = df[mask]
    return filtered if not filtered.empty else df


def _trading_x_labels(index: pd.DatetimeIndex, is_intraday: bool = False) -> list[str]:
    """Chuyển trục thời gian thành nhãn rời rạc để Plotly loại bỏ hoàn toàn ngày nghỉ lễ, T7/CN và giờ nghỉ trưa."""
    if is_intraday:
        fmt = "%H:%M" if len(set(index.date)) <= 1 else "%d/%m %H:%M"
    else:
        fmt = "%d/%m/%y"
    return index.strftime(fmt).tolist()


def _patch_live_candle(df: pd.DataFrame, tick: Optional[dict], is_intraday: bool = False) -> pd.DataFrame:
    """Cập nhật nến cuối cùng bằng giá khớp lệnh Realtime từ SSI WebSocket."""
    if df.empty or not tick or not tick.get("last"):
        return df
    out = df.copy()
    live_px = float(tick["last"])
    last_idx = out.index[-1]
    out.loc[last_idx, "Close"] = live_px
    out.loc[last_idx, "High"] = max(float(out.loc[last_idx, "High"]), live_px)
    out.loc[last_idx, "Low"] = min(float(out.loc[last_idx, "Low"]), live_px)
    if not is_intraday and tick.get("volume"):
        out.loc[last_idx, "Volume"] = max(float(out.loc[last_idx, "Volume"]), float(tick["volume"]))
    return out


def _merge_live_intraday_series(df_hist_1m: pd.DataFrame, ws_bars_df: pd.DataFrame, target_date: date) -> pd.DataFrame:
    """Nối liền mạch chuỗi nến 1 phút từ WebSocket vào cuối dữ liệu REST API trong phiên hôm nay."""
    if target_date != vn_today() or ws_bars_df.empty:
        return df_hist_1m
    ws_today = ws_bars_df[ws_bars_df.index.date == target_date]
    if ws_today.empty:
        return df_hist_1m
    if df_hist_1m.empty:
        return ws_today.copy()

    combined = df_hist_1m.copy()
    for ts, row in ws_today.iterrows():
        if ts in combined.index:
            combined.loc[ts, "High"] = max(float(combined.loc[ts, "High"]), float(row["High"]))
            combined.loc[ts, "Low"] = min(float(combined.loc[ts, "Low"]), float(row["Low"]))
            combined.loc[ts, "Close"] = float(row["Close"])
            if float(row["Volume"]) > 0:
                combined.loc[ts, "Volume"] = float(row["Volume"])
        elif ts > combined.index[-1]:
            combined.loc[ts] = row
    return combined.sort_index()


def _add_candlestick_clean(
    fig: go.Figure,
    x_lbls: list[str],
    df: pd.DataFrame,
    sym: str,
    row: Optional[int] = None,
    col: Optional[int] = None,
):
    """Vẽ nến + lớp bắt sự kiện hover ẩn (không hiện popup che nến, chỉ cập nhật thanh OHLC)."""
    kw = {"row": row, "col": col} if (row is not None and col is not None) else {}
    fig.add_trace(
        go.Candlestick(
            x=x_lbls, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name=sym,
            increasing_line_color="#10b981", decreasing_line_color="#ef4444",
            hoverinfo="skip",
        ),
        **kw,
    )
    fig.add_trace(
        go.Scatter(
            x=x_lbls, y=df["Close"], mode="markers",
            marker=dict(opacity=0, size=1),
            hovertemplate="<extra></extra>",
            showlegend=False,
        ),
        **kw,
    )


def _render_dynamic_ohlc_chart(
    fig: go.Figure,
    df: pd.DataFrame,
    sym: str,
    prev_close_series: Optional[pd.Series] = None,
    ma_info: Optional[list[tuple[str, str]]] = None,
    is_intraday: bool = False,
    height: int = 600,
    chart_id: str = "ohlc_chart",
):
    """
    Render biểu đồ Plotly kèm thanh OHLC + % tăng giảm + MA tự động thay đổi
    tức thì theo chuyển động con trỏ chuột (plotly_hover / plotly_unhover).
    """
    prev_s = prev_close_series if prev_close_series is not None else df["Close"].shift(1)
    dt_fmt = "%d/%m/%Y %H:%M" if is_intraday else "%d/%m/%Y"
    ma_info = ma_info or []

    records = []
    for i, (ts, row) in enumerate(df.iterrows()):
        o, h, l, c, v = (
            float(row["Open"]), float(row["High"]),
            float(row["Low"]), float(row["Close"]), float(row["Volume"]),
        )
        prev_c = prev_s.iloc[i]
        if pd.notna(prev_c) and float(prev_c) > 0:
            delta = c - float(prev_c)
            pct = (delta / float(prev_c)) * 100.0
            clr = "#059669" if delta > 0 else ("#dc2626" if delta < 0 else "#d97706")
            chg = f"{delta:+.2f} ({pct:+.2f}%)"
        else:
            clr = "#475569"
            chg = "—"

        ma_vals = []
        for col_name, col_hex in ma_info:
            if col_name in df.columns and pd.notna(row.get(col_name)):
                val_str = f"{float(row[col_name]):,.0f}" if "Vol" in col_name else f"{float(row[col_name]):,.2f}"
                ma_vals.append({"name": col_name.replace("_", " "), "val": val_str, "color": col_hex})

        records.append({
            "dt": ts.strftime(dt_fmt),
            "o": f"{o:,.2f}", "h": f"{h:,.2f}", "l": f"{l:,.2f}", "c": f"{c:,.2f}",
            "v": f"{v:,.0f}", "chg": chg, "clr": clr, "mas": ma_vals,
        })

    fig.update_layout(
        hovermode="x",
        hoverlabel=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)", font=dict(size=1, color="rgba(0,0,0,0)")),
    )
    fig.update_xaxes(showspikes=True, spikemode="across", spikesnap="cursor", spikethickness=1, spikecolor="#94a3b8", spikedash="dot")
    fig.update_yaxes(showspikes=True, spikemode="across", spikesnap="cursor", spikethickness=1, spikecolor="#94a3b8", spikedash="dot")

    fig_json = fig.to_json()
    rec_json = json.dumps(records, ensure_ascii=False)
    safe_sym = json.dumps(sym, ensure_ascii=False)
    dom_id = f"plt_{chart_id}"
    bar_id = f"bar_{chart_id}"

    html_code = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:8px 10px 4px 10px;">
        <div id="{bar_id}" style="border-left:4px solid #0284c7; padding:4px 12px; margin-bottom:4px; font-size:13px; color:#1e293b; line-height:1.55;"></div>
        <div id="{dom_id}" style="width:100%; height:{height}px;"></div>
    </div>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <script>
        (function() {{
            const figData = {fig_json};
            const bars = {rec_json};
            const sym = {safe_sym};
            const barEl = document.getElementById("{bar_id}");
            const pltEl = document.getElementById("{dom_id}");

            function renderBar(idx) {{
                if (!bars.length) return;
                const b = bars[Math.max(0, Math.min(idx, bars.length - 1))];
                barEl.style.borderLeftColor = b.clr;
                let maHtml = "";
                if (b.mas && b.mas.length) {{
                    maHtml = "<div style='font-size:12px; margin-top:2px;'>" +
                        b.mas.map(m => `<span style="color:${{m.color}}; font-weight:700; margin-right:12px;">${{m.name}}: ${{m.val}}</span>`).join("") +
                        "</div>";
                }}
                barEl.innerHTML =
                    `<div>` +
                    `<b>${{sym}}</b> <span style="color:#64748b;">(${{b.dt}})</span> &nbsp;|&nbsp; ` +
                    `O: <b style="color:${{b.clr}}">${{b.o}}</b> &nbsp; ` +
                    `H: <b style="color:${{b.clr}}">${{b.h}}</b> &nbsp; ` +
                    `L: <b style="color:${{b.clr}}">${{b.l}}</b> &nbsp; ` +
                    `C: <b style="color:${{b.clr}}">${{b.c}}</b> &nbsp;|&nbsp; ` +
                    `<b style="color:${{b.clr}}">${{b.chg}}</b> &nbsp;|&nbsp; ` +
                    `Vol: <b>${{b.v}}</b>` +
                    `</div>` + maHtml;
            }}

            renderBar(bars.length - 1);

            Plotly.newPlot(pltEl, figData.data, figData.layout, {{
                responsive: true,
                displaylogo: false,
                modeBarButtonsToRemove: ['lasso2d', 'select2d']
            }}).then(function(gd) {{
                gd.on('plotly_hover', function(ev) {{
                    if (ev && ev.points && ev.points.length > 0) {{
                        const idx = ev.points[0].pointIndex;
                        if (typeof idx === 'number') renderBar(idx);
                    }}
                }});
                gd.on('plotly_unhover', function() {{
                    renderBar(bars.length - 1);
                }});
            }});
        }})();
    </script>
    """
    components.html(html_code, height=height + 76, scrolling=False)


def _style_chart(fig: go.Figure, height: int = 500, categorical_x: bool = False) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        height=height,
        hovermode="x unified",
        uirevision="v11_keep_view",
        margin=dict(l=12, r=12, t=34, b=12),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(family="Segoe UI, Arial, sans-serif", size=12, color="#1e293b"),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    )
    if categorical_x:
        fig.update_xaxes(type="category", nticks=12, tickangle=0, showgrid=True, gridcolor="#f1f5f9", zeroline=False)
    else:
        fig.update_xaxes(showgrid=True, gridcolor="#f1f5f9", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e2e8f0", zeroline=False)
    return fig


def _color_status(val):
    s = str(val).upper()
    if any(k in s for k in ["DẪN DẮT", "TRÊN", "ĐẠT (FULL)", "BUY", "CHUẨN", "CHỐT LỜI", "MUA THÊM", "GIAI ĐOẠN 2", "POWER PLAY"]):
        return "color: #059669; font-weight: 700;"
    if any(k in s for k in ["YẾU", "DƯỚI", "SELL", "CẮT LỖ", "QUÁ", "GÃY", "GIAI ĐOẠN 4", "CẢNH BÁO"]):
        return "color: #dc2626; font-weight: 700;"
    if any(k in s for k in ["TRUNG LẬP", "CHẠM", "CHỜ", "NỔ VOL", "KHÓA LÃI", "GIAI ĐOẠN 3", "QUAN SÁT"]):
        return "color: #d97706; font-weight: 700;"
    return ""


def _color_signed(val):
    try:
        v = float(val)
        if v > 0:
            return "color: #059669; font-weight: 700;"
        if v < 0:
            return "color: #dc2626; font-weight: 700;"
        return "color: #d97706; font-weight: 600;"
    except Exception:
        return ""


def _color_pct_strength(val):
    try:
        v = float(val)
        if v >= 50:
            return "color: #059669; font-weight: 700;"
        if v <= 30:
            return "color: #dc2626; font-weight: 700;"
        return "color: #d97706; font-weight: 600;"
    except Exception:
        return ""


def _color_pct_weak(val):
    try:
        return "color: #dc2626; font-weight: 700;" if float(val) >= 50 else ""
    except Exception:
        return ""


def _color_rs(val):
    try:
        v = float(val)
        if v >= 90:
            return "color: #7c3aed; font-weight: 700;"
        if v >= 80:
            return "color: #059669; font-weight: 700;"
        return "color: #d97706; font-weight: 700;"
    except Exception:
        return ""


def _color_purple(_val):
    return "color: #9333ea; font-weight: 700;"


def _color_vol_score(val):
    try:
        return "color: #059669; font-weight: 700;" if float(val) >= 1.5 else ""
    except Exception:
        return ""


# ==============================================================================
# 3. KHỞI TẠO SSI WEBSOCKET, HEADER & THANH 5 WORKSPACE PHẲNG
# ==============================================================================
ws_mgr = get_ssi_ws_manager()
ssi_stocks_meta = fetch_ssi_stock_list("hose")
TODAY_VN = vn_today()
vn_clock = vn_now().strftime("%d/%m/%Y %H:%M")

badge_html = (
    f'<span class="ws-badge-on">🟢 SSI WebSocket Live ({len(ssi_stocks_meta)} mã HOSE) • {vn_clock}</span>'
    if ws_mgr.is_connected else
    f'<span class="ws-badge-off">🟡 SSI WebSocket Đang kết nối • {vn_clock}</span>'
)

st.markdown(f"""
<div class="v11-header">
    <div>
        <span class="v11-title">📊 V11 PRO</span>
        <span class="v11-subtitle">Hệ Thống Phân Tích Định Lượng Minervini & SSI Realtime</span>
    </div>
    <div>{badge_html}</div>
</div>
""", unsafe_allow_html=True)

WORKSPACES = [
    "🌐 Toàn Cảnh Thị Trường",
    "🧭 Sóng Ngành & Dòng Tiền",
    "🎯 Lọc Cổ Phiếu Đột Phá",
    "📈 Phân Tích Biểu Đồ",
    "💼 Danh Mục & Backtest",
]

if "active_ws" not in st.session_state:
    st.session_state["active_ws"] = WORKSPACES[0]

nav_cols = st.columns([1, 1, 1, 1, 1, 0.95], gap="small", vertical_alignment="center")
for idx, ws_name in enumerate(WORKSPACES):
    is_active = st.session_state["active_ws"] == ws_name
    if nav_cols[idx].button(
        ws_name,
        key=f"nav_btn_{idx}",
        type="primary" if is_active else "secondary",
        width="stretch",
    ):
        st.session_state["active_ws"] = ws_name
        st.rerun()

with nav_cols[5]:
    LIVE_AUTO = st.toggle("⚡ Live WS (5s)", value=True, key="global_live_toggle")

workspace = st.session_state["active_ws"]


# ==============================================================================
# WORKSPACE 1: TOÀN CẢNH THỊ TRƯỜNG
# ==============================================================================
if workspace == "🌐 Toàn Cảnh Thị Trường":
    t1, t2, t3 = st.tabs([
        "⏱️ Chỉ Số Trực Tiếp (SSI Realtime)",
        "🗺️ Bản Đồ Nhiệt (Treemap)",
        "🩺 Sức Khỏe & Ngày Phân Phối",
    ])

    # --- SUB-TAB 1.1: CHỈ SỐ TRỰC TIẾP (ĐỌC TỪ RAM NỀN - KHÔNG GIẬT MỜ) ---
    with t1:
        c1, c2, c3 = st.columns([1.1, 3.6, 1.2], vertical_alignment="bottom")
        idx_date = c1.date_input("Ngày giao dịch", value=TODAY_VN, key="idx_live_date")
        selected_indices = c2.multiselect(
            "Chọn chỉ số hiển thị",
            ALL_MAIN_INDICES,
            default=ALL_MAIN_INDICES,
        )
        if c3.button("🔄 Làm mới ngay", type="primary", width="stretch"):
            ws_mgr.subscribe(selected_indices)
            ws_mgr.refresh_indices_now(selected_indices)
            st.cache_data.clear()

        def _render_indices_live_body():
            if not selected_indices:
                st.info("Vui lòng chọn ít nhất một chỉ số.")
                return

            ws_mgr.subscribe(selected_indices)
            if idx_date == TODAY_VN:
                ws_mgr.ensure_indices_loaded(selected_indices)
            live_ticks = ws_mgr.get_snapshot(selected_indices)

            n_sel = len(selected_indices)
            cols_kpi = st.columns(min(n_sel, 6))
            n_cols = 1 if n_sel == 1 else 2
            n_rows = int(np.ceil(n_sel / n_cols))

            fig_idx = make_subplots(
                rows=n_rows, cols=n_cols,
                subplot_titles=selected_indices,
                vertical_spacing=0.11, horizontal_spacing=0.06,
            )

            for i, sym in enumerate(selected_indices):
                if idx_date == TODAY_VN:
                    df_1m, df_d = ws_mgr.get_index_data(sym)
                else:
                    df_1m = fetch_ssi_ohlcv_cached(sym, idx_date - timedelta(days=6), idx_date, "1")
                    df_d = fetch_ssi_ohlcv_cached(sym, idx_date - timedelta(days=25), idx_date, "D")

                last_px = delta = pct = vol = 0.0
                trade_date_str = idx_date.strftime("%d/%m")
                prev_close = None
                plot_series = pd.DataFrame()
                is_intraday_mode = True

                if not df_1m.empty:
                    df_1m = df_1m[df_1m.index.date <= idx_date]
                    if not df_1m.empty:
                        actual_trade_date = df_1m.index[-1].date()
                        trade_date_str = actual_trade_date.strftime("%d/%m")
                        day_1m = df_1m[df_1m.index.date == actual_trade_date]
                        if actual_trade_date == TODAY_VN:
                            day_1m = _merge_live_intraday_series(day_1m, ws_mgr.get_minute_bars_df(sym), TODAY_VN)
                        plot_series = _filter_vn_trading_hours(day_1m)
                        if not df_d.empty:
                            df_prev = df_d[df_d.index.date < actual_trade_date]
                            if not df_prev.empty:
                                prev_close = float(df_prev["Close"].iloc[-1])

                if plot_series.empty and not df_d.empty:
                    df_d_cut = df_d[df_d.index.date <= idx_date]
                    if not df_d_cut.empty:
                        is_intraday_mode = False
                        plot_series = df_d_cut.tail(30)
                        trade_date_str = df_d_cut.index[-1].strftime("%d/%m")
                        if len(df_d_cut) >= 2:
                            prev_close = float(df_d_cut["Close"].iloc[-2])

                if not plot_series.empty:
                    if idx_date == TODAY_VN and sym in live_ticks:
                        plot_series = _patch_live_candle(plot_series, live_ticks[sym], is_intraday=is_intraday_mode)
                    last_px = float(plot_series["Close"].iloc[-1])
                    vol = float(plot_series["Volume"].sum()) if is_intraday_mode else float(plot_series["Volume"].iloc[-1])
                    if idx_date == TODAY_VN and sym in live_ticks and live_ticks[sym].get("volume"):
                        vol = float(live_ticks[sym]["volume"])
                    if prev_close and prev_close > 0:
                        delta = last_px - prev_close
                        pct = (delta / prev_close) * 100.0

                    r_idx = (i // n_cols) + 1
                    c_idx = (i % n_cols) + 1
                    line_col = "#10b981" if delta > 0 else ("#ef4444" if delta < 0 else "#d97706")
                    x_lbls = _trading_x_labels(plot_series.index, is_intraday=is_intraday_mode)

                    idx_hovers = []
                    for ts, r_px in zip(plot_series.index, plot_series["Close"]):
                        t_fmt = ts.strftime("%d/%m %H:%M" if is_intraday_mode else "%d/%m/%Y")
                        if prev_close and prev_close > 0:
                            d_pt = float(r_px) - prev_close
                            p_pt = d_pt / prev_close * 100.0
                            idx_hovers.append(f"<b>{sym}</b> • {t_fmt}<br>Điểm: <b>{float(r_px):,.2f}</b> ({d_pt:+.2f} | {p_pt:+.2f}%)")
                        else:
                            idx_hovers.append(f"<b>{sym}</b> • {t_fmt}<br>Điểm: <b>{float(r_px):,.2f}</b>")

                    fig_idx.add_trace(
                        go.Scatter(
                            x=x_lbls, y=plot_series["Close"],
                            mode="lines", name=sym, line=dict(color=line_col, width=2),
                            text=idx_hovers, hovertemplate="%{text}<extra></extra>",
                        ),
                        row=r_idx, col=c_idx,
                    )
                    if prev_close:
                        fig_idx.add_hline(
                            y=prev_close, line_dash="dash", line_color="#64748b",
                            line_width=1.1, row=r_idx, col=c_idx,
                        )

                with cols_kpi[i % len(cols_kpi)]:
                    st.metric(
                        label=f"{sym} ({trade_date_str})",
                        value=f"{last_px:,.2f}",
                        delta=f"{delta:+.2f} ({pct:+.2f}%)",
                    )

            _style_chart(fig_idx, height=max(420, n_rows * 240), categorical_x=True)
            fig_idx.update_layout(showlegend=False)
            st.plotly_chart(fig_idx, width="stretch", key="indices_live_chart")

        @st.fragment(run_every=5)
        def _indices_live_fragment():
            _render_indices_live_body()

        if LIVE_AUTO and idx_date == TODAY_VN:
            _indices_live_fragment()
        else:
            _render_indices_live_body()

    # --- SUB-TAB 1.2: BẢN ĐỒ NHIỆT TREEMAP (ĐỒNG BỘ REALTIME LIÊN TỤC 5S) ---
    with t2:
        c1, c2, c3, _ = st.columns([1.2, 1.4, 1.3, 2.1], vertical_alignment="bottom")
        tm_date = c1.date_input("Ngày bản đồ nhiệt", value=TODAY_VN, key="tm_date")
        tm_size_mode = c2.selectbox("Kích thước ô theo", ["Giá trị GD (Tỷ)", "Khối lượng GD"])
        run_tm = c3.button("🔄 Nạp lại dữ liệu", type="primary", width="stretch")

        st.markdown("""
        <div class="tm-legend-bar">
            <span style="color:#334155; margin-right:4px;">Chú thích màu:</span>
            <span class="tm-chip" style="background:#0284c7;">≤ −6.5% (Sàn)</span>
            <span class="tm-chip" style="background:#dc2626;">−6.5% ~ −2%</span>
            <span class="tm-chip" style="background:#ef4444;">−2% ~ 0%</span>
            <span class="tm-chip" style="background:#d97706;">0% (TC)</span>
            <span class="tm-chip" style="background:#10b981;">0% ~ +2%</span>
            <span class="tm-chip" style="background:#059669;">+2% ~ +6.5%</span>
            <span class="tm-chip" style="background:#9333ea;">≥ +6.5% (Trần)</span>
        </div>
        """, unsafe_allow_html=True)

        if tm_date != TODAY_VN:
            if run_tm or st.session_state.get("tm_hist_date") != tm_date:
                all_syms = [s for s, ind in HARDCODED_HOSE_INDUSTRIES_MAPPING.items() if ind != "Chỉ số"]
                prog = st.progress(0, text="Đang tải dữ liệu lịch sử toàn sàn từ SSI...")
                raw_map = fetch_batch_ohlcv_ssi(
                    all_syms, tm_date - timedelta(days=10), tm_date, "D",
                    _progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
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
                                "GTGD (Tỷ)": round(c_now * vol / 1e6, 2) if tm_size_mode == "Giá trị GD (Tỷ)" else round(vol, 0),
                                "% Thay đổi": round(pct, 2), "Giá": round(c_now, 2),
                            })
                st.session_state["tm_hist_df"] = pd.DataFrame(rows_tm)
                st.session_state["tm_hist_date"] = tm_date

            if "tm_hist_df" in st.session_state and not st.session_state["tm_hist_df"].empty:
                st.plotly_chart(build_vn_treemap(st.session_state["tm_hist_df"]), width="stretch", key="tm_hist_chart")
            else:
                st.warning("Không có dữ liệu giao dịch trong ngày đã chọn.")
        else:
            if run_tm:
                ws_mgr.refresh_board_now()

            def _render_live_treemap():
                live_board = ws_mgr.get_live_board()
                if not live_board:
                    live_board = ws_mgr.refresh_board_now()

                rows_live = []
                cnt_up = cnt_down = cnt_ref = 0
                for sym, ind_raw in HARDCODED_HOSE_INDUSTRIES_MAPPING.items():
                    if ind_raw == "Chỉ số":
                        continue
                    item = live_board.get(sym)
                    if not item:
                        continue
                    last_px = float(item.get("last") or 0.0)
                    vol = float(item.get("volume") or 0.0)
                    pct = float(item.get("pct") or 0.0)
                    if last_px <= 0 or vol <= 0:
                        continue

                    if pct > 0:
                        cnt_up += 1
                    elif pct < 0:
                        cnt_down += 1
                    else:
                        cnt_ref += 1

                    ind = "Penny" if is_penny_stock(sym) else ind_raw
                    if tm_size_mode == "Giá trị GD (Tỷ)":
                        size_val = round(float(item.get("value_bil") or (last_px * vol / 1e6)), 2)
                    else:
                        size_val = round(vol, 0)

                    if size_val > 0:
                        rows_live.append({
                            "Mã": sym,
                            "Ngành": ind,
                            "GTGD (Tỷ)": size_val,
                            "% Thay đổi": round(pct, 2),
                            "Giá": round(last_px, 2),
                        })

                if rows_live:
                    df_live_tm = pd.DataFrame(rows_live)
                    sync_ts = ws_mgr.last_update.strftime("%H:%M:%S") if ws_mgr.last_update else vn_now().strftime("%H:%M:%S")
                    st.caption(
                        f"🟢 **SSI Realtime HOSE** • Đồng bộ lúc `{sync_ts}` • "
                        f"Tăng: **{cnt_up}** | Giảm: **{cnt_down}** | TC: **{cnt_ref}**"
                    )
                    st.plotly_chart(build_vn_treemap(df_live_tm), width="stretch", key="tm_live_chart")
                else:
                    st.info("Đang đồng bộ dữ liệu khớp lệnh phiên hôm nay từ SSI...")

            @st.fragment(run_every=5)
            def _treemap_live_fragment():
                _render_live_treemap()

            if LIVE_AUTO:
                _treemap_live_fragment()
            else:
                _render_live_treemap()

    # --- SUB-TAB 1.3: SỨC KHỎE & NGÀY PHÂN PHỐI ---
    with t3:
        c1, c2, c3, c4, c5, _ = st.columns([1.2, 0.9, 0.9, 0.9, 1.4, 0.7], vertical_alignment="bottom")
        ma_date = c1.date_input("Ngày phân tích", value=TODAY_VN, key="ma_date")
        dd_win = c2.number_input("Cửa sổ DD", 10, 60, 25)
        cancel_reb = c3.number_input("Xóa DD (%)", 3.0, 15.0, 6.0, step=0.5)
        ma20_lag = c4.number_input("Độ trễ MA20", 1, 20, 1)
        run_ma = c5.button("🩺 Phân Tích Thị Trường", type="primary", width="stretch")

        if run_ma:
            idx_map = fetch_batch_ohlcv_ssi(
                ["VNINDEX", "VN30", "HNX", "UPCOM"],
                ma_date - timedelta(days=365), ma_date, "D", max_workers=4,
            )
            summary_lines = []
            for idx_name in ["VNINDEX", "VN30", "HNX", "UPCOM"]:
                df_i = idx_map.get(idx_name)
                if df_i is not None and not df_i.empty:
                    dd, stall, churn, score, details = compute_distribution_days_core(
                        df_i, window=int(dd_win), cancel_rebound_pct=float(cancel_reb), return_details=True
                    )
                    dd_dates = ", ".join([d.strftime("%d/%m") for d in details[details["type"] == "DD"].index[-8:]]) if not details.empty else "—"
                    extra = ""
                    if idx_name == "VNINDEX":
                        close = float(df_i["Close"].iloc[-1])
                        ma50 = float(df_i["Close"].rolling(50, min_periods=50).mean().iloc[-1])
                        ma20 = float(df_i["Close"].rolling(20, min_periods=20).mean().iloc[-1])
                        if pd.notna(ma50) and close < ma50:
                            alloc_txt, reason = "0%", "Gãy MA50"
                        elif dd >= 5 and pd.notna(ma20) and close < ma20:
                            alloc_txt, reason = "0%", "Phân phối ≥ 5 + Dưới MA20"
                        else:
                            alloc_txt = f"{get_target_exposure_from_risk(score) * 100:.0f}%"
                            reason = f"Theo Risk Score ({score:.1f})"
                        extra = f" | **Rủi ro:** `{score:.1f}` → **Tỷ trọng:** `{alloc_txt}` ({reason})"
                    summary_lines.append(f"**{idx_name}**: Phân phối **{dd}** ({dd_dates}) | Stalling **{stall}** | Churning **{churn}**{extra}")

            syms = [s for s, ind in HARDCODED_HOSE_INDUSTRIES_MAPPING.items() if ind not in ("Chỉ số", "Penny") and not is_penny_stock(s)]
            prog = st.progress(0, text="Đang quét sức mạnh các nhóm ngành...")
            sec_dfs = fetch_batch_ohlcv_ssi(
                syms, ma_date - timedelta(days=180), ma_date, "D",
                _progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
            )
            prog.empty()

            sec_groups: dict = {}
            lag = int(ma20_lag)
            for s, df_s in sec_dfs.items():
                if len(df_s) >= (60 + lag):
                    ind = HARDCODED_HOSE_INDUSTRIES_MAPPING.get(s, "Khác")
                    sub_c = df_s["Close"].iloc[-100:]
                    m20 = sub_c.rolling(20, min_periods=20).mean()
                    m50 = sub_c.rolling(50, min_periods=50).mean()
                    g = sec_groups.setdefault(ind, {"tot": 0, "a20": 0, "b50": 0, "prev_sum": 0.0, "prev_cnt": 0})
                    g["tot"] += 1
                    if pd.notna(m20.iloc[-1]) and sub_c.iloc[-1] > m20.iloc[-1]:
                        g["a20"] += 1
                    if pd.notna(m50.iloc[-1]) and sub_c.iloc[-1] < m50.iloc[-1]:
                        g["b50"] += 1
                    p_c = sub_c.iloc[-(lag + 1):-1]
                    p_m = m20.iloc[-(lag + 1):-1]
                    if len(p_c) > 0:
                        g["prev_sum"] += float(((p_c > p_m) & p_m.notna()).mean())
                        g["prev_cnt"] += 1

            lead_rows, weak_rows = [], []
            for k, v in sec_groups.items():
                if v["tot"] == 0:
                    continue
                pct_now = v["a20"] / v["tot"] * 100.0
                pct_prev = (v["prev_sum"] / v["prev_cnt"] * 100.0) if v["prev_cnt"] else 0.0
                delta_pp = pct_now - pct_prev
                pct_b50 = v["b50"] / v["tot"] * 100.0
                if pct_now > 50.0:
                    lead_rows.append({
                        "Ngành": k, "% > MA20": round(pct_now, 1),
                        "Trước đó": round(pct_prev, 1), "Thay đổi": round(delta_pp, 1),
                        "Cảnh báo": "⚠️ Suy yếu" if (pct_prev - pct_now) >= 25.0 else "—",
                        "Số mã": v["tot"],
                    })
                if pct_b50 > 50.0:
                    weak_rows.append({"Ngành": k, "% < MA50": round(pct_b50, 1), "Số mã": v["tot"]})

            st.session_state["ma_res"] = {
                "summary": summary_lines,
                "leaders": pd.DataFrame(lead_rows).sort_values("% > MA20", ascending=False) if lead_rows else pd.DataFrame(),
                "weak": pd.DataFrame(weak_rows).sort_values("% < MA50", ascending=False) if weak_rows else pd.DataFrame(),
            }

        if "ma_res" in st.session_state:
            res_ma = st.session_state["ma_res"]
            for line in res_ma["summary"]:
                st.info(line)

            col_l, col_w = st.columns([1.4, 1])
            with col_l:
                st.markdown("#### 🔥 Nhóm Ngành DẪN DẮT (> 50% mã trên MA20)")
                df_l = res_ma["leaders"]
                if not df_l.empty:
                    styled_l = (
                        df_l.style
                        .map(_color_pct_strength, subset=["% > MA20"])
                        .map(_color_signed, subset=["Thay đổi"])
                        .map(_color_status, subset=["Cảnh báo"])
                        .format({"% > MA20": "{:.1f}%", "Trước đó": "{:.1f}%", "Thay đổi": "{:+.1f}%"})
                    )
                    st.dataframe(styled_l, width="stretch", hide_index=True, height=_auto_df_height(df_l))
                else:
                    st.caption("Không có nhóm ngành nào đạt chuẩn dẫn dắt.")
            with col_w:
                st.markdown("#### ❄️ Nhóm Ngành SUY YẾU (> 50% mã dưới MA50)")
                df_w = res_ma["weak"]
                if not df_w.empty:
                    styled_w = (
                        df_w.style
                        .map(_color_pct_weak, subset=["% < MA50"])
                        .format({"% < MA50": "{:.1f}%"})
                    )
                    st.dataframe(styled_w, width="stretch", hide_index=True, height=_auto_df_height(df_w))
                else:
                    st.caption("Không có nhóm ngành nào suy yếu > 50%.")


# ==============================================================================
# WORKSPACE 2: SÓNG NGÀNH & DÒNG TIỀN
# ==============================================================================
elif workspace == "🧭 Sóng Ngành & Dòng Tiền":
    t_ma, t_mf = st.tabs(["🧭 Xu Hướng MA Ngành", "💸 Dòng Tiền Ngành (Money Flow)"])

    # --- SUB-TAB 2.1: XU HƯỚNG MA NGÀNH ---
    with t_ma:
        c1, c2, c3, c4, _ = st.columns([1.8, 1.2, 1.3, 1.0, 1.2], vertical_alignment="bottom")
        ind_choice = c1.selectbox("Nhóm ngành", [g for g in INDUSTRY_GROUPS if g != "Chỉ số"], key="sec_ma_ind")
        ma_asof = c2.date_input("Ngày tra cứu", value=TODAY_VN, key="sec_ma_date")
        run_sec_ma = c3.button("🔄 Quét Xu Hướng MA", type="primary", width="stretch")

        if run_sec_ma:
            syms = get_symbols_by_industry(ind_choice, exclude_penny=(ind_choice == "Tất cả ngành"))
            prog = st.progress(0, text="Đang quét đường trung bình MA từ SSI...")
            dfs = fetch_batch_ohlcv_ssi(
                syms, ma_asof - timedelta(days=450), ma_asof, "D",
                _progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
            )
            prog.empty()

            def _ma_stt(px, mv):
                if pd.isna(px) or pd.isna(mv):
                    return "—"
                return "CHẠM" if abs(px - mv) <= 0.001 * px else ("TRÊN" if px > mv else "DƯỚI")

            if ind_choice == "Tất cả ngành":
                groups: dict = {}
                for s, df_s in dfs.items():
                    if len(df_s) >= 50:
                        ind = HARDCODED_HOSE_INDUSTRIES_MAPPING.get(s, "Khác")
                        c_now = float(df_s["Close"].iloc[-1])
                        m20 = float(df_s["Close"].rolling(20).mean().iloc[-1])
                        m50 = float(df_s["Close"].rolling(50).mean().iloc[-1])
                        g = groups.setdefault(ind, {"tot": 0, "a20": 0, "b50": 0, "best_d": -1e9, "hl": ""})
                        g["tot"] += 1
                        if _ma_stt(c_now, m20) == "TRÊN":
                            g["a20"] += 1
                        if _ma_stt(c_now, m50) == "DƯỚI":
                            g["b50"] += 1
                        if m20 > 0:
                            d_pct = (c_now - m20) / m20 * 100.0
                            if d_pct > g["best_d"]:
                                g["best_d"] = d_pct
                                g["hl"] = s

                rows = []
                for ind, g in groups.items():
                    pct_s = round(g["a20"] / g["tot"] * 100.0, 1)
                    pct_w = round(g["b50"] / g["tot"] * 100.0, 1)
                    lbl = "DẪN DẮT" if pct_s >= 50 else ("YẾU" if pct_w >= 50 else "TRUNG LẬP")
                    rows.append({
                        "Ngành": ind, "Phân loại": lbl,
                        "% Mạnh (>MA20)": pct_s, "% Yếu (<MA50)": pct_w,
                        "Tổng mã": g["tot"], "Mã nổi bật": g["hl"],
                        "MA tham chiếu": "MA20",
                        "Δ (%)": round(g["best_d"], 1) if g["hl"] else np.nan,
                    })
                st.session_state["sec_ma_df"] = pd.DataFrame(rows).sort_values(["% Mạnh (>MA20)", "% Yếu (<MA50)"], ascending=[False, True])
                st.session_state["sec_ma_mode"] = "all"
            else:
                rows = []
                for s, df_s in dfs.items():
                    if not df_s.empty:
                        c_now = float(df_s["Close"].iloc[-1])
                        c_prev = float(df_s["Close"].iloc[-2]) if len(df_s) >= 2 else c_now
                        item = {"Mã": s, "Giá": round(c_now, 2), "% Thay đổi": round((c_now / c_prev - 1) * 100, 2)}
                        score = 0
                        for w in MA_WINDOWS:
                            if len(df_s) >= w:
                                mv = float(df_s["Close"].rolling(w).mean().iloc[-1])
                                stt = _ma_stt(c_now, mv)
                                if stt == "TRÊN":
                                    score += 1
                                item[f"MA{w}"] = f"{stt} ({mv:,.2f})"
                            else:
                                item[f"MA{w}"] = "—"
                        item["_score"] = score
                        rows.append(item)
                df_grp = pd.DataFrame(rows).sort_values(["_score", "Mã"], ascending=[False, True]).drop(columns=["_score"]) if rows else pd.DataFrame()
                st.session_state["sec_ma_df"] = df_grp
                st.session_state["sec_ma_mode"] = "group"

        if "sec_ma_df" in st.session_state and not st.session_state["sec_ma_df"].empty:
            df_show = st.session_state["sec_ma_df"]
            csv_bytes = df_show.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            c4.download_button("💾 Xuất CSV", data=csv_bytes, file_name=f"sector_ma_{ma_asof}.csv", mime="text/csv", width="stretch")

            if st.session_state.get("sec_ma_mode") == "all":
                styled = (
                    df_show.style
                    .map(_color_status, subset=["Phân loại"])
                    .map(_color_pct_strength, subset=["% Mạnh (>MA20)"])
                    .map(_color_pct_weak, subset=["% Yếu (<MA50)"])
                    .map(_color_signed, subset=["Δ (%)"])
                    .format({"% Mạnh (>MA20)": "{:.1f}%", "% Yếu (<MA50)": "{:.1f}%", "Δ (%)": "{:+.1f}%"}, na_rep="—")
                )
            else:
                ma_cols = [f"MA{w}" for w in MA_WINDOWS if f"MA{w}" in df_show.columns]
                styled = (
                    df_show.style
                    .map(_color_signed, subset=["% Thay đổi"])
                    .map(_color_status, subset=ma_cols)
                    .format({"Giá": "{:,.2f}", "% Thay đổi": "{:+.2f}%"})
                )
            st.dataframe(styled, width="stretch", hide_index=True, height=_auto_df_height(df_show))

    # --- SUB-TAB 2.2: DÒNG TIỀN NGÀNH ---
    with t_mf:
        c1, c2, c3, c4, _ = st.columns([1.2, 0.9, 1.6, 1.3, 1.0], vertical_alignment="bottom")
        mf_date = c1.date_input("Ngày kết thúc", value=TODAY_VN, key="mf_date")
        mf_days = c2.number_input("Số phiên", 3, 60, 10)
        mf_method = c3.selectbox("Phương pháp", ["ΔP × Vol (VNĐ)", "Signed TP × Vol (VNĐ)", "CMF × GTGD (VNĐ)"])
        if c4.button("💸 Phân Tích Dòng Tiền", type="primary", width="stretch"):
            syms = [s for s, ind in HARDCODED_HOSE_INDUSTRIES_MAPPING.items() if ind != "Chỉ số"]
            prog = st.progress(0, text="Đang tải dữ liệu dòng tiền toàn sàn từ SSI...")
            dfs = fetch_batch_ohlcv_ssi(
                syms, mf_date - timedelta(days=int(mf_days) * 2 + 15), mf_date, "D",
                _progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
            )
            prog.empty()
            st.session_state["mf_raw_dfs"] = dfs
            st.session_state["mf_params"] = (mf_date, int(mf_days))

        if "mf_raw_dfs" in st.session_state:
            dfs = st.session_state["mf_raw_dfs"]
            saved_date, saved_days = st.session_state["mf_params"]
            per_ind: dict = {}
            for sym, df_s in dfs.items():
                sub = df_s[df_s.index.date <= saved_date]
                if len(sub) < saved_days + 1:
                    continue
                sub = sub.iloc[-(saved_days + 1):].copy()
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
                pct = float(sub["Close"].iloc[-1] / sub["Close"].iloc[0] - 1.0) * 100.0 if sub["Close"].iloc[0] > 0 else 0.0

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
            styled_mf = (
                df_mf.style
                .map(_color_signed, subset=["Dòng tiền ròng (Tỷ VNĐ)", "CMF (N phiên)", "% Giá TB"])
                .format({
                    "Dòng tiền ròng (Tỷ VNĐ)": "{:+,.2f}",
                    "Tổng GTGD (Tỷ VNĐ)": "{:,.2f}",
                    "CMF (N phiên)": "{:+.3f}",
                    "% Giá TB": "{:+.2f}%",
                })
            )
            st.dataframe(styled_mf, width="stretch", hide_index=True, height=_auto_df_height(df_mf))


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
        c1, c2, c3, c4, c5, c6 = st.columns([0.8, 0.8, 1.1, 0.9, 1.5, 1.3], vertical_alignment="bottom")
        ma_f = c1.number_input("MA Nhanh", 5, 50, 20)
        ma_m = c2.number_input("MA Trung", 20, 100, 50)
        min_v = c3.number_input("Min Vol", 0, 10_000_000, 100_000, step=50_000)
        use_ftd = c4.checkbox("Bật FTD", value=True)
        ftd_mode = c5.selectbox(
            "Chuẩn FTD", [0, 1],
            format_func=lambda x: "Nâng cao (Vol > MA20)" if x == 0 else "Tiêu chuẩn (Vol > Hôm trước)",
            disabled=not use_ftd,
        )
        if c6.button("📡 Quét Thị Trường EOD", type="primary", width="stretch"):
            syms = get_symbols_by_industry("Tất cả ngành", exclude_penny=True) + ["VNINDEX"]
            prog = st.progress(0, text="Đang quét Radar EOD toàn sàn...")
            dfs = fetch_batch_ohlcv_ssi(
                syms, TODAY_VN - timedelta(days=350), TODAY_VN, "D",
                _progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
            )
            prog.empty()

            vni = dfs.get("VNINDEX")
            risk_info = {"date": TODAY_VN.strftime("%d/%m/%Y"), "phase": "Không xác định", "target": 0.0, "dd": 0.0, "rally": 0, "is_ftd": False, "risk": 0.0}
            if vni is not None and not vni.empty:
                vni["VolMA20"] = vni["Volume"].rolling(20).mean()
                ftd_state = {"historical_peak": 0.0, "reference_peak": 0.0, "is_confirmed_uptrend": True, "rally_attempt_count": 0, "rally_low": float("inf"), "market_phase": "Uptrend"}
                for i in range(len(vni)):
                    r = vni.iloc[i]
                    p_c = float(vni["Close"].iloc[i - 1]) if i > 0 else float(r["Close"])
                    p_v = float(vni["Volume"].iloc[i - 1]) if i > 0 else float(r["Volume"])
                    ftd_state = evaluate_market_ftd_step(
                        ftd_state, float(r["Close"]), float(r["Low"]), float(r["Volume"]),
                        p_c, p_v, float(r["VolMA20"] or 0), use_ftd=use_ftd, ftd_mode=int(ftd_mode),
                    )
                _, _, _, risk_sc = compute_distribution_days_core(vni, window=25)
                tgt_exp = 0.0 if not ftd_state["is_confirmed_uptrend"] else (0.7 if ftd_state["market_phase"] == "Pullback" else get_target_exposure_from_risk(risk_sc))
                ma200_vni = vni["Close"].rolling(200).mean().iloc[-1]
                below_200 = pd.notna(ma200_vni) and float(vni["Close"].iloc[-1]) < float(ma200_vni)
                risk_info = {
                    "date": vni.index[-1].strftime("%d/%m/%Y"),
                    "phase": f"{ftd_state['market_phase']} {'(<MA200)' if below_200 else ''}".strip(),
                    "target": tgt_exp * 100.0,
                    "dd": ftd_state["actual_drawdown"] * 100.0,
                    "rally": ftd_state["rally_attempt_count"],
                    "is_ftd": ftd_state["is_confirmed_uptrend"],
                    "risk": risk_sc,
                }

            sec_map: dict = {}
            for sym, sec in HARDCODED_HOSE_INDUSTRIES_MAPPING.items():
                if sec not in ["Chỉ số", "Penny", "Khác"] and not is_penny_stock(sym) and sym in dfs:
                    sec_map.setdefault(sec, []).append(sym)

            sec_rows = []
            for sec, s_list in sec_map.items():
                cnt_up = sum(1 for s in s_list if len(dfs[s]) >= int(ma_f) and float(dfs[s]["Close"].iloc[-1]) > float(dfs[s]["Close"].rolling(int(ma_f)).mean().iloc[-1]))
                sec_rows.append({"Ngành": sec, "Sức Mạnh": round(cnt_up / len(s_list) * 100.0, 1), "Số Mã > MA": f"{cnt_up}/{len(s_list)}"})
            sec_df = pd.DataFrame(sec_rows).sort_values("Sức Mạnh", ascending=False) if sec_rows else pd.DataFrame()

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
                if c > maf and vma > 0:
                    full = (c > maf > mam > mas)
                    v_sc = v / vma
                    brk = (v > min_v) and (v_sc > 1.0)
                    sig = "ĐẠT (Full)" if (full and brk) else ("Chờ Vol" if full else ("Nổ Vol (Hồi)" if brk else "Tích lũy"))
                    stk_rows.append({
                        "Mã CP": sym, "Ngành": HARDCODED_HOSE_INDUSTRIES_MAPPING.get(sym, "Khác"),
                        "Giá": round(c, 2), "Volume": int(v), "Hệ Số Vol": round(v_sc, 2),
                        "Tín Hiệu": sig, "_full": full,
                    })
            stk_df = pd.DataFrame(stk_rows).sort_values(["_full", "Hệ Số Vol"], ascending=[False, False]).drop(columns=["_full"]).head(50) if stk_rows else pd.DataFrame()
            st.session_state["radar_res"] = {"risk": risk_info, "sec": sec_df, "stk": stk_df}

        if "radar_res" in st.session_state:
            rr = st.session_state["radar_res"]
            rk = rr["risk"]
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            k1.metric("Ngày Cập Nhật", rk["date"])
            k2.metric("Trạng Thái TT", rk["phase"])
            k3.metric("Tỷ Trọng KN", f"{rk['target']:.0f}%")
            k4.metric("Độ Sâu ĐC", f"{rk['dd']:.1f}%")
            k5.metric("Nỗ Lực Hồi Phục", "✅ FTD" if rk["is_ftd"] else (f"Ngày {rk['rally']}" if rk["rally"] > 0 else "Chưa tạo đáy"))
            k6.metric("Risk Score", f"{rk['risk']:.1f}")

            col_s1, col_s2 = st.columns([1, 2.2])
            with col_s1:
                st.markdown("#### 🏆 Top Ngành Dẫn Dắt")
                if not rr["sec"].empty:
                    st.dataframe(
                        rr["sec"].style.map(_color_pct_strength, subset=["Sức Mạnh"]).format({"Sức Mạnh": "{:.1f}%"}),
                        width="stretch", hide_index=True, height=_auto_df_height(rr["sec"]),
                    )
            with col_s2:
                st.markdown("#### 🚀 Top Cổ Phiếu Nổi Bật")
                if not rr["stk"].empty:
                    st.dataframe(
                        rr["stk"].style
                        .map(_color_vol_score, subset=["Hệ Số Vol"])
                        .map(_color_status, subset=["Tín Hiệu"])
                        .format({"Giá": "{:,.2f}", "Volume": "{:,.0f}", "Hệ Số Vol": "{:.2f}x"}),
                        width="stretch", hide_index=True, height=_auto_df_height(rr["stk"]),
                    )

    # --- SUB-TAB 3.2: MINERVINI & VCP PRO ---
    with t_min:
        c1, c2, c3, c4, _ = st.columns([1.1, 1.1, 0.9, 1.6, 1.3], vertical_alignment="bottom")
        min_start = c1.date_input("Từ ngày", value=TODAY_VN - timedelta(days=365), key="min_s")
        min_end = c2.date_input("Đến ngày", value=TODAY_VN, key="min_e")
        min_rs = c3.number_input("RS Min", 50, 99, 70)
        if c4.button("🚀 Quét Siêu Cổ Phiếu Minervini", type="primary", width="stretch"):
            syms = get_symbols_by_industry("Tất cả ngành", exclude_penny=True)
            prog = st.progress(0, text="Đang tải dữ liệu và tính RS Rating toàn sàn...")
            raw_m = fetch_batch_ohlcv_ssi(
                syms, min_start - timedelta(days=450), min_end, "D",
                _progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
            )
            prog.empty()
            proc_map, screened, df_breadth, stats_sum = run_minervini_screener(raw_m, min_start, min_end, int(min_rs))
            st.session_state["min_res"] = {
                "proc_map": proc_map, "screened": screened,
                "breadth": df_breadth, "stats": stats_sum, "end_date": min_end,
            }

        if "min_res" in st.session_state:
            mr = st.session_state["min_res"]
            screened, proc_map, df_breadth, stats_sum = mr["screened"], mr["proc_map"], mr["breadth"], mr["stats"]

            if not df_breadth.empty:
                lb = df_breadth.iloc[-1]
                p200, pbot = float(lb["Pct_Above_MA200"]), float(lb["Pct_Bottoming"])
                if p200 >= 50:
                    st.success(f"🟢 **UPTREND XÁC NHẬN** ({p200:.1f}% cổ phiếu > MA200)")
                elif p200 <= 20:
                    st.error(f"🔴 **VÙNG HOẢNG LOẠN / DÒ ĐÁY** ({p200:.1f}% > MA200 | {pbot:.1f}% sát đáy 52T)")
                else:
                    st.warning(f"🟡 **THỊ TRƯỜNG PHÂN HÓA** ({p200:.1f}% > MA200)")

            st1, st2, st3 = st.tabs([
                f"🏆 Siêu Cổ Phiếu ({len(screened)})",
                "🔍 Chẩn Đoán Chu Kỳ & Chart VCP",
                "🌊 Độ Rộng Thị Trường",
            ])

            with st1:
                if screened:
                    df_sc = pd.DataFrame(screened)
                    styled_sc = (
                        df_sc.style
                        .map(_color_rs, subset=["RS Rating"])
                        .map(_color_status, subset=["Chu Kỳ", "Trạng Thái Pivot"])
                        .format({"Giá": "{:,.2f}", "% Đỉnh 52T": "{:+.1f}%", "Pivot": "{:,.2f}"}, na_rep="—")
                    )
                    st.dataframe(styled_sc, width="stretch", hide_index=True, height=_auto_df_height(df_sc))
                else:
                    st.info("Không có mã nào thỏa mãn toàn bộ 8 tiêu chí Trend Template ở thời điểm này.")

            with st2:
                if proc_map:
                    default_sym = screened[0]["Mã CP"] if screened else sorted(list(proc_map.keys()))[0]
                    all_m_syms = sorted(list(proc_map.keys()))
                    sc_sel, _ = st.columns([1.2, 4.8])
                    diag_sym = sc_sel.selectbox("Chọn cổ phiếu kiểm tra", all_m_syms, index=all_m_syms.index(default_sym))
                    df_d = proc_map[diag_sym]
                    latest = df_d.iloc[-1].to_dict()
                    p_title, p_col, p_desc = evaluate_stock_phase(latest)
                    vcp = detect_vcp_pattern(df_d, mr["end_date"])

                    col_info, col_chart = st.columns([1.2, 2.8])
                    with col_info:
                        st.markdown(
                            f"<div style='padding:12px; border-left:4px solid {p_col}; background:#ffffff; "
                            f"border-radius:8px; border:1px solid #e2e8f0; border-left-width:4px;'>"
                            f"<b style='color:{p_col}; font-size:15px;'>{p_title}</b><br>{p_desc}</div>",
                            unsafe_allow_html=True,
                        )
                        if vcp:
                            st.success(f"**VCP {vcp['num_contractions']}T:** {' -> '.join([str(x)+'%' for x in vcp['ranges']])}\n\n**Pivot:** `{vcp['buy_point']:,.2f}` ({vcp['status']})")
                        c_val = latest["Close"]
                        st.markdown(f"""
                        **📋 Minervini Trend Template:**
                        - Giá vs MA50 (`{latest['MA50']:,.2f}`): **{'🟢 Trên' if c_val > latest['MA50'] else '🔴 Dưới'}**
                        - Giá vs MA150 (`{latest['MA150']:,.2f}`): **{'🟢 Trên' if c_val > latest['MA150'] else '🔴 Dưới'}**
                        - Giá vs MA200 (`{latest['MA200']:,.2f}`): **{'🟢 Trên' if c_val > latest['MA200'] else '🔴 Dưới'}**
                        - Đỉnh 52T: `{latest['Peak_52W']:,.2f}` (`{latest['Pct_From_Peak']:+.1f}%`)
                        - Đáy 52T: `{latest['Bottom_52W']:,.2f}` (`{latest['Pct_From_Bottom']:+.1f}%`)
                        - **RS Rating:** **`{latest.get('RS_Rating', 0)} / 99`**
                        """)
                    with col_chart:
                        df_d_tmp = df_d.copy()
                        df_d_tmp["PrevClose"] = df_d_tmp["Close"].shift(1)
                        sub_p = df_d_tmp.tail(150)

                        x_vcp = _trading_x_labels(sub_p.index, is_intraday=False)
                        fig_vcp = go.Figure()
                        _add_candlestick_clean(fig_vcp, x_vcp, sub_p, diag_sym)
                        vcp_mas = [("MA50", "#f97316"), ("MA150", "#8b5cf6"), ("MA200", "#ef4444")]
                        for ma_col, col_hex in vcp_mas:
                            fig_vcp.add_trace(
                                go.Scatter(x=x_vcp, y=sub_p[ma_col], name=ma_col, line=dict(color=col_hex, width=1.5), hoverinfo="skip")
                            )
                        if vcp:
                            fig_vcp.add_hline(y=vcp["buy_point"], line_dash="dot", line_color="#7c3aed", annotation_text=f"Pivot: {vcp['buy_point']:,.2f}")
                        _style_chart(fig_vcp, height=420, categorical_x=True)
                        fig_vcp.update_layout(xaxis_rangeslider_visible=False)
                        _render_dynamic_ohlc_chart(
                            fig_vcp, sub_p, diag_sym,
                            prev_close_series=sub_p["PrevClose"],
                            ma_info=vcp_mas, is_intraday=False, height=420, chart_id="vcp",
                        )

            with st3:
                if not df_breadth.empty:
                    lb = df_breadth.iloc[-1]
                    b1, b2, b3, b4 = st.columns(4)
                    b1.metric("Giá TB HOSE", f"{lb['Avg_Price']:,.1f}")
                    b2.metric("Độ Rộng (> MA200)", f"{lb['Pct_Above_MA200']:.1f}%")
                    b3.metric("% Sát Đáy 52T", f"{lb['Pct_Bottoming']:.1f}%")
                    b4.metric("Sụt Giảm Từ Đỉnh", f"-{stats_sum['pct_drop']:.1f}%")

                    x_br = _trading_x_labels(df_breadth.index, is_intraday=False)
                    fig_br = make_subplots(specs=[[{"secondary_y": True}]])
                    fig_br.add_trace(go.Scatter(x=x_br, y=df_breadth["Avg_Price"], name="Giá TB HOSE", line=dict(color="#0284c7", width=2)), secondary_y=False)
                    fig_br.add_trace(go.Scatter(x=x_br, y=df_breadth["Pct_Above_MA200"], name="% > MA200", line=dict(color="#f59e0b", width=1.8)), secondary_y=True)
                    fig_br.add_trace(go.Scatter(x=x_br, y=df_breadth["Pct_Bottoming"], name="% Dò đáy 52T", line=dict(color="#8b5cf6", dash="dot")), secondary_y=True)
                    fig_br.add_hline(y=20, line_dash="dash", line_color="#ef4444", secondary_y=True)
                    fig_br.add_hline(y=50, line_dash="dash", line_color="#94a3b8", secondary_y=True)
                    _style_chart(fig_br, height=420, categorical_x=True)
                    st.plotly_chart(fig_br, width="stretch")

    # --- SUB-TAB 3.3: LỌC CP TĂNG MẠNH ---
    with t_gain:
        c1, c2, c3, c4, c5, c6 = st.columns([1.0, 1.0, 1.3, 0.7, 1.5, 1.1], vertical_alignment="bottom")
        g_start = c1.date_input("Từ ngày", value=TODAY_VN - timedelta(days=30), key="g_s")
        g_end = c2.date_input("Đến ngày", value=TODAY_VN, key="g_e")
        g_ind = c3.selectbox("Nhóm ngành", INDUSTRY_GROUPS, key="g_ind")
        g_top = c4.selectbox("Top", [10, 15, 20, 30, 50], index=0)
        g_rank = c5.selectbox("Xếp hạng theo", ["Kết hợp (Hồi & Giảm từ Đỉnh)", "% Thay Đổi", "% Hồi từ Đáy"])
        if c6.button("🚀 Lọc Cổ Phiếu", type="primary", width="stretch"):
            syms = get_symbols_by_industry(g_ind, exclude_penny=(g_ind == "Tất cả ngành"))
            prog = st.progress(0, text="Đang tải dữ liệu lọc cổ phiếu tăng mạnh...")
            dfs = fetch_batch_ohlcv_ssi(
                syms, g_start - timedelta(days=10), g_end, "D",
                _progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
            )
            prog.empty()
            g_rows = []
            for sym, df_s in dfs.items():
                sub = df_s[(df_s.index.date >= g_start) & (df_s.index.date <= g_end)]
                if len(sub) >= 2:
                    c0, cl = float(sub["Close"].iloc[0]), float(sub["Close"].iloc[-1])
                    hmax, lmin = float(sub["High"].max()), float(sub["Low"].min())
                    if c0 > 0 and lmin > 0 and hmax > 0:
                        g_rows.append({
                            "Mã CP": sym,
                            "Nhóm Ngành": "Penny" if g_ind == "Penny" else HARDCODED_HOSE_INDUSTRIES_MAPPING.get(sym, "Khác"),
                            "% Thay Đổi": round((cl - c0) / c0 * 100.0, 2),
                            "% Tăng từ Đáy": round((cl - lmin) / lmin * 100.0, 2),
                            "% Giảm từ Đỉnh": round((cl - hmax) / hmax * 100.0, 2),
                            "Biên Độ (H/L)": round((hmax - lmin) / c0 * 100.0, 2),
                            "Ngày đạt đỉnh": sub["High"].idxmax().strftime("%d-%m-%Y"),
                        })
            st.session_state["gainers_df"] = pd.DataFrame(g_rows)

        if "gainers_df" in st.session_state and not st.session_state["gainers_df"].empty:
            df_g = st.session_state["gainers_df"].copy()
            if g_rank == "% Thay Đổi":
                df_g = df_g.sort_values("% Thay Đổi", ascending=False)
            elif g_rank == "% Hồi từ Đáy":
                df_g = df_g.sort_values("% Tăng từ Đáy", ascending=False)
            else:
                df_g["_score"] = df_g["% Tăng từ Đáy"] + df_g["% Giảm từ Đỉnh"]
                df_g = df_g.sort_values("_score", ascending=False).drop(columns=["_score"])

            df_g_show = df_g.head(g_top)
            styled_g = (
                df_g_show.style
                .map(_color_signed, subset=["% Thay Đổi", "% Tăng từ Đáy", "% Giảm từ Đỉnh"])
                .map(_color_purple, subset=["Biên Độ (H/L)"])
                .format({
                    "% Thay Đổi": "{:+.2f}%",
                    "% Tăng từ Đáy": "{:+.2f}%",
                    "% Giảm từ Đỉnh": "{:+.2f}%",
                    "Biên Độ (H/L)": "{:.2f}%",
                })
            )
            st.dataframe(styled_g, width="stretch", hide_index=True, height=_auto_df_height(df_g_show))


# ==============================================================================
# WORKSPACE 4: PHÂN TÍCH BIỂU ĐỒ (DYNAMIC OHLC CURSOR + LIVE WS 5S)
# ==============================================================================
elif workspace == "📈 Phân Tích Biểu Đồ":
    t_eod, t_intra = st.tabs(["📉 Biểu Đồ Kỹ Thuật (EOD)", "⚡ Khớp Lệnh Trong Phiên & Bảng Giá SSI"])

    # --- SUB-TAB 4.1: BIỂU ĐỒ KỸ THUẬT EOD ---
    with t_eod:
        c1, c2, c3, c4, c5 = st.columns([1.4, 1.1, 1.1, 1.1, 1.0], vertical_alignment="bottom")
        ind_sel = c1.selectbox("Nhóm ngành", INDUSTRY_GROUPS, key="hist_ind")
        if ind_sel == "Chỉ số":
            sym_list = ALL_MAIN_INDICES + [s for s in get_symbols_by_industry("Chỉ số") if s not in ALL_MAIN_INDICES]
        elif ind_sel == "Tất cả ngành":
            sym_list = ALL_MAIN_INDICES + get_symbols_by_industry("Tất cả ngành", exclude_penny=False)
        else:
            sym_list = get_symbols_by_industry(ind_sel, exclude_penny=False)

        sym_sel = c2.selectbox("Mã cổ phiếu / Chỉ số", sym_list, index=sym_list.index("FPT") if "FPT" in sym_list else 0)
        h_start = c3.date_input("Từ ngày", value=TODAY_VN - timedelta(days=365), key="h_s")
        h_end = c4.date_input("Đến ngày", value=TODAY_VN, key="h_e")
        h_tf = c5.selectbox("Khung", ["1 Ngày", "1 Tuần", "1 Tháng"])

        o1, o2, o3, o4 = st.columns([2.2, 1.2, 1.0, 1.4], vertical_alignment="bottom")
        ma_sel = o1.multiselect("Đường MA", [10, 20, 50, 100, 200], default=[10, 20, 50])
        custom_ma_txt = o2.text_input("Custom MA", placeholder="vd: 5, 15")
        show_ma_vol = o3.checkbox("MA20 Vol", value=True)
        show_ath = o4.checkbox("Đỉnh LS (ATH) & Giá hiện tại", value=True)

        active_mas = list(ma_sel)
        if custom_ma_txt:
            for part in re.split(r"[,;\s]+", custom_ma_txt):
                if part.isdigit() and 1 < int(part) < 500:
                    active_mas.append(int(part))
        active_mas = sorted(list(set(active_mas)))

        def _render_eod_chart_body():
            ws_mgr.subscribe([sym_sel])
            tick = ws_mgr.get_snapshot([sym_sel]).get(sym_sel) if h_end >= TODAY_VN else None

            df_hist = fetch_ssi_ohlcv_cached(sym_sel, h_start - timedelta(days=400), h_end, "D")
            if df_hist.empty:
                st.warning(f"Không có dữ liệu biểu đồ cho mã {sym_sel}.")
                return

            if h_end >= TODAY_VN and tick:
                df_hist = _patch_live_candle(df_hist, tick, is_intraday=False)

            raw_ath = float(df_hist["High"].max())
            logic = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
            if h_tf == "1 Tuần":
                df_hist = df_hist.resample("W-FRI").apply(logic).dropna()
            elif h_tf == "1 Tháng":
                try:
                    df_hist = df_hist.resample("ME").apply(logic).dropna()
                except ValueError:
                    df_hist = df_hist.resample("M").apply(logic).dropna()

            for p in active_mas:
                df_hist[f"MA{p}"] = df_hist["Close"].rolling(p, min_periods=1).mean()
            df_hist["MA20_Vol"] = df_hist["Volume"].rolling(20, min_periods=1).mean()
            df_hist["PrevClose"] = df_hist["Close"].shift(1)
            plot_df = df_hist[df_hist.index.date >= h_start]

            if plot_df.empty:
                return

            x_lbls = _trading_x_labels(plot_df.index, is_intraday=False)
            fig_c = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.74, 0.26], vertical_spacing=0.03)
            _add_candlestick_clean(fig_c, x_lbls, plot_df, sym_sel, row=1, col=1)

            ma_info_list = []
            fallback_cols = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
            for idx_p, p in enumerate(active_mas):
                col_hex = MA_COLORS.get(p, fallback_cols[idx_p % len(fallback_cols)])
                ma_info_list.append((f"MA{p}", col_hex))
                fig_c.add_trace(
                    go.Scatter(x=x_lbls, y=plot_df[f"MA{p}"], name=f"MA{p}", line=dict(color=col_hex, width=1.4), hoverinfo="skip"),
                    row=1, col=1,
                )
            if show_ath:
                last_c = float(plot_df["Close"].iloc[-1])
                fig_c.add_hline(y=raw_ath, line_dash="dash", line_color="#9333ea", annotation_text=f"ATH: {raw_ath:,.2f}", row=1, col=1)
                fig_c.add_hline(y=last_c, line_dash="dot", line_color="#0284c7", annotation_text=f"Giá: {last_c:,.2f}", row=1, col=1)

            vol_colors = ["#10b981" if c >= o else "#ef4444" for c, o in zip(plot_df["Close"], plot_df["Open"])]
            fig_c.add_trace(go.Bar(x=x_lbls, y=plot_df["Volume"], marker_color=vol_colors, name="Volume", hoverinfo="skip"), row=2, col=1)
            if show_ma_vol:
                ma_info_list.append(("MA20_Vol", "#d946ef"))
                fig_c.add_trace(
                    go.Scatter(x=x_lbls, y=plot_df["MA20_Vol"], name="MA20 Vol", line=dict(color="#d946ef", width=1.3), hoverinfo="skip"),
                    row=2, col=1,
                )

            _style_chart(fig_c, height=580, categorical_x=True)
            fig_c.update_layout(xaxis_rangeslider_visible=False)
            _render_dynamic_ohlc_chart(
                fig_c, plot_df, sym_sel,
                prev_close_series=plot_df["PrevClose"],
                ma_info=ma_info_list, is_intraday=False, height=580, chart_id="eod",
            )

        @st.fragment(run_every=5)
        def _eod_live_fragment():
            _render_eod_chart_body()

        if LIVE_AUTO and h_end >= TODAY_VN:
            _eod_live_fragment()
        else:
            _render_eod_chart_body()

    # --- SUB-TAB 4.2: KHỚP LỆNH TRONG PHIÊN (INTRADAY) ---
    with t_intra:
        c1, c2, c3, c4, _ = st.columns([1.1, 1.1, 1.0, 1.0, 1.8], vertical_alignment="bottom")
        in_sym = c1.text_input("Mã CP / Chỉ số", value="FPT").strip().upper()
        in_date = c2.date_input("Ngày khớp lệnh", value=TODAY_VN, key="in_date")
        in_tf = c3.selectbox("Khung nến", ["1", "5", "15", "30", "60"], format_func=lambda x: f"{x} phút")
        if c4.button("🔄 Cập nhật", type="primary", width="stretch", key="btn_intra_ref"):
            st.cache_data.clear()

        def _render_intraday_body():
            if not in_sym:
                return
            ws_mgr.subscribe([in_sym])
            tick = ws_mgr.get_snapshot([in_sym]).get(in_sym)

            df_in = fetch_ssi_ohlcv_cached(in_sym, in_date, in_date, in_tf)
            if in_date == TODAY_VN and in_tf == "1":
                df_in = _merge_live_intraday_series(df_in, ws_mgr.get_minute_bars_df(in_sym), TODAY_VN)
            df_in = _filter_vn_trading_hours(df_in)

            if df_in.empty:
                st.info("Chưa có dữ liệu khớp lệnh trong ngày đã chọn.")
                return

            if in_date == TODAY_VN and tick:
                df_in = _patch_live_candle(df_in, tick, is_intraday=True)

            x_lbls = _trading_x_labels(df_in.index, is_intraday=True)
            col_tbl, col_ch = st.columns([1.3, 2.7])
            with col_tbl:
                df_disp = df_in.iloc[::-1].copy()
                df_disp["%"] = (df_disp["Close"].pct_change(-1) * 100.0).fillna(0.0)
                df_disp.index = df_disp.index.strftime("%H:%M")
                st.dataframe(
                    df_disp.style
                    .map(_color_signed, subset=["%"])
                    .format({"Open": "{:,.2f}", "High": "{:,.2f}", "Low": "{:,.2f}", "Close": "{:,.2f}", "%": "{:+.2f}%", "Volume": "{:,.0f}"}),
                    height=525, width="stretch",
                )
            with col_ch:
                fig_in = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.03)
                _add_candlestick_clean(fig_in, x_lbls, df_in, in_sym, row=1, col=1)

                v_cols = ["#10b981" if c >= o else "#ef4444" for c, o in zip(df_in["Close"], df_in["Open"])]
                fig_in.add_trace(go.Bar(x=x_lbls, y=df_in["Volume"], marker_color=v_cols, name="Vol", hoverinfo="skip"), row=2, col=1)
                _style_chart(fig_in, height=450, categorical_x=True)
                fig_in.update_layout(xaxis_rangeslider_visible=False)
                _render_dynamic_ohlc_chart(
                    fig_in, df_in, in_sym,
                    is_intraday=True, height=450, chart_id="intraday",
                )

        @st.fragment(run_every=5)
        def _intraday_live_fragment():
            _render_intraday_body()

        if LIVE_AUTO and in_date == TODAY_VN:
            _intraday_live_fragment()
        else:
            _render_intraday_body()


# ==============================================================================
# WORKSPACE 5: DANH MỤC NẮM GIỮ (LIVE 5S) & BACKTEST HYBRID
# ==============================================================================
elif workspace == "💼 Danh Mục & Backtest":
    t_port, t_bt = st.tabs(["📘 Danh Mục Nắm Giữ", "🧪 Backtest Chiến Lược Hybrid"])

    # --- SUB-TAB 5.1: DANH MỤC NẮM GIỮ ---
    with t_port:
        port_file = Path("portfolio.json")
        if "portfolio_data" not in st.session_state:
            st.session_state["portfolio_data"] = json.loads(port_file.read_text(encoding="utf-8")) if port_file.exists() else []

        pc1, pc2, pc3, pc4, _ = st.columns([1.6, 1.6, 1.0, 1.0, 0.8], vertical_alignment="bottom")
        cash_vnd = pc1.number_input("Tiền mặt khả dụng (VNĐ)", 0.0, 1e12, 0.0, step=10_000_000.0)
        up_json = pc2.file_uploader("Nhập portfolio.json", type=["json"], label_visibility="collapsed")
        if up_json is not None:
            try:
                loaded = json.loads(up_json.read().decode("utf-8"))
                if isinstance(loaded, list):
                    st.session_state["portfolio_data"] = loaded
                    port_file.write_text(json.dumps(loaded, ensure_ascii=False, indent=2), encoding="utf-8")
                    st.success("Đã nhập danh mục thành công!")
            except Exception as e:
                st.error(f"File JSON không hợp lệ: {e}")

        port_json_bytes = json.dumps(st.session_state["portfolio_data"], ensure_ascii=False, indent=2).encode("utf-8")
        pc3.download_button("💾 Xuất JSON", data=port_json_bytes, file_name="portfolio.json", mime="application/json", width="stretch")
        if pc4.button("🔄 Làm mới giá", type="primary", width="stretch"):
            clear_batch_cache()
            st.cache_data.clear()

        with st.expander("➕ Thêm / Xóa vị thế danh mục", expanded=False):
            ac1, ac2, ac3, ac4, ac5, ac6 = st.columns([0.9, 1.1, 1, 1, 1.4, 1], vertical_alignment="bottom")
            new_sym = ac1.text_input("Mã CP", placeholder="VD: FPT").strip().upper()
            new_bdate = ac2.date_input("Ngày mua", value=TODAY_VN, key="port_bdate")
            new_bpx = ac3.number_input("Giá mua (nghìn)", 0.0, 1000.0, 0.0, step=0.1)
            new_qty = ac4.number_input("Khối lượng", 0, 10_000_000, 100, step=100)
            new_note = ac5.text_input("Ghi chú")
            if ac6.button("➕ Thêm", type="primary", width="stretch"):
                if new_sym and new_qty > 0:
                    st.session_state["portfolio_data"].append({
                        "symbol": new_sym, "buy_date": new_bdate.isoformat(),
                        "buy_price": new_bpx, "qty": int(new_qty), "note": new_note,
                    })
                    port_file.write_text(json.dumps(st.session_state["portfolio_data"], ensure_ascii=False, indent=2), encoding="utf-8")
                    st.rerun()

            if st.session_state["portfolio_data"]:
                del_opts = [f"#{i}: {h['symbol']} ({h['qty']:,} CP @ {h['buy_price']})" for i, h in enumerate(st.session_state["portfolio_data"])]
                dc1, dc2 = st.columns([3, 1], vertical_alignment="bottom")
                del_sel = dc1.selectbox("Chọn vị thế cần xóa", del_opts)
                if dc2.button("🗑️ Xóa vị thế", width="stretch"):
                    idx_del = int(del_sel.split(":")[0].replace("#", ""))
                    st.session_state["portfolio_data"].pop(idx_del)
                    port_file.write_text(json.dumps(st.session_state["portfolio_data"], ensure_ascii=False, indent=2), encoding="utf-8")
                    st.rerun()

        def _render_portfolio_live_body():
            holdings = st.session_state["portfolio_data"]
            if not holdings:
                st.info("Danh mục đang trống. Nhấn '➕ Thêm / Xóa vị thế danh mục' hoặc nhập file `portfolio.json`.")
                return

            syms_p = list(set([h["symbol"] for h in holdings]))
            ws_mgr.subscribe(syms_p)
            live_p = ws_mgr.get_snapshot(syms_p)
            hist_p = fetch_batch_ohlcv_ssi(syms_p, TODAY_VN - timedelta(days=400), TODAY_VN, "D")

            rows_p = []
            tot_cost = tot_val = tot_today_pl = 0.0
            for h in holdings:
                sym = h["symbol"]
                bp = float(h["buy_price"])
                qty = int(h["qty"])
                df_h = hist_p.get(sym)

                last_px = prev_px = bp
                ma20 = ma50 = ma150 = ma200 = None
                days_held = 0
                if df_h is not None and not df_h.empty:
                    last_px = float(df_h["Close"].iloc[-1])
                    prev_px = float(df_h["Close"].iloc[-2]) if len(df_h) >= 2 else last_px
                    ma20 = float(df_h["Close"].rolling(20).mean().iloc[-1]) if len(df_h) >= 20 else None
                    ma50 = float(df_h["Close"].rolling(50).mean().iloc[-1]) if len(df_h) >= 50 else None
                    ma150 = float(df_h["Close"].rolling(150).mean().iloc[-1]) if len(df_h) >= 150 else None
                    ma200 = float(df_h["Close"].rolling(200).mean().iloc[-1]) if len(df_h) >= 200 else None
                    try:
                        bd = date.fromisoformat(h["buy_date"])
                        days_held = int((df_h.index.date >= bd).sum())
                    except Exception:
                        days_held = 0

                if sym in live_p and live_p[sym].get("last"):
                    last_px = float(live_p[sym]["last"])

                pl_vnd = (last_px - bp) * qty * 1000.0
                pl_pct = ((last_px / bp - 1.0) * 100.0) if bp > 0 else 0.0
                today_pl = (last_px - prev_px) * qty * 1000.0
                row_val = last_px * qty * 1000.0
                tot_cost += bp * qty * 1000.0
                tot_val += row_val
                tot_today_pl += today_pl

                is_strong = bool(ma50 and ma150 and ma200 and (last_px > ma50 > ma150 > ma200))
                if pl_pct <= -7.0:
                    reco = "🛑 BÁN CẮT LỖ (-7%)"
                elif pl_pct <= -5.0:
                    reco = "⚠️ CẢNH BÁO (-5%)"
                elif ma50 and last_px < ma50:
                    reco = "BÁN/HẠ TỶ TRỌNG (Gãy MA50)"
                elif pl_pct >= 25.0:
                    reco = "💰 CHỐT LỜI (>25%)"
                elif pl_pct >= 20.0:
                    reco = "💎 POWER PLAY (Giữ 8 tuần)" if days_held < 15 else "CÂN NHẮC CHỐT LỜI (20-25%)"
                elif ma20 and last_px < ma20:
                    reco = "BÁN KHÓA LÃI (<MA20)" if pl_pct > 0 else "QUAN SÁT (<MA20)"
                elif 2.0 <= pl_pct <= 5.0 and is_strong:
                    reco = "➕ MUA THÊM (Xác nhận Trend)"
                elif is_strong:
                    reco = "NẮM GIỮ (Trend mạnh)"
                else:
                    reco = "NẮM GIỮ (Theo dõi)"

                rows_p.append({
                    "Mã": sym, "Ngày mua": h["buy_date"], "Giá mua": bp, "KL": qty,
                    "Số phiên": days_held, "Giá hiện tại": round(last_px, 2),
                    "Lãi/Lỗ (VNĐ)": round(pl_vnd, 0), "% Lãi/Lỗ": round(pl_pct, 2),
                    "Hôm nay (VNĐ)": round(today_pl, 0), "_val": row_val,
                    "Khuyến nghị tự động": reco, "Ghi chú": h.get("note", ""),
                })

            nav_all = tot_val + cash_vnd
            denom = nav_all if nav_all > 0 else 1.0
            for rp in rows_p:
                rp["Tỷ trọng (%)"] = round(rp.pop("_val") / denom * 100.0, 2)

            tot_pl = tot_val - tot_cost
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Tổng Lãi / Lỗ", f"{tot_pl:,.0f} đ", f"{(tot_pl / tot_cost * 100) if tot_cost > 0 else 0:+.2f}%")
            k2.metric("Biến Động Hôm Nay", f"{tot_today_pl:+,.0f} đ")
            k3.metric("Giá Trị Cổ Phiếu", f"{tot_val:,.0f} đ")
            k4.metric("Tổng NAV (Gồm Tiền Mặt)", f"{nav_all:,.0f} đ")

            df_p = pd.DataFrame(rows_p)[
                ["Mã", "Ngày mua", "Giá mua", "KL", "Số phiên", "Giá hiện tại", "Lãi/Lỗ (VNĐ)", "% Lãi/Lỗ", "Hôm nay (VNĐ)", "Tỷ trọng (%)", "Khuyến nghị tự động", "Ghi chú"]
            ]
            styled_p = (
                df_p.style
                .map(_color_signed, subset=["Lãi/Lỗ (VNĐ)", "% Lãi/Lỗ", "Hôm nay (VNĐ)"])
                .map(_color_status, subset=["Khuyến nghị tự động"])
                .format({
                    "Giá mua": "{:,.2f}", "KL": "{:,.0f}", "Giá hiện tại": "{:,.2f}",
                    "Lãi/Lỗ (VNĐ)": "{:+,.0f}", "% Lãi/Lỗ": "{:+.2f}%",
                    "Hôm nay (VNĐ)": "{:+,.0f}", "Tỷ trọng (%)": "{:.2f}%",
                })
            )
            st.dataframe(styled_p, width="stretch", hide_index=True, height=_auto_df_height(df_p))

        @st.fragment(run_every=5)
        def _portfolio_live_fragment():
            _render_portfolio_live_body()

        if LIVE_AUTO:
            _portfolio_live_fragment()
        else:
            _render_portfolio_live_body()

    # --- SUB-TAB 5.2: BACKTEST HYBRID ---
    with t_bt:
        col_cfg, col_res = st.columns([1.15, 2.85])
        with col_cfg:
            with st.expander("💼 1. Vốn & Quản Trị Danh Mục", expanded=True):
                bt_ind = st.selectbox("Vũ trụ cổ phiếu", [g for g in INDUSTRY_GROUPS if g != "Chỉ số"], key="bt_ind")
                bt_cap = st.number_input("Vốn ban đầu (VNĐ)", 10_000_000.0, 1e12, 1_000_000_000.0, step=100_000_000.0)
                d1, d2 = st.columns(2)
                bt_start = d1.date_input("Từ ngày", value=date(2024, 10, 17), key="bt_s")
                bt_end = d2.date_input("Đến ngày", value=TODAY_VN, key="bt_e")

                c_a, c_b = st.columns(2)
                bt_max_pos = c_a.number_input("Số mã max", 1, 20, 5)
                bt_max_sec = c_b.number_input("Max/Ngành", 1, 10, 2)
                bt_sl = c_a.number_input("Cắt lỗ (%)", 1.0, 30.0, 7.0, step=0.5)
                bt_ma_exit = c_b.number_input("MA chặn", 5, 200, 20)
                bt_fee = c_a.number_input("Phí+Thuế (%)", 0.0, 5.0, 0.15, step=0.05)
                bt_tplus = c_b.number_input("Chu kỳ T+", 0.0, 5.0, 2.5, step=0.5)

            with st.expander("🎯 2. Điểm Mua Minervini & VCP", expanded=True):
                bt_mode = st.selectbox(
                    "Chế độ điểm mua", [0, 1, 2], index=1,
                    format_func=lambda x: ["1. Chuẩn VCP Pivot (2T-4T)", "2. VCP hoặc Breakout 20P", "3. Mọi mã Stage 2 + Nổ Vol"][x],
                )
                m1, m2 = st.columns(2)
                bt_rs = m1.number_input("RS Min", 50, 99, 70, key="bt_rs")
                bt_pivot = m2.number_input("Biên Pivot (%)", 1.0, 15.0, 5.0, step=0.5)
                bt_vol_mult = m1.number_input("Hệ số Vol", 0.5, 5.0, 1.2, step=0.1)
                bt_min_vol = m2.number_input("Min Vol", 0, 10_000_000, 1_000_000, step=100_000)

                bt_fsec = st.checkbox("Chỉ mua Top ngành", value=False)
                bt_top_sec = st.number_input("Số ngành Top", 1, 20, 5, disabled=not bt_fsec)
                bt_use_tp = st.checkbox("Chốt lời chủ động", value=False)
                bt_tp = st.number_input("Mức chốt lời (%)", 5.0, 200.0, 25.0, step=1.0, disabled=not bt_use_tp)
                bt_pp = st.checkbox("Power Play (Giữ MA50 khi lãi ≥ 20%)", value=True)

            with st.expander("🛡️ 3. Lá Chắn Phân Phối & Đỉnh/Đáy", expanded=False):
                bt_dd_shield = st.checkbox("Bật Lá chắn Phân phối", value=True)
                s1, s2 = st.columns(2)
                bt_wdd = s1.number_input("Trọng số PP", 0.1, 5.0, 1.0, step=0.1)
                bt_wstall = s2.number_input("Stalling", 0.1, 5.0, 0.7, step=0.1)
                bt_dd_cancel = st.number_input("Xóa DD khi hồi (%)", 1.0, 20.0, 5.0, step=0.5)
                bt_climax = st.checkbox("Bán Đỉnh Hưng Phấn", value=True)
                bt_climax_th = st.number_input("Ngưỡng >MA200 (%)", 50.0, 99.0, 80.0, disabled=not bt_climax)
                bt_bot_fish = st.checkbox("Bắt Đáy Hoảng Loạn", value=True)
                p1, p2 = st.columns(2)
                bt_p200 = p1.number_input("MA200 < (%)", 5.0, 40.0, 20.0, disabled=not bt_bot_fish)
                bt_p52 = p2.number_input("Đáy 52T > (%)", 10.0, 90.0, 70.0, disabled=not bt_bot_fish)

            run_bt_btn = st.button("🚀 CHẠY BACKTEST HYBRID", type="primary", width="stretch")

        with col_res:
            if run_bt_btn:
                target_syms = get_symbols_by_industry(bt_ind, exclude_penny=(bt_ind == "Tất cả ngành"))
                all_hose = get_symbols_by_industry("Tất cả ngành", exclude_penny=True)
                fetch_syms = sorted(list(set(all_hose + target_syms + ["VNINDEX"])))

                prog = st.progress(0, text="Đang tải dữ liệu lịch sử toàn sàn từ SSI...")
                raw_bt = fetch_batch_ohlcv_ssi(
                    fetch_syms, bt_start - timedelta(days=450), bt_end, "D",
                    _progress_cb=lambda d, t: prog.progress(int(d / t * 100)),
                )
                prog.empty()

                params = {
                    "symbols": target_syms, "initial_capital": bt_cap,
                    "fee_rate": bt_fee / 100.0, "t_plus": bt_tplus,
                    "max_positions": int(bt_max_pos), "max_per_sector": int(bt_max_sec),
                    "stop_loss": bt_sl / 100.0, "ma_exit": int(bt_ma_exit),
                    "start_date": bt_start, "end_date": bt_end,
                    "entry_mode": int(bt_mode), "min_rs": int(bt_rs),
                    "max_pivot_pct": float(bt_pivot), "vol_mult": float(bt_vol_mult),
                    "min_vol": int(bt_min_vol), "filter_top_sectors": bt_fsec,
                    "top_sectors": int(bt_top_sec), "use_take_profit": bt_use_tp,
                    "take_profit": bt_tp / 100.0, "use_power_play": bt_pp,
                    "use_dd_shield": bt_dd_shield, "w_dd": float(bt_wdd), "w_stall": float(bt_wstall),
                    "dd_cancel_pct": float(bt_dd_cancel), "t_low": 3, "t_med": 5, "t_high": 7, "t_crit": 9,
                    "use_top_climax": bt_climax, "climax_breadth_thresh": float(bt_climax_th),
                    "use_bottom_fishing": bt_bot_fish, "panic_ma200_thresh": float(bt_p200), "panic_bot52_thresh": float(bt_p52),
                }
                with st.spinner("Đang chạy mô phỏng chiến lược Hybrid..."):
                    st.session_state["bt_result"] = run_hybrid_backtest(raw_bt, params)

            if "bt_result" in st.session_state and st.session_state["bt_result"]:
                res = st.session_state["bt_result"]
                s = res["stats"]
                eq = res["equity"]

                m1, m2, m3, m4, m5, m6 = st.columns(6)
                m1.metric("Lãi / Lỗ Ròng", f"{s['Profit'] / 1e6:+,.1f} Tr")
                m2.metric("% Tổng Lãi", f"{s['Profit %']:+.2f}%")
                m3.metric("CAGR / Năm", f"{s['CAGR']:+.2f}%")
                m4.metric("Tỷ Lệ Thắng", f"{s['Win Rate']:.1f}%", f"{s['Total Trades']} lệnh")
                m5.metric("Tài Sản Cuối", f"{s['Final'] / 1e9:,.2f} Tỷ")
                m6.metric("Max Drawdown", f"{s['Max DD']:.2f}%")

                x_eq = _trading_x_labels(eq.index, is_intraday=False)
                peak_nav = eq["NAV"].cummax()
                fig_eq = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.05)
                fig_eq.add_trace(go.Scatter(x=x_eq, y=peak_nav, name="Đỉnh NAV", line=dict(color="rgba(239,68,68,0.2)", width=0.5), showlegend=False), row=1, col=1)
                fig_eq.add_trace(go.Scatter(x=x_eq, y=eq["NAV"], name="Tổng NAV", fill="tonexty", fillcolor="rgba(239,68,68,0.12)", line=dict(color="#0284c7", width=2.2)), row=1, col=1)
                fig_eq.add_trace(go.Scatter(x=x_eq, y=eq["Exposure"], name="% Tỷ trọng CP", fill="tozeroy", fillcolor="rgba(16,185,129,0.22)", line=dict(color="#10b981", width=1.2)), row=2, col=1)
                fig_eq.add_trace(go.Scatter(x=x_eq, y=eq["Breadth200"], name="% > MA200", line=dict(color="#f59e0b", dash="dash", width=1.4)), row=2, col=1)

                panic_mask = eq["IsPanic"].values
                if panic_mask.any():
                    fig_eq.add_trace(
                        go.Scatter(x=[x_eq[i] for i, m in enumerate(panic_mask) if m], y=[10] * int(panic_mask.sum()), mode="markers", name="Đáy Hoảng Loạn", marker=dict(color="#ef4444", size=6)),
                        row=2, col=1,
                    )
                climax_mask = eq["IsClimax"].values
                if climax_mask.any():
                    fig_eq.add_trace(
                        go.Scatter(x=[x_eq[i] for i, m in enumerate(climax_mask) if m], y=[90] * int(climax_mask.sum()), mode="markers", name="Đỉnh Hưng Phấn", marker=dict(color="#8b5cf6", size=6)),
                        row=2, col=1,
                    )

                _style_chart(fig_eq, height=470, categorical_x=True)
                st.plotly_chart(fig_eq, width="stretch", key="bt_equity_chart")

                sub_t1, sub_t2, sub_t3 = st.tabs(["📝 Sổ Lệnh Chi Tiết", "✅ Deal Đã Đóng", "📊 Lịch Sử Tài Sản"])
                with sub_t1:
                    df_tr = res["trades"].iloc[::-1] if not res["trades"].empty else pd.DataFrame()
                    if not df_tr.empty:
                        st.dataframe(
                            df_tr.style
                            .map(_color_status, subset=["Lệnh"])
                            .map(_color_signed, subset=["Lãi/Lỗ"])
                            .format({"Giá": "{:,.2f}", "KL": "{:,.0f}", "Lãi/Lỗ": "{:+,.0f}"}),
                            width="stretch", hide_index=True, height=_auto_df_height(df_tr),
                        )
                with sub_t2:
                    df_cl = res["closed"].iloc[::-1] if not res["closed"].empty else pd.DataFrame()
                    if not df_cl.empty:
                        st.dataframe(
                            df_cl.style
                            .map(_color_signed, subset=["Lãi/Lỗ", "% Lãi/Lỗ"])
                            .format({"Giá Mua": "{:,.2f}", "Giá Bán": "{:,.2f}", "KL": "{:,.0f}", "Lãi/Lỗ": "{:+,.0f}", "% Lãi/Lỗ": "{:+.2f}%"}),
                            width="stretch", hide_index=True, height=_auto_df_height(df_cl),
                        )
                with sub_t3:
                    df_sn = res["snapshots"].iloc[::-1] if not res["snapshots"].empty else pd.DataFrame()
                    if not df_sn.empty:
                        st.dataframe(
                            df_sn.style.format({
                                "Tổng NAV": "{:,.0f}", "Tiền Mặt": "{:,.0f}",
                                "Tiền Chờ Về": "{:,.0f}", "Giá Trị CP": "{:,.0f}",
                                "Risk Score": "{:.1f}", "% > MA200": "{:.1f}%",
                            }),
                            width="stretch", hide_index=True, height=_auto_df_height(df_sn),
                        )

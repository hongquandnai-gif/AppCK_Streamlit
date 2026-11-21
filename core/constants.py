# ========================= app/constants.py =========================
from __future__ import annotations

# ============================================================
# =============== HẰNG SỐ / DỮ LIỆU NGÀNH HOSE ===============
# ============================================================

# --- Nhóm "Chỉ số" (để tab_historical chọn và vẽ) ---
INDEX_SYMBOLS = {
    "VNINDEX", "VN30", "HNX", "UPCOM", "VNMID", "VNSML", "VNSMALL",
    "HNXINDEX", "HNXUPCOMINDEX", "VN100", "VNALL",
}

# Mapping Ngành Gốc (Thủ công) - Giữ nguyên ngành kinh doanh thực tế của từng mã
BASE_INDUSTRIES_MAPPING = {
    # ------------------ Chỉ số ------------------
    "VNINDEX": "Chỉ số", "VN30": "Chỉ số", "HNX": "Chỉ số", "UPCOM": "Chỉ số",
    "VNMID": "Chỉ số", "VNSMALL": "Chỉ số", "VNSML": "Chỉ số",
    "VNALL": "Chỉ số", "VN100": "Chỉ số",

    # ------------------ Ngân hàng ------------------
    "VCB": "Ngân hàng", "BID": "Ngân hàng", "CTG": "Ngân hàng", "MBB": "Ngân hàng",
    "TCB": "Ngân hàng", "VPB": "Ngân hàng", "STB": "Ngân hàng", "HDB": "Ngân hàng",
    "ACB": "Ngân hàng", "LPB": "Ngân hàng", "EIB": "Ngân hàng", "OCB": "Ngân hàng",
    "SHB": "Ngân hàng", "TPB": "Ngân hàng", "VIB": "Ngân hàng", "MSB": "Ngân hàng",
    "SSB": "Ngân hàng", "NAB": "Ngân hàng", "VAB": "Ngân hàng", "BAB": "Ngân hàng",

    # ------------------ Chứng khoán ------------------
    "SSI": "Chứng khoán", "HCM": "Chứng khoán", "VND": "Chứng khoán", "VCI": "Chứng khoán",
    "FTS": "Chứng khoán", "VDS": "Chứng khoán", "CTS": "Chứng khoán", "BSI": "Chứng khoán",
    "VIX": "Chứng khoán", "ORS": "Chứng khoán", "AGR": "Chứng khoán", "TVS": "Chứng khoán",
    "MBS": "Chứng khoán", "SHS": "Chứng khoán", "APS": "Chứng khoán", "VIG": "Chứng khoán",
    "VCK": "Chứng khoán", "VPX": "Chứng khoán", "TCX": "Chứng khoán",

    # ------------------ Bất động sản ------------------
    "VIC": "Bất động sản", "VHM": "Bất động sản", "NVL": "Bất động sản", "PDR": "Bất động sản",
    "DXG": "Bất động sản", "KDH": "Bất động sản", "NLG": "Bất động sản", "DIG": "Bất động sản",
    "CEO": "Bất động sản", "HDG": "Bất động sản", "TCH": "Bất động sản", "KHG": "Bất động sản",
    "SCR": "Bất động sản", "HQC": "Bất động sản", "IJC": "Bất động sản", "CRE": "Bất động sản",
    "NHA": "Bất động sản", "HPX": "Bất động sản", "HDC": "Bất động sản", "NTL": "Bất động sản",
    "AGG": "Bất động sản", "DRH": "Bất động sản", "LDG": "Bất động sản", "QCG": "Bất động sản",

    # ------------------ Bất động sản KCN ------------------
    "KBC": "Bất động sản KCN", "IDC": "Bất động sản KCN", "SZC": "Bất động sản KCN",
    "ITA": "Bất động sản KCN", "GVR": "Bất động sản KCN", "PHR": "Bất động sản KCN",
    "DPR": "Bất động sản KCN", "LHG": "Bất động sản KCN", "BCM": "Bất động sản KCN",
    "VGC": "Bất động sản KCN", "TIP": "Bất động sản KCN", "SIP": "Bất động sản KCN",
    "DTD": "Bất động sản KCN", "GEL": "Bất động sản KCN", 

    # ------------------ Thép ------------------
    "HPG": "Thép", "HSG": "Thép", "NKG": "Thép", "TLH": "Thép",
    "POM": "Thép", "SMC": "Thép", "TVN": "Thép", "VGS": "Thép",

    # ------------------ Dầu khí ------------------
    "GAS": "Dầu khí", "PLX": "Dầu khí", "PVD": "Dầu khí", "PVS": "Dầu khí",
    "BSR": "Dầu khí", "OIL": "Dầu khí", "PVC": "Dầu khí",
    "PVB": "Dầu khí", "PVO": "Dầu khí",

    # ------------------ Năng lượng / Điện ------------------
    "POW": "Năng lượng", "REE": "Năng lượng", "GEG": "Năng lượng", "NT2": "Năng lượng",
    "PC1": "Năng lượng", "VSH": "Năng lượng", "TV2": "Năng lượng", "PPC": "Năng lượng",
    "QTP": "Năng lượng", "HND": "Năng lượng", "GEE": "Năng lượng",

    # ------------------ Bán lẻ ------------------
    "MWG": "Bán lẻ", "PNJ": "Bán lẻ", "FRT": "Bán lẻ", "DGW": "Bán lẻ",
    "PET": "Bán lẻ", "VRE": "Bán lẻ", "MSN": "Bán lẻ", "SAB": "Bán lẻ",
    "VNM": "Bán lẻ", "HAX": "Bán lẻ",

    # ------------------ Công nghệ / Viễn thông ------------------
    "FPT": "Công nghệ", "CMG": "Công nghệ", "ELC": "Công nghệ",
    "VTP": "Công nghệ", "CTR": "Công nghệ", "VGI": "Công nghệ", "FOX": "Công nghệ",
    "TTN": "Công nghệ",

    # ------------------ Hóa chất & Phân bón ------------------
    "DGC": "Hóa chất", "DCM": "Hóa chất", "DPM": "Hóa chất", "CSV": "Hóa chất",
    "LAS": "Hóa chất", "DDV": "Hóa chất", "BFC": "Hóa chất",

    # ------------------ Thủy sản ------------------
    "VHC": "Thủy sản", "ANV": "Thủy sản", "IDI": "Thủy sản", "FMC": "Thủy sản",
    "CMX": "Thủy sản", "ACL": "Thủy sản",

    # ------------------ Dệt may ------------------
    "TNG": "Dệt may", "TCM": "Dệt may", "GIL": "Dệt may", "MSH": "Dệt may",
    "STK": "Dệt may", "VGT": "Dệt may", "ADS": "Dệt may",

    # ------------------ Xây dựng & Đầu tư công ------------------
    "VCG": "Đầu tư công", "HHV": "Đầu tư công", "LCG": "Đầu tư công", "FCN": "Đầu tư công",
    "C4G": "Đầu tư công", "G36": "Đầu tư công", "CTD": "Xây dựng", "HBC": "Xây dựng",
    "HT1": "Xây dựng", "KSB": "Xây dựng", "BCC": "Xây dựng", "PLC": "Xây dựng",
    "CII": "Đầu tư công", "HUT": "Đầu tư công", "CTI": "Đầu tư công", "DPG": "Xây dựng",

    # ------------------ Vận tải & Cảng ------------------
    "GMD": "Vận tải & Cảng", "HAH": "Vận tải & Cảng", "VSC": "Vận tải & Cảng",
    "VOS": "Vận tải & Cảng", "GSP": "Vận tải & Cảng", "PVT": "Vận tải & Cảng",
    "HVN": "Hàng không", "VJC": "Hàng không",

    # ------------------ Nông nghiệp / Đường / Chăn nuôi ------------------
    "HAG": "Nông nghiệp", "HNG": "Nông nghiệp", "DBC": "Nông nghiệp", "BAF": "Nông nghiệp",
    "SBT": "Nông nghiệp", "LSS": "Nông nghiệp", "QNS": "Nông nghiệp", "SLS": "Nông nghiệp",
    "PAN": "Nông nghiệp", "TAR": "Nông nghiệp", "LTG": "Nông nghiệp", "ASM": "Nông nghiệp",
    "NAF": "Nông nghiệp",

    # ------------------ Khác ------------------
    "GEX": "Đa ngành", "AAA": "Nhựa", "APH": "Nhựa", "BMP": "Nhựa", "NTP": "Nhựa",
    "BVH": "Bảo hiểm", "MIG": "Bảo hiểm", "BMI": "Bảo hiểm",
    "TDM": "Nước", "BWE": "Nước",
    "DLG": "Đa ngành",
}

# =============================================================================
# ===================== PENNY (CẤU HÌNH TĨNH, KHÔNG DÙNG APP) =================
# =============================================================================
RESTRICTED_OR_BANNED_HOSE = set()

# Danh sách các mã Penny/Đầu cơ đặc trưng
HOSE_PENNY_FORCE_INCLUDE = {
    "YEG", "OGC", "LDG", "DRH", "HQC", "ITA", "DLG", "JVC", "TTF",
    "HNG", "AMD", "HAI", "TSC", "DAH", "TNI", "C69", "TNT",
    "HTN", "QCG", "C47", "CDC", "FIT", "SAM", "NAF", "FIR",
    "DC4", "HSL", "MHC", "TLD", "CRC", "APG", "CTF",
    "CCL", "TTA", "TNH", "NO1", "CLL", "NBB", "APH", "VIP",
    "SKG", "TVS", "TDP", "HCD", "TTH", "TVN", "DL1", "EVG"
}

HOSE_PENNY_ALWAYS_EXCLUDE = set()
HOSE_PENNY_CONVERT_FROM_EXISTING = set()

PENNY_SYMBOLS = (
    (HOSE_PENNY_FORCE_INCLUDE | HOSE_PENNY_CONVERT_FROM_EXISTING)
    - RESTRICTED_OR_BANNED_HOSE
    - HOSE_PENNY_ALWAYS_EXCLUDE
)

# Mapping chính dùng trong App:
# - Các mã đã có ngành gốc trong BASE_INDUSTRIES_MAPPING sẽ GIỮ NGUYÊN ngành gốc
#   để không bị mất mã khi lọc theo ngành (VD: ITA vẫn ở KCN, HNG ở Nông nghiệp).
# - Chỉ những mã Penny chưa có ngành gốc mới gán thẳng là "Penny".
HARDCODED_HOSE_INDUSTRIES_MAPPING = dict(BASE_INDUSTRIES_MAPPING)
for _sym in PENNY_SYMBOLS:
    if _sym not in HARDCODED_HOSE_INDUSTRIES_MAPPING:
        HARDCODED_HOSE_INDUSTRIES_MAPPING[_sym] = "Penny"


def is_penny_stock(symbol: str) -> bool:
    """Kiểm tra nhanh một mã có thuộc nhóm Penny hay không."""
    sym = str(symbol or "").strip().upper()
    return sym in PENNY_SYMBOLS or HARDCODED_HOSE_INDUSTRIES_MAPPING.get(sym) == "Penny"


def get_symbols_by_industry(selected_industry: str, exclude_penny: bool = False) -> list[str]:
    """Lấy danh sách mã chuẩn theo lựa chọn ComboBox ngành."""
    if selected_industry == "Chỉ số":
        return sorted([s for s, g in HARDCODED_HOSE_INDUSTRIES_MAPPING.items() if g == "Chỉ số"])
    if selected_industry == "Penny":
        return sorted(list(PENNY_SYMBOLS))
    if selected_industry == "Tất cả ngành":
        return sorted([
            s for s, g in HARDCODED_HOSE_INDUSTRIES_MAPPING.items()
            if g != "Chỉ số"
            and s not in RESTRICTED_OR_BANNED_HOSE
            and (not exclude_penny or not is_penny_stock(s))
        ])
    return sorted([
        s for s, g in HARDCODED_HOSE_INDUSTRIES_MAPPING.items()
        if g == selected_industry and s not in RESTRICTED_OR_BANNED_HOSE
    ])


# ============================================================
# ============== DANH SÁCH NGÀNH & DANH SÁCH MÃ ==============
# ============================================================

_all_groups = sorted(set(HARDCODED_HOSE_INDUSTRIES_MAPPING.values()))
if "Penny" in _all_groups:
    _all_groups.remove("Penny")
if "Chỉ số" in _all_groups:
    _all_groups.remove("Chỉ số")

INDUSTRY_GROUPS = (
    ["Tất cả ngành", "Chỉ số"]
    + _all_groups
    + ["Penny"]
)

ALL_SYMBOLS_FROM_MAP = sorted([
    s for s, g in HARDCODED_HOSE_INDUSTRIES_MAPPING.items()
    if s not in RESTRICTED_OR_BANNED_HOSE and g != "Chỉ số"
])

ALL_SYMBOLS_WITH_PLACEHOLDER = ["Chọn mã..."] + ALL_SYMBOLS_FROM_MAP

# ============================================================
# ================== CÁC HẰNG SỐ PHỤ TRỢ KHÁC ================
# ============================================================

MA_COLORS = {10: "#1f77b4", 20: "#ff7f0e", 50: "#2ca02c", 100: "#d62728", 200: "#9467bd"}
MA_WINDOWS = [10, 20, 50, 100, 200]

SYMBOL_TO_COMPANY: dict[str, str] = {
    # ------------------ Chỉ số ------------------
    "VNINDEX": "Chỉ số VN-Index (Sàn HOSE)",
    "VN30": "Chỉ số VN30 (Top 30 HOSE)",
    "HNX": "Chỉ số HNX-Index (Sàn HNX)",
    "HNXINDEX": "Chỉ số HNX-Index (Sàn HNX)",
    "UPCOM": "Chỉ số UPCoM-Index (Sàn UPCoM)",
    "HNXUPCOMINDEX": "Chỉ số UPCoM-Index (Sàn UPCoM)",
    "VNMID": "Chỉ số VNMidcap (Vốn hóa vừa)",
    "VNSMALL": "Chỉ số VNSmallcap (Vốn hóa nhỏ)",
    "VNSML": "Chỉ số VNSmallcap (Vốn hóa nhỏ)",
    "VN100": "Chỉ số VN100 (Top 100 HOSE)",
    "VNALL": "Chỉ số VNAllshare (Toàn sàn HOSE)",

    # ------------------ Ngân hàng ------------------
    "VCB": "Ngân hàng TMCP Ngoại thương Việt Nam (Vietcombank)",
    "BID": "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam (BIDV)",
    "CTG": "Ngân hàng TMCP Công Thương Việt Nam (VietinBank)",
    "MBB": "Ngân hàng TMCP Quân Đội (MBBank)",
    "TCB": "Ngân hàng TMCP Kỹ thương Việt Nam (Techcombank)",
    "VPB": "Ngân hàng TMCP Việt Nam Thịnh Vượng (VPBank)",
    "STB": "Ngân hàng TMCP Sài Gòn Thương Tín (Sacombank)",
    "HDB": "Ngân hàng TMCP Phát triển TP.HCM (HDBank)",
    "ACB": "Ngân hàng TMCP Á Châu (ACB)",
    "LPB": "Ngân hàng TMCP Lộc Phát Việt Nam (LPBank)",
    "EIB": "Ngân hàng TMCP Xuất Nhập Khẩu Việt Nam (Eximbank)",
    "OCB": "Ngân hàng TMCP Phương Đông (OCB)",
    "SHB": "Ngân hàng TMCP Sài Gòn - Hà Nội (SHB)",
    "TPB": "Ngân hàng TMCP Tiên Phong (TPBank)",
    "VIB": "Ngân hàng TMCP Quốc tế Việt Nam (VIB)",
    "MSB": "Ngân hàng TMCP Hàng Hải Việt Nam (MSB)",
    "SSB": "Ngân hàng TMCP Đông Nam Á (SeABank)",
    "NAB": "Ngân hàng TMCP Nam Á (Nam A Bank)",
    "VAB": "Ngân hàng TMCP Việt Á (VietABank)",
    "BAB": "Ngân hàng TMCP Bắc Á (Bac A Bank)",

    # ------------------ Chứng khoán ------------------
    "SSI": "CTCP Chứng khoán SSI",
    "HCM": "CTCP Chứng khoán Thành phố Hồ Chí Minh (HSC)",
    "VND": "CTCP Chứng khoán VNDIRECT",
    "VCI": "CTCP Chứng khoán Vietcap",
    "FTS": "CTCP Chứng khoán FPT",
    "VDS": "CTCP Chứng khoán Rồng Việt",
    "CTS": "CTCP Chứng khoán Ngân hàng Công Thương Việt Nam",
    "BSI": "CTCP Chứng khoán BIDV",
    "VIX": "CTCP Chứng khoán VIX",
    "ORS": "CTCP Chứng khoán Tiên Phong",
    "AGR": "CTCP Chứng khoán Agribank",
    "TVS": "CTCP Chứng khoán Thiên Việt",
    "MBS": "CTCP Chứng khoán MB",
    "SHS": "CTCP Chứng khoán Sài Gòn - Hà Nội",
    "APS": "CTCP Chứng khoán Châu Á - Thái Bình Dương",
    "VIG": "CTCP Chứng khoán Thương mại và Công nghiệp Việt Nam",
    "VCK": "CTCP Chứng khoán VPS",
    "VPX": "CTCP Chứng khoán VPBank",
    "TCX": "CTCP Chứng khoán Kỹ thương (TCBS)",

    # ------------------ Bất động sản ------------------
    "VIC": "Tập đoàn Vingroup - CTCP",
    "VHM": "CTCP Vinhomes",
    "NVL": "CTCP Tập đoàn Đầu tư Địa ốc No Va (Novaland)",
    "PDR": "CTCP Phát triển Bất động sản Phát Đạt",
    "DXG": "CTCP Tập đoàn Đất Xanh",
    "KDH": "CTCP Đầu tư và Kinh doanh Nhà Khang Điền",
    "NLG": "CTCP Đầu tư Nam Long",
    "DIG": "Tổng CTCP Đầu tư Phát triển Xây dựng (DIC Corp)",
    "CEO": "CTCP Tập đoàn C.E.O",
    "HDG": "CTCP Tập đoàn Hà Đô",
    "TCH": "CTCP Đầu tư Dịch vụ Tài chính Hoàng Huy",
    "KHG": "CTCP Tập đoàn Khải Hoàn Land",
    "SCR": "CTCP Địa ốc Sài Gòn Thương Tín (TTC Land)",
    "HQC": "CTCP Tư vấn - Thương mại - Dịch vụ Địa ốc Hoàng Quân",
    "IJC": "CTCP Phát triển Hạ tầng Kỹ thuật (Becamex IJC)",
    "CRE": "CTCP Bất động sản Thế Kỷ (Cen Land)",
    "NHA": "Tổng Công ty Đầu tư Phát triển Nhà và Đô thị Nam Hà Nội",
    "HPX": "CTCP Đầu tư Hải Phát",
    "HDC": "CTCP Phát triển Nhà Bà Rịa - Vũng Tàu (Hodeco)",
    "NTL": "CTCP Phát triển Đô thị Từ Liêm (Lideco)",
    "AGG": "CTCP Đầu tư và Phát triển Bất động sản An Gia",
    "DRH": "CTCP DRH Holdings",
    "LDG": "CTCP Đầu tư LDG",
    "QCG": "CTCP Quốc Cường Gia Lai",

    # ------------------ Bất động sản KCN ------------------
    "KBC": "Tổng Công ty Phát triển Đô thị Kinh Bắc - CTCP",
    "IDC": "Tổng Công ty IDICO - CTCP",
    "SZC": "CTCP Sonadezi Châu Đức",
    "ITA": "CTCP Đầu tư và Công nghiệp Tân Tạo",
    "GVR": "Tập đoàn Công nghiệp Cao su Việt Nam - CTCP",
    "PHR": "CTCP Cao su Phước Hòa",
    "DPR": "CTCP Cao su Đồng Phú",
    "LHG": "CTCP Long Hậu",
    "BCM": "Tổng Công ty Đầu tư và Phát triển Công nghiệp (Becamex IDC)",
    "VGC": "Tổng Công ty Viglacera - CTCP",
    "TIP": "CTCP Phát triển Khu Công nghiệp Tín Nghĩa",
    "SIP": "CTCP Đầu tư Sài Gòn VRG",
    "DTD": "CTCP Đầu tư Phát triển Thành Đạt",
    "GEL": "CTCP Hạ tầng GELEX",

    # ------------------ Thép ------------------
    "HPG": "CTCP Tập đoàn Hòa Phát",
    "HSG": "CTCP Tập đoàn Hoa Sen",
    "NKG": "CTCP Thép Nam Kim",
    "TLH": "CTCP Tập đoàn Thép Tiến Lên",
    "POM": "CTCP Thép Pomina",
    "SMC": "CTCP Đầu tư Thương mại SMC",
    "TVN": "Tổng Công ty Thép Việt Nam - CTCP (VNSTEEL)",
    "VGS": "CTCP Ống thép Việt Đức VG PIPE",

    # ------------------ Dầu khí ------------------
    "GAS": "Tổng Công ty Khí Việt Nam - CTCP (PV GAS)",
    "PLX": "Tập đoàn Xăng dầu Việt Nam (Petrolimex)",
    "PVD": "Tổng CTCP Khoan và Dịch vụ Khoan Dầu khí (PV Drilling)",
    "PVS": "Tổng CTCP Dịch vụ Kỹ thuật Dầu khí Việt Nam (PTSC)",
    "BSR": "CTCP Lọc hóa dầu Bình Sơn",
    "OIL": "Tổng Công ty Dầu Việt Nam - CTCP (PVOIL)",
    "PVT": "Tổng CTCP Vận tải Dầu khí (PVTrans)",
    "PVC": "Tổng Công ty Hóa chất và Dịch vụ Dầu khí (PVChem)",
    "PVB": "CTCP Bọc Ống Dầu khí Việt Nam (PVCoating)",
    "PVO": "CTCP Dầu nhờn PVOIL",

    # ------------------ Năng lượng / Điện ------------------
    "POW": "Tổng Công ty Điện lực Dầu khí Việt Nam - CTCP (PV Power)",
    "REE": "CTCP Cơ Điện Lạnh (REE)",
    "GEG": "CTCP Điện Gia Lai",
    "NT2": "CTCP Điện lực Dầu khí Nhơn Trạch 2",
    "PC1": "CTCP Tập đoàn PC1",
    "VSH": "CTCP Thủy điện Vĩnh Sơn - Sông Hinh",
    "TV2": "CTCP Tư vấn Xây dựng Điện 2 (PECC2)",
    "PPC": "CTCP Nhiệt điện Phả Lại",
    "QTP": "CTCP Nhiệt điện Quảng Ninh",
    "HND": "CTCP Nhiệt điện Hải Phòng",

    # ------------------ Bán lẻ ------------------
    "MWG": "CTCP Đầu tư Thế Giới Di Động",
    "PNJ": "CTCP Vàng bạc Đá quý Phú Nhuận",
    "FRT": "CTCP Bán lẻ Kỹ thuật số FPT (FPT Retail)",
    "DGW": "CTCP Thế Giới Số (Digiworld)",
    "PET": "Tổng CTCP Dịch vụ Tổng hợp Dầu khí (Petrosetco)",
    "VRE": "CTCP Vincom Retail",
    "MSN": "CTCP Tập đoàn Masan",
    "SAB": "Tổng CTCP Bia - Rượu - Nước giải khát Sài Gòn (Sabeco)",
    "VNM": "CTCP Sữa Việt Nam (Vinamilk)",
    "HAX": "CTCP Dịch vụ Ô tô Hàng Xanh (Haxaco)",

    # ------------------ Công nghệ / Viễn thông ------------------
    "FPT": "CTCP FPT",
    "CMG": "CTCP Tập đoàn Công nghệ CMC",
    "ELC": "CTCP Công nghệ - Viễn thông ELCOM",
    "VTP": "Tổng CTCP Bưu chính Viettel (Viettel Post)",
    "CTR": "Tổng CTCP Công trình Viettel (Viettel Construction)",
    "VGI": "Tổng CTCP Đầu tư Quốc tế Viettel (Viettel Global)",
    "FOX": "CTCP Viễn thông FPT (FPT Telecom)",
    "TTN": "CTCP Công nghệ và Truyền thông Việt Nam (VNTT)",

    # ------------------ Hóa chất & Phân bón ------------------
    "DGC": "CTCP Tập đoàn Hóa chất Đức Giang",
    "DCM": "CTCP Phân bón Dầu khí Cà Mau",
    "DPM": "Tổng Công ty Phân bón và Hóa chất Dầu khí (Đạm Phú Mỹ)",
    "CSV": "CTCP Hóa chất Cơ bản Miền Nam",
    "LAS": "CTCP Supe Phốt phát và Hóa chất Lâm Thao",
    "DDV": "CTCP DAP - VINACHEM",
    "BFC": "CTCP Phân bón Bình Điền",

    # ------------------ Thủy sản ------------------
    "VHC": "CTCP Vĩnh Hoàn",
    "ANV": "CTCP Nam Việt",
    "IDI": "CTCP Đầu tư và Phát triển Đa Quốc Gia I.D.I",
    "FMC": "CTCP Thực phẩm Sao Ta",
    "CMX": "CTCP Camimex Group",
    "ACL": "CTCP Xuất nhập khẩu Thủy sản Cửu Long An Giang",

    # ------------------ Dệt may ------------------
    "TNG": "CTCP Đầu tư và Thương mại TNG",
    "TCM": "CTCP Dệt may - Đầu tư - Thương mại Thành Công",
    "GIL": "CTCP Sản xuất Kinh doanh Xuất nhập khẩu Bình Thạnh (Gilimex)",
    "MSH": "CTCP May Sông Hồng",
    "STK": "CTCP Sợi Thế Kỷ",
    "VGT": "Tập đoàn Dệt May Việt Nam (Vinatex)",
    "ADS": "CTCP Damsan",

    # ------------------ Xây dựng & Đầu tư công ------------------
    "VCG": "Tổng CTCP Xuất nhập khẩu và Xây dựng Việt Nam (Vinaconex)",
    "HHV": "CTCP Đầu tư Hạ tầng Giao thông Đèo Cả",
    "LCG": "CTCP Lizen",
    "FCN": "CTCP FECON",
    "C4G": "CTCP Tập đoàn CIENCO4",
    "G36": "Tổng Công ty 36 - CTCP",
    "CTD": "CTCP Xây dựng Coteccons",
    "HBC": "CTCP Tập đoàn Xây dựng Hòa Bình",
    "HT1": "CTCP Xi măng Vicem Hà Tiên",
    "KSB": "CTCP Khoáng sản và Xây dựng Bình Dương",
    "BCC": "CTCP Xi măng Bỉm Sơn",
    "PLC": "Tổng Công ty Hóa dầu Petrolimex - CTCP",
    "CII": "CTCP Đầu tư Hạ tầng Kỹ thuật TP.HCM",
    "HUT": "CTCP Tasco",
    "CTI": "CTCP Đầu tư Phát triển Cường Thuận IDICO",

    # ------------------ Vận tải & Cảng / Hàng không ------------------
    "GMD": "CTCP Gemadept",
    "HAH": "CTCP Vận tải và Xếp dỡ Hải An",
    "VSC": "CTCP Container Việt Nam (Viconship)",
    "VOS": "CTCP Vận tải Biển Việt Nam (Vosco)",
    "GSP": "CTCP Vận tải Sản phẩm khí Quốc tế (Gas Shipping)",
    "HVN": "Tổng Công ty Hàng không Việt Nam - CTCP (Vietnam Airlines)",
    "VJC": "CTCP Hàng không Vietjet",

    # ------------------ Nông nghiệp / Đường / Chăn nuôi ------------------
    "HAG": "CTCP Hoàng Anh Gia Lai",
    "HNG": "CTCP Nông nghiệp Quốc tế Hoàng Anh Gia Lai",
    "DBC": "CTCP Tập đoàn Dabaco Việt Nam",
    "BAF": "CTCP Nông nghiệp BAF Việt Nam",
    "SBT": "CTCP Thành Thành Công - Biên Hòa (TTC AgriS)",
    "LSS": "CTCP Mía đường Lam Sơn",
    "QNS": "CTCP Đường Quảng Ngãi",
    "SLS": "CTCP Mía đường Sơn La",
    "PAN": "CTCP Tập đoàn PAN",
    "TAR": "CTCP Nông nghiệp Công nghệ cao Trung An",
    "LTG": "CTCP Tập đoàn Lộc Trời",
    "ASM": "CTCP Tập đoàn Sao Mai",
    "NAF": "CTCP Nafoods Group",

    # ------------------ Đa ngành / Nhựa / Bảo hiểm / Nước ------------------
    "GEX": "CTCP Tập đoàn GELEX",
    "AAA": "CTCP Nhựa An Phát Xanh",
    "APH": "CTCP Tập đoàn An Phát Holdings",
    "BMP": "CTCP Nhựa Bình Minh",
    "NTP": "CTCP Nhựa Thiếu niên Tiền Phong",
    "BVH": "Tập đoàn Bảo Việt",
    "MIG": "Tổng CTCP Bảo hiểm Quân Đội (MIC)",
    "BMI": "Tổng CTCP Bảo Minh",
    "TDM": "CTCP Nước Thủ Dầu Một",
    "BWE": "CTCP Nước - Môi trường Bình Dương (Biwase)",
    "DLG": "CTCP Tập đoàn Đức Long Gia Lai",

    # ------------------ Nhóm Penny bổ sung ------------------
    "YEG": "CTCP Tập đoàn Yeah1",
    "OGC": "CTCP Tập đoàn Đại Dương",
    "JVC": "CTCP Thiết bị Y tế Việt Nhật",
    "TTF": "CTCP Tập đoàn Kỹ nghệ Gỗ Trường Thành",
    "AMD": "CTCP Đầu tư và Khoáng sản FLC Stone",
    "HAI": "CTCP Nông dược H.A.I",
    "TSC": "CTCP Vật tư Kỹ thuật Nông nghiệp Cần Thơ",
    "DAH": "CTCP Tập đoàn Khách sạn Đông Á",
    "TNI": "CTCP Tập đoàn Thành Nam",
    "C69": "CTCP Xây dựng 1369",
    "TNT": "CTCP Tập đoàn TNT",
    "HTN": "CTCP Hưng Thịnh Incons",
    "C47": "CTCP Xây dựng 47",
    "CDC": "CTCP Chương Dương",
    "FIT": "CTCP Tập đoàn F.I.T",
    "SAM": "CTCP SAM Holdings",
    "FIR": "CTCP Địa ốc First Real",
    "DC4": "CTCP Xây dựng DIC Holdings",
    "HSL": "CTCP Đầu tư Phát triển Thực phẩm Hồng Hà",
    "MHC": "CTCP MHC",
    "TLD": "CTCP Đầu tư Xây dựng và Phát triển Đô thị Thăng Long",
    "CRC": "CTCP Create Capital Việt Nam",
    "APG": "CTCP Chứng khoán APG",
    "CTF": "CTCP City Auto",
    "CCL": "CTCP Đầu tư và Phát triển Đô thị Dầu khí Cửu Long",
    "TTA": "CTCP Đầu tư Xây dựng và Phát triển Trường Thành",
    "TNH": "CTCP Tập đoàn Bệnh viện TNH",
    "NO1": "CTCP Tập đoàn 911",
    "CLL": "CTCP Cảng Cát Lái",
    "NBB": "CTCP Đầu tư Năm Bảy Bảy",
    "VIP": "CTCP Vận tải Xăng dầu VIPCO",
    "SKG": "CTCP Tàu cao tốc Superdong - Kiên Giang",
    "TDP": "CTCP Thuận Đức",
    "HCD": "CTCP Đầu tư Sản xuất và Thương mại HCD",
    "TTH": "CTCP Thương mại và Dịch vụ Tiến Thành",
    "DL1": "CTCP Tập đoàn Alpha Seven",
    "EVG": "CTCP Tập đoàn EverLand",
}


def get_company_name(
    symbol: str,
    company_map: dict[str, str] | None = None,
    fallback: str = "",
) -> str:
    """Trả về tên công ty đồng bộ cho một mã chứng khoán / chỉ số."""
    sym = str(symbol or "").strip().upper()
    if not sym:
        return fallback
    if company_map:
        name = str(company_map.get(sym) or "").strip()
        if name and name.upper() != sym:
            return name
    name = str(SYMBOL_TO_COMPANY.get(sym) or "").strip()
    if name and name.upper() != sym:
        return name
    return fallback


def format_symbol_label(
    symbol: str,
    company_map: dict[str, str] | None = None,
) -> str:
    """Định dạng thống nhất 'MÃ — Tên công ty' cho selectbox và tiêu đề giữa các tab."""
    sym = str(symbol or "").strip().upper()
    comp = get_company_name(sym, company_map=company_map)
    return f"{sym} — {comp}" if comp else sym


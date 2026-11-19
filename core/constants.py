# ========================= app/constants.py =========================

# ============================================================
# =============== HẰNG SỐ / DỮ LIỆU NGÀNH HOSE ===============
# ============================================================

# --- Nhóm "Chỉ số" (để tab_historical chọn và vẽ) ---
INDEX_SYMBOLS = {"VNINDEX", "VN30", "HNX", "UPCOM", "VNMID", "VNSML"}

# Mapping Ngành Gốc (Thủ công) - Giữ nguyên ngành kinh doanh thực tế của từng mã
BASE_INDUSTRIES_MAPPING = {
    # ------------------ Chỉ số ------------------
    "VNINDEX": "Chỉ số", "VN30": "Chỉ số", "HNX": "Chỉ số", "UPCOM": "Chỉ số",
    "VNMID": "Chỉ số", "VNSML": "Chỉ số", "VNALL": "Chỉ số", "VN100": "Chỉ số",

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
    "BSR": "Dầu khí", "OIL": "Dầu khí", "PVT": "Dầu khí", "PVC": "Dầu khí",
    "PVB": "Dầu khí", "PVO": "Dầu khí",

    # ------------------ Năng lượng / Điện ------------------
    "POW": "Năng lượng", "REE": "Năng lượng", "GEG": "Năng lượng", "NT2": "Năng lượng",
    "PC1": "Năng lượng", "VSH": "Năng lượng", "TV2": "Năng lượng", "PPC": "Năng lượng",
    "QTP": "Năng lượng", "HND": "Năng lượng",

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
    "CII": "Đầu tư công", "HUT": "Đầu tư công", "CTI": "Đầu tư công",

    # ------------------ Vận tải & Cảng ------------------
    "GMD": "Vận tải & Cảng", "HAH": "Vận tải & Cảng", "VSC": "Vận tải & Cảng",
    "VOS": "Vận tải & Cảng", "GSP": "Vận tải & Cảng",
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
    return symbol in PENNY_SYMBOLS or HARDCODED_HOSE_INDUSTRIES_MAPPING.get(symbol) == "Penny"


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

SYMBOL_TO_COMPANY = {
    "FPT": "FPT Corporation",
    "MWG": "Mobile World Investment",
    "PNJ": "Phu Nhuan Jewelry",
    "HPG": "Hoa Phat Group",
    "VNM": "Vinamilk",
    "GAS": "PV Gas",
    "VCB": "Vietcombank",
    "VIC": "Vingroup",
    "VHM": "Vinhomes"
}

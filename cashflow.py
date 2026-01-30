import pandas as pd
import re

# --- Helper Functions ---
def normalize_text(text):
    if not isinstance(text, str): return ""
    # Loại bỏ ký tự đánh dấu đầu dòng (I.1, a, -...) và nội dung trong ngoặc đơn
    text = re.sub(r'^[A-Z0-9\.\s\-IXV]+[\.\s\-]+', '', text)
    text = re.sub(r'\s*\(.*\)', '', text)
    text = " ".join(text.split()).lower()
    return text

def safe_extract_value_and_round(df, chi_tieu_dao, column, unit_factor=1_000_000_000):
    try:
        targets = [chi_tieu_dao] if isinstance(chi_tieu_dao, str) else chi_tieu_dao
        targets_norm = [normalize_text(t) for t in targets]
        
        df_temp = df.copy()
        target_col = df.columns[0]
        df_temp["NORM"] = df_temp[target_col].apply(normalize_text)
        
        row = df_temp.loc[df_temp["NORM"].isin(targets_norm)]
        if row.empty:
            for t_norm in targets_norm:
                mask = df_temp["NORM"].str.contains(t_norm, na=False, regex=False)
                row = df_temp[mask]
                if not row.empty: break
        
        if row.empty: return 0
            
        value = row[column].iloc[0]
        if isinstance(value, str):
            value = value.replace(',', '').replace('(', '-').replace(')', '').strip()
            if value in ['-', '']: return 0
            try: value = float(value)
            except: return 0
                
        return float(value) if pd.notna(value) else 0
    except:
        return 0

def extract_flows_from_dataframe(df):
    """
    Tạo Sankey với Breakdown chi tiết theo format: Source [value] Target
    - Giá trị: số thập phân tỷ VND (VD: 222.438)
    - Mục chi tiết -> Activity node -> Pool -> Tiền cuối kỳ
    """
    try:
        if df.shape[1] < 2: return "// Error: DataFrame thiếu dữ liệu cột giá trị."
        col_val = df.columns[1] 
        
        # Format: Integer tỷ VND
        def to_b(val): return round(val / 1_000_000_000)

        # Trích xuất dữ liệu
        net_kd = safe_extract_value_and_round(df, "Lưu chuyển tiền thuần từ hoạt động kinh doanh", col_val)
        net_dt = safe_extract_value_and_round(df, "Lưu chuyển tiền thuần từ hoạt động đầu tư", col_val)
        net_tc = safe_extract_value_and_round(df, "Lưu chuyển tiền thuần từ hoạt động tài chính", col_val)
        
        items = {
            "dau_ky": safe_extract_value_and_round(df, "Tiền và tương đương tiền đầu kỳ", col_val),
            "cuoi_ky": safe_extract_value_and_round(df, "Tiền và tương đương tiền cuối kỳ", col_val),
            "ty_gia": safe_extract_value_and_round(df, "Ảnh hưởng của thay đổi tỷ giá", col_val),
            
            # Chi tiết Kinh doanh
            "ln_truoc_thue": safe_extract_value_and_round(df, "Lợi nhuận trước thuế", col_val),
            "ln_truoc_vld": safe_extract_value_and_round(df, "Lợi nhuận từ hoạt động kinh doanh trước thay đổi vốn lưu động", col_val),
            
            # Chi tiết Đầu tư
            "thu_thanh_ly": safe_extract_value_and_round(df, ["Tiền thu từ thanh lý", "nhượng bán TSCĐ"], col_val),
            "thu_hoi_cho_vay": safe_extract_value_and_round(df, ["Tiền thu hồi cho vay", "bán lại các công cụ nợ"], col_val),
            "thu_lai_vay_ct": safe_extract_value_and_round(df, ["Tiền thu lãi cho vay", "cổ tức và lợi nhuận được chia"], col_val),
            "chi_mua_tscd": safe_extract_value_and_round(df, ["Tiền chi để mua sắm", "xây dựng TSCĐ"], col_val),
            "chi_cho_vay": safe_extract_value_and_round(df, ["Tiền chi cho vay", "mua các công cụ nợ"], col_val),
            
            # Chi tiết Tài chính
            "thu_vay": safe_extract_value_and_round(df, "Tiền thu từ đi vay", col_val),
            "chi_tra_goc_vay": safe_extract_value_and_round(df, "Tiền trả nợ gốc vay", col_val),
            "chi_tra_co_tuc": safe_extract_value_and_round(df, ["Cổ tức, lợi nhuận đã trả", "Cổ tức đã trả"], col_val),
        }

        # Calculate Adjustment based on user formula: PBT - Net Operating Cash Flow
        # Adjustment = Items['ln_truoc_thue'] - net_kd
        items["adj_leakage"] = items["ln_truoc_thue"] - net_kd
        # Values for splitting PBT
        ln_thue = items["ln_truoc_thue"]

        # Ngưỡng 1%
        total_inflow = max(0, items["dau_ky"]) + max(0, net_kd) + max(0, net_dt) + max(0, net_tc)
        threshold = total_inflow * 0.01

        flows = []
        POOL = "Dòng tiền"
        ACT_KD = "Hoạt động kinh doanh"
        ACT_DT = "Hoạt động đầu tư"
        ACT_TC = "Hoạt động tài chính"
        ADJ_NODE = "Điều chỉnh (không phải dòng tiền)"

        # === TIỀN ĐẦU KỲ ===
        if items["dau_ky"] > threshold:
            flows.append(f"Tiền đầu kỳ [{to_b(items['dau_ky'])}] {POOL}")

        # === HOẠT ĐỘNG KINH DOANH ===
        # Use user formula: Adjustment = PBT - Net_KD
        # If Adj > 0: PBT splits into ACT_KD and ADJ_NODE (leakage)
        # If Adj < 0: PBT flows to ACT_KD, and ADJ_NODE also flows to ACT_KD (add-back)
        adj = items.get("adj_leakage", 0)

        if adj > threshold:
            # Profit is higher than cash flow: leakage to adjustments
            if net_kd > threshold:
                flows.append(f"Lợi nhuận trước thuế [{to_b(net_kd)}] {ACT_KD}")
            flows.append(f"Lợi nhuận trước thuế [{to_b(adj)}] {ADJ_NODE}")
        elif adj < -threshold:
            # Cash flow is higher than profit: adjustments add to cash
            if ln_thue > threshold:
                flows.append(f"Lợi nhuận trước thuế [{to_b(ln_thue)}] {ACT_KD}")
            flows.append(f"{ADJ_NODE} [{to_b(abs(adj))}] {ACT_KD}")
        else:
            # No significant adjustment
            if ln_thue > threshold:
                flows.append(f"Lợi nhuận trước thuế [{to_b(ln_thue)}] {ACT_KD}")
        
        # ACT_KD net -> POOL (hoặc ngược lại)
        if net_kd > threshold:
            flows.append(f"{ACT_KD} [{to_b(net_kd)}] {POOL}")
        elif net_kd < -threshold:
            flows.append(f"{POOL} [{to_b(abs(net_kd))}] {ACT_KD}")

        # === HOẠT ĐỘNG ĐẦU TƯ ===
        # Chi tiết inflow -> ACT_DT
        if items["thu_hoi_cho_vay"] > threshold:
            flows.append(f"Tiền thu hồi cho vay [{to_b(items['thu_hoi_cho_vay'])}] {ACT_DT}")
        if items["thu_lai_vay_ct"] > threshold:
            flows.append(f"Tiền thu lãi cho vay, cổ tức [{to_b(items['thu_lai_vay_ct'])}] {ACT_DT}")
        if items["thu_thanh_ly"] > threshold:
            flows.append(f"Thu thanh lý TSCĐ [{to_b(items['thu_thanh_ly'])}] {ACT_DT}")
        
        # ACT_DT net -> POOL (hoặc ngược lại)
        if net_dt > threshold:
            flows.append(f"{ACT_DT} [{to_b(net_dt)}] {POOL}")
        elif net_dt < -threshold:
            flows.append(f"{POOL} [{to_b(abs(net_dt))}] {ACT_DT}")
        
        # ACT_DT -> Chi tiết outflow
        if items["chi_mua_tscd"] < -threshold:
            flows.append(f"{ACT_DT} [{to_b(abs(items['chi_mua_tscd']))}] Mua sắm TSCĐ")
        if items["chi_cho_vay"] < -threshold:
            flows.append(f"{ACT_DT} [{to_b(abs(items['chi_cho_vay']))}] Cho vay / mua công cụ nợ")
        if items["thu_thanh_ly"] < -threshold:
            flows.append(f"{ACT_DT} [{to_b(abs(items['thu_thanh_ly']))}] Thu thanh lý TSCĐ")

        # === HOẠT ĐỘNG TÀI CHÍNH ===
        # Chi tiết inflow -> ACT_TC
        if items["thu_vay"] > threshold:
            flows.append(f"Tiền vay nhận được [{to_b(items['thu_vay'])}] {ACT_TC}")
        
        # ACT_TC net -> POOL (hoặc ngược lại)
        if net_tc > threshold:
            flows.append(f"{ACT_TC} [{to_b(net_tc)}] {POOL}")
        elif net_tc < -threshold:
            flows.append(f"{POOL} [{to_b(abs(net_tc))}] {ACT_TC}")
        
        # ACT_TC -> Chi tiết outflow
        if items["chi_tra_goc_vay"] < -threshold:
            flows.append(f"{ACT_TC} [{to_b(abs(items['chi_tra_goc_vay']))}] Trả nợ gốc")
        if items["chi_tra_co_tuc"] < -threshold:
            flows.append(f"{ACT_TC} [{to_b(abs(items['chi_tra_co_tuc']))}] Trả cổ tức")

        # === TIỀN CUỐI KỲ ===
        if items["cuoi_ky"] > threshold:
            flows.append(f"{POOL} [{to_b(items['cuoi_ky'])}] Tiền cuối kỳ")

        # === TỶ GIÁ ===
        if items["ty_gia"] > threshold:
            flows.append(f"Chênh lệch tỷ giá [{to_b(items['ty_gia'])}] {POOL}")
        elif items["ty_gia"] < -threshold:
            flows.append(f"{POOL} [{to_b(abs(items['ty_gia']))}] Chênh lệch tỷ giá")

        return '\n'.join(dict.fromkeys(flows))

    except Exception as e:
        return f"// Error: {str(e)}"

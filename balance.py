import pandas as pd
import os
import re

def normalize_text(text):
    """
    Chuẩn hóa text để so sánh: bỏ số thứ tự, bỏ khoảng trắng dư, viết thường
    Ví dụ: 'I. Tiền và các khoản tương đương tiền' -> 'tien va cac khoan tuong duong tien'
    """
    if not isinstance(text, str):
        return ""
    # Bỏ các tiền tố như "I. ", "1. ", "A. ", "   - "
    text = re.sub(r'^[A-Z0-9\.\s\-IXV]+[\.\s\-]+', '', text)
    # Bỏ dấu ngoặc đơn và nội dung bên trong (thường là đơn vị hoặc chú thích)
    text = re.sub(r'\s*\(.*\)', '', text)
    # Bỏ khoảng trắng dư và chuyển về chữ thường
    text = " ".join(text.split()).lower()
    return text

def safe_extract_value_and_round(df, chi_tieu_dao, column, unit_factor=1_000_000_000, is_cost=False):
    """
    Trích xuất và làm tròn giá trị từ DataFrame bằng cách so sánh chuẩn hóa.
    """
    try:
        if isinstance(chi_tieu_dao, str):
            targets = [chi_tieu_dao]
        else:
            targets = chi_tieu_dao
            
        targets_norm = [normalize_text(t) for t in targets]
        
        df_temp = df.copy()
        df_temp["NORM"] = df_temp["CHỈ TIÊU"].apply(normalize_text)
        
        row = df_temp.loc[df_temp["NORM"].isin(targets_norm)]
        
        if row.empty:
            for t_norm in targets_norm:
                # Find matches where target exists within the source line
                row = df_temp[df_temp["NORM"].str.contains(t_norm, na=False)]
                if not row.empty:
                    # If multiple matches, prefer the one most similar in length (best fit)
                    row = row.assign(len_diff=abs(row["NORM"].str.len() - len(t_norm))).sort_values("len_diff")
                    break
            
        if row.empty:
            return 0
            
        value = row[column].iloc[0]
        if pd.notna(value):
            # Giữ dấu để tính toán, chỉ lấy trị tuyệt đối khi hiển thị luồng
            val_rounded = round(value / unit_factor)
            return abs(val_rounded) if is_cost else val_rounded
        return 0
    except Exception as e:
        print(f"Lỗi khi trích xuất {chi_tieu_dao}: {e}")
        return 0

def extract_flows_from_dataframe(df):
    """
    Xử lý DataFrame và trả về chuỗi flows cho SankeyMATIC.
    df: pandas DataFrame với cột đầu tiên là tên chỉ tiêu
    """
    try:
        # Đổi tên và làm sạch
        if df.shape[1] < 2:
            return "// Error: DataFrame không đủ cột dữ liệu."

        # Cột 0 là tên chỉ tiêu, Cột 1 là số liệu (Kỳ này/Năm nay...)
        # Ta lấy tên cột đầu tiên gán lại cho dễ tham chiếu
        first_col_name = df.columns[0]
        df = df.rename(columns={first_col_name: "CHỈ TIÊU"})
        df["CHỈ TIÊU"] = df["CHỈ TIÊU"].astype(str).str.strip()
        df = df.dropna(how='all')

        # Lấy tên cột số liệu (cột thứ 2)
        first_numeric_column = df.columns[1]

        # --- EXTRACT DATA ---
        return _extract_flows_logic(df, first_numeric_column)
        
    except Exception as e:
        return f"// Error processing DataFrame: {str(e)}"

def _extract_flows_logic(df, first_numeric_column):
    """
    Core logic for extracting flows from DataFrame
    """
    # Tài sản (Dùng tên chính xác hoặc chuẩn hóa)
    tong_tai_san = safe_extract_value_and_round(df, ["TỔNG CỘNG TÀI SẢN", "TỔNG CỘNG TÀI SẢN (đồng)"], first_numeric_column)
    tai_san_ngan_han = safe_extract_value_and_round(df, ["TÀI SẢN NGẮN HẠN", "TÀI SẢN NGẮN HẠN (đồng)"], first_numeric_column)
    tai_san_dai_han = safe_extract_value_and_round(df, ["TÀI SẢN DÀI HẠN", "TÀI SẢN DÀI HẠN (đồng)"], first_numeric_column)
    
    # Chi tiết Tài sản ngắn hạn
    tien_va_cac_khoan_tuong_duong_tien = safe_extract_value_and_round(df, ["Tiền và các khoản tương đương tiền", "Tiền và tương đương tiền (đồng)"], first_numeric_column)
    dau_tu_tai_chinh_ngan_han = safe_extract_value_and_round(df, ["Đầu tư tài chính ngắn hạn", "Giá trị thuần đầu tư ngắn hạn (đồng)"], first_numeric_column)
    cac_khoan_phai_thu_ngan_han = safe_extract_value_and_round(df, ["Các khoản phải thu ngắn hạn", "Các khoản phải thu ngắn hạn (đồng)"], first_numeric_column)
    hang_ton_kho = safe_extract_value_and_round(df, ["Hàng tồn kho", "Hàng tồn kho ròng", "Hàng tồn kho, ròng (đồng)"], first_numeric_column)
    tai_san_ngan_han_khac = safe_extract_value_and_round(df, ["Tài sản ngắn hạn khác", "Tài sản lưu động khác"], first_numeric_column)

    # Chi tiết Tài sản dài hạn
    tai_san_co_dinh = safe_extract_value_and_round(df, ["Tài sản cố định", "Tài sản cố định (đồng)"], first_numeric_column)
    tai_san_dai_han_khac = safe_extract_value_and_round(df, ["Tài sản dài hạn khác", "Tài sản dài hạn khác (đồng)"], first_numeric_column)
    cac_khoan_phai_thu_dai_han = safe_extract_value_and_round(df, ["Các khoản phải thu dài hạn", "Phải thu dài hạn (đồng)"], first_numeric_column)
    bat_dong_san_dau_tu = safe_extract_value_and_round(df, ["Bất động sản đầu tư", "Giá trị ròng tài sản đầu tư"], first_numeric_column)
    tai_san_do_dang_dai_han = safe_extract_value_and_round(df, ["Tài sản dở dang dài hạn", "Chi phí xây dựng cơ bản dở dang", "Chi phí xây dựng cơ bản dở dang (đồng)"], first_numeric_column)
    dau_tu_tai_chinh_dai_han = safe_extract_value_and_round(df, ["Đầu tư tài chính dài hạn", "Đầu tư dài hạn (đồng)"], first_numeric_column)
    loi_the_thuong_mai = safe_extract_value_and_round(df, ["Lợi thế thương mại", "Lợi thế thương mại (đồng)"], first_numeric_column)

    # Nguồn vốn
    no_phai_tra = safe_extract_value_and_round(df, ["NỢ PHẢI TRẢ", "NỢ PHẢI TRẢ (đồng)"], first_numeric_column)
    von_chu_so_huu = safe_extract_value_and_round(df, ["VỐN CHỦ SỞ HỮU", "VỐN CHỦ SỞ HỮU (đồng)"], first_numeric_column)
    no_ngan_han = safe_extract_value_and_round(df, ["Nợ ngắn hạn", "Nợ ngắn hạn (đồng)"], first_numeric_column)
    no_dai_han = safe_extract_value_and_round(df, ["Nợ dài hạn", "Nợ dài hạn (đồng)"], first_numeric_column)

    # Chi tiết Nợ ngắn hạn
    phai_tra_nguoi_ban_ngan_han = safe_extract_value_and_round(df, ["Phải trả người bán ngắn hạn", "Phải trả người bán", "Phải trả cho người bán"], first_numeric_column)
    nguoi_mua_tra_tien_truoc_ngan_han = safe_extract_value_and_round(df, ["Người mua trả tiền trước ngắn hạn", "Người mua trả tiền trước ngắn hạn (đồng)"], first_numeric_column)
    thue_va_cac_khoan_phai_nop_nha_nuoc = safe_extract_value_and_round(df, ["Thuế và các khoản phải nộp Nhà nước"], first_numeric_column)
    phai_tra_nguoi_lao_dong = safe_extract_value_and_round(df, ["Phải trả người lao động"], first_numeric_column)
    chi_phi_phai_tra_ngan_han = safe_extract_value_and_round(df, ["Chi phí phải trả ngắn hạn"], first_numeric_column)
    phai_tra_khac_ngan_han = safe_extract_value_and_round(df, ["Phải trả ngắn hạn khác"], first_numeric_column)
    vay_va_no_thue_tai_chinh_ngan_han = safe_extract_value_and_round(df, ["Vay và nợ thuê tài chính ngắn hạn", "Vay và nợ thuê tài chính ngắn hạn (đồng)"], first_numeric_column)
    quy_khen_thuong_phuc_loi = safe_extract_value_and_round(df, ["Quỹ khen thưởng, phúc lợi", "Quỹ khen thưởng phúc lợi", "Quỹ khen thưởng và phúc lợi"], first_numeric_column)
    du_phong_phai_tra_ngan_han = safe_extract_value_and_round(df, ["Dự phòng phải trả ngắn hạn"], first_numeric_column)

    # Chi tiết Nợ dài hạn
    vay_va_no_thue_tai_chinh_dai_han = safe_extract_value_and_round(df, ["Vay và nợ thuê tài chính dài hạn", "Vay và nợ thuê tài chính dài hạn (đồng)"], first_numeric_column)
    phai_tra_nha_cung_cap_dai_han = safe_extract_value_and_round(df, ["Phải trả nhà cung cấp dài hạn", "Phải trả người bán dài hạn"], first_numeric_column)
    nguoi_mua_tra_tien_truoc_dai_han = safe_extract_value_and_round(df, ["Người mua trả tiền trước dài hạn"], first_numeric_column)
    chi_phi_phai_tra_dai_han = safe_extract_value_and_round(df, ["Chi phí phải trả dài hạn", "Chi phí phải trả dài hạn (đồng)"], first_numeric_column)
    phai_tra_noi_bo_von_kinh_doanh = safe_extract_value_and_round(df, ["Phải trả nội bộ về vốn kinh doanh"], first_numeric_column)
    phai_tra_noi_bo_dai_han = safe_extract_value_and_round(df, ["Phải trả nội bộ dài hạn"], first_numeric_column)
    doanh_thu_chua_thuc_hien_dai_han = safe_extract_value_and_round(df, ["Doanh thu chưa thực hiện dài hạn"], first_numeric_column)
    phai_tra_dai_han_khac = safe_extract_value_and_round(df, ["Phải trả dài hạn khác"], first_numeric_column)
    trai_phieu_chuyen_doi = safe_extract_value_and_round(df, ["Trái phiếu chuyển đổi"], first_numeric_column)
    co_phieu_uu_dai_no = safe_extract_value_and_round(df, ["Cổ phiếu ưu đãi (Nợ)"], first_numeric_column)
    thue_thu_nhap_hoan_lai_phai_tra = safe_extract_value_and_round(df, ["Thuế thu nhập hoãn lại phải trả"], first_numeric_column)
    du_phong_phai_tra_dai_han = safe_extract_value_and_round(df, ["Dự phòng phải trả dài hạn"], first_numeric_column)
    quy_phat_trien_khoa_hoc_cong_nghe = safe_extract_value_and_round(df, ["Quỹ phát triển khoa học và công nghệ"], first_numeric_column)
    du_phong_tro_cap_mat_viec = safe_extract_value_and_round(df, ["Dự phòng trợ cấp mất việc làm"], first_numeric_column)

    # Chi tiết Vốn chủ sở hữu
    von_gop_chu_so_huu = safe_extract_value_and_round(df, ["Vốn góp của chủ sở hữu", "Vốn góp của chủ sở hữu (đồng)"], first_numeric_column)
    thang_du_von_co_phan = safe_extract_value_and_round(df, ["Thặng dư vốn cổ phần"], first_numeric_column)
    quyen_chon_chuyen_doi_trai_phieu = safe_extract_value_and_round(df, ["Quyền chọn chuyển đổi trái phiếu"], first_numeric_column)
    von_khac_chu_so_huu = safe_extract_value_and_round(df, ["Vốn khác của chủ sở hữu"], first_numeric_column)
    co_phieu_quy = safe_extract_value_and_round(df, ["Cổ phiếu quỹ"], first_numeric_column)
    chenh_lech_danh_gia_lai_tai_san = safe_extract_value_and_round(df, ["Chênh lệch đánh giá lại tài sản"], first_numeric_column)
    chenh_lech_ty_gia_hoi_doai = safe_extract_value_and_round(df, ["Chênh lệch tỷ giá hối đoái"], first_numeric_column)
    quy_dau_tu_phat_trien = safe_extract_value_and_round(df, ["Quỹ đầu tư phát triển", "Quỹ đầu tư và phát triển (đồng)"], first_numeric_column)
    quy_ho_tro_sap_xep_doanh_nghiep = safe_extract_value_and_round(df, ["Quỹ hỗ trợ sắp xếp doanh nghiệp"], first_numeric_column)
    quy_khac_thuoc_von_chu_so_huu = safe_extract_value_and_round(df, ["Quỹ khác thuộc vốn chủ sở hữu"], first_numeric_column)
    loi_nhuan_chua_phan_phoi = safe_extract_value_and_round(df, ["Lợi nhuận sau thuế chưa phân phối", "Lãi chưa phân phối (đồng)"], first_numeric_column)
    loi_ich_co_dong_khong_kiem_soat = safe_extract_value_and_round(df, ["Lợi ích cổ đông không kiểm soát", "Lợi ích của cổ đông thiểu số", "LỢI ÍCH CỦA CỔ ĐÔNG THIỂU SỐ"], first_numeric_column)
    nguon_kinh_phi_va_quy_khac = safe_extract_value_and_round(df, ["Nguồn kinh phí và quỹ khác"], first_numeric_column)

    # BUILD FLOWS
    # Recalculate hierarchy totals to ensure visual balance
    calc_no_ngan_han = phai_tra_nguoi_ban_ngan_han + nguoi_mua_tra_tien_truoc_ngan_han + thue_va_cac_khoan_phai_nop_nha_nuoc + \
                        phai_tra_nguoi_lao_dong + chi_phi_phai_tra_ngan_han + phai_tra_khac_ngan_han + \
                        vay_va_no_thue_tai_chinh_ngan_han + quy_khen_thuong_phuc_loi + du_phong_phai_tra_ngan_han
    
    calc_no_dai_han = vay_va_no_thue_tai_chinh_dai_han + phai_tra_nha_cung_cap_dai_han + nguoi_mua_tra_tien_truoc_dai_han + \
                        chi_phi_phai_tra_dai_han + phai_tra_noi_bo_von_kinh_doanh + phai_tra_noi_bo_dai_han + \
                        doanh_thu_chua_thuc_hien_dai_han + phai_tra_dai_han_khac + trai_phieu_chuyen_doi + \
                        co_phieu_uu_dai_no + thue_thu_nhap_hoan_lai_phai_tra + du_phong_phai_tra_dai_han + \
                        quy_phat_trien_khoa_hoc_cong_nghe + du_phong_tro_cap_mat_viec
    
    calc_no_phai_tra = calc_no_ngan_han + calc_no_dai_han
    
    # Equity Groups - Use signed math for correctly handling treasury shares/losses
    group_1_val = von_gop_chu_so_huu + thang_du_von_co_phan + quyen_chon_chuyen_doi_trai_phieu + von_khac_chu_so_huu + co_phieu_quy
    group_2_val = quy_dau_tu_phat_trien + quy_ho_tro_sap_xep_doanh_nghiep + quy_khac_thuoc_von_chu_so_huu + nguon_kinh_phi_va_quy_khac
    group_3_val = loi_nhuan_chua_phan_phoi + loi_ich_co_dong_khong_kiem_soat + chenh_lech_danh_gia_lai_tai_san + chenh_lech_ty_gia_hoi_doai

    # We use the absolute sum of components for visual links into subgroups to avoid SankeyMATIC gaps
    # but the link from Bridge to Parent must be the sum of those absolute weights
    sum_group_1 = abs(von_gop_chu_so_huu) + abs(thang_du_von_co_phan) + abs(quyen_chon_chuyen_doi_trai_phieu) + abs(von_khac_chu_so_huu) + abs(co_phieu_quy)
    sum_group_2 = abs(quy_dau_tu_phat_trien) + abs(quy_ho_tro_sap_xep_doanh_nghiep) + abs(quy_khac_thuoc_von_chu_so_huu) + abs(nguon_kinh_phi_va_quy_khac)
    sum_group_3 = abs(loi_nhuan_chua_phan_phoi) + abs(loi_ich_co_dong_khong_kiem_soat) + abs(chenh_lech_danh_gia_lai_tai_san) + abs(chenh_lech_ty_gia_hoi_doai)

    # Calculate a plug to ensure Vốn chủ sở hữu flows sum up to abs(von_chu_so_huu) perfectly
    target_equity = abs(von_chu_so_huu)
    total_calc_equity = sum_group_1 + sum_group_2 + sum_group_3
    plug_equity = max(0, target_equity - total_calc_equity)
    
    # Re-adjust group 3 if there's a plug to avoid gaps in Sankey
    if plug_equity > (target_equity * 0.005):
        # We'll add it as a separate flow inside Lợi nhuận group later
        pass
    else:
        # For tiny differences, just ignore or absorb
        plug_equity = 0
    
    # Structure Tier 1: Asset Details -> Categories
    flows = [
        ("Tiền và các khoản tương đương tiền", abs(tien_va_cac_khoan_tuong_duong_tien), "Tài sản ngắn hạn"),
        ("Đầu tư tài chính ngắn hạn", abs(dau_tu_tai_chinh_ngan_han), "Tài sản ngắn hạn"),
        ("Các khoản phải thu ngắn hạn", abs(cac_khoan_phai_thu_ngan_han), "Tài sản ngắn hạn"),
        ("Hàng tồn kho", abs(hang_ton_kho), "Tài sản ngắn hạn"),
        ("Tài sản ngắn hạn khác", abs(tai_san_ngan_han_khac), "Tài sản ngắn hạn"),
        ("Tài sản cố định", abs(tai_san_co_dinh), "Tài sản dài hạn"),
        ("Tài sản dài hạn khác", abs(tai_san_dai_han_khac), "Tài sản dài hạn"),
        ("Các khoản phải thu dài hạn", abs(cac_khoan_phai_thu_dai_han), "Tài sản dài hạn"),
        ("Bất động sản đầu tư", abs(bat_dong_san_dau_tu), "Tài sản dài hạn"),
        ("Tài sản dở dang dài hạn", abs(tai_san_do_dang_dai_han), "Tài sản dài hạn"),
        ("Đầu tư tài chính dài hạn", abs(dau_tu_tai_chinh_dai_han), "Tài sản dài hạn"),
        ("Lợi thế thương mại", abs(loi_the_thuong_mai), "Tài sản dài hạn"),
        
        # Structure Tier 2: Categories -> Central Bridge (Tổng tài sản)
        ("Tài sản ngắn hạn", abs(tai_san_ngan_han), "Tổng tài sản"),
        ("Tài sản dài hạn", abs(tai_san_dai_han), "Tổng tài sản"),
        
        # Structure Tier 3: Central Bridge -> Liabilities/Equity
        ("Tổng tài sản", abs(no_phai_tra), "Nợ phải trả"),
        ("Tổng tài sản", target_equity, "Vốn chủ sở hữu"),

        # Structure Tier 4: Funding -> Sub-categories -> Details
        ("Nợ phải trả", abs(no_ngan_han), "Nợ ngắn hạn"),
        ("Nợ phải trả", abs(no_dai_han), "Nợ dài hạn"),
        
        ("Nợ ngắn hạn", abs(phai_tra_nguoi_ban_ngan_han), "Phải trả người bán ngắn hạn"),
        ("Nợ ngắn hạn", abs(nguoi_mua_tra_tien_truoc_ngan_han), "Người mua trả tiền trước ngắn hạn"),
        ("Nợ ngắn hạn", abs(thue_va_cac_khoan_phai_nop_nha_nuoc), "Thuế và các khoản phải nộp nhà nước"),
        ("Nợ ngắn hạn", abs(phai_tra_nguoi_lao_dong), "Phải trả người lao động"),
        ("Nợ ngắn hạn", abs(chi_phi_phai_tra_ngan_han), "Chi phí phải trả ngắn hạn"),
        ("Nợ ngắn hạn", abs(phai_tra_khac_ngan_han), "Phải trả ngắn hạn khác"),
        ("Nợ ngắn hạn", abs(vay_va_no_thue_tai_chinh_ngan_han), "Vay và nợ thuê tài chính ngắn hạn"),
        ("Nợ ngắn hạn", abs(quy_khen_thuong_phuc_loi), "Quỹ khen thưởng phúc lợi"),
        ("Nợ ngắn hạn", abs(du_phong_phai_tra_ngan_han), "Dự phòng phải trả ngắn hạn"),
        
        ("Nợ dài hạn", abs(vay_va_no_thue_tai_chinh_dai_han), "Vay và nợ thuê tài chính dài hạn"),
        ("Nợ dài hạn", abs(phai_tra_nha_cung_cap_dai_han), "Phải trả nhà cung cấp dài hạn"),
        ("Nợ dài hạn", abs(nguoi_mua_tra_tien_truoc_dai_han), "Người mua trả tiền trước dài hạn"),
        ("Nợ dài hạn", abs(chi_phi_phai_tra_dai_han), "Chi phí phải trả dài hạn"),
        ("Nợ dài hạn", abs(phai_tra_noi_bo_von_kinh_doanh), "Phải trả nội bộ về vốn kinh doanh"),
        ("Nợ dài hạn", abs(phai_tra_noi_bo_dai_han), "Phải trả nội bộ dài hạn"),
        ("Nợ dài hạn", abs(doanh_thu_chua_thuc_hien_dai_han), "Doanh thu chưa thực hiện dài hạn"),
        ("Nợ dài hạn", abs(phai_tra_dai_han_khac), "Phải trả dài hạn khác"),
        ("Nợ dài hạn", abs(trai_phieu_chuyen_doi), "Trái phiếu chuyển đổi"),
        ("Nợ dài hạn", abs(co_phieu_uu_dai_no), "Cổ phiếu ưu đãi (Nợ)"),
        ("Nợ dài hạn", abs(thue_thu_nhap_hoan_lai_phai_tra), "Thuế thu nhập hoãn lại phải trả"),
        ("Nợ dài hạn", abs(du_phong_phai_tra_dai_han), "Dự phòng phải trả dài hạn"),
        ("Nợ dài hạn", abs(quy_phat_trien_khoa_hoc_cong_nghe), "Quỹ phát triển khoa học và công nghệ"),
        ("Nợ dài hạn", abs(du_phong_tro_cap_mat_viec), "Dự phòng trợ cấp mất việc"),

        ("Vốn chủ sở hữu", sum_group_1, "Vốn và thặng dư"),
        ("Vốn chủ sở hữu", sum_group_2, "Các quỹ thuộc VCSH"),
        ("Vốn chủ sở hữu", sum_group_3 + plug_equity, "Lợi nhuận"),

        ("Vốn và thặng dư", abs(von_gop_chu_so_huu), "Vốn góp"),
        ("Vốn và thặng dư", abs(thang_du_von_co_phan), "Thặng dư vốn cổ phần"),
        ("Vốn và thặng dư", abs(quyen_chon_chuyen_doi_trai_phieu), "Quyền chọn chuyển đổi trái phiếu"),
        ("Vốn và thặng dư", abs(von_khac_chu_so_huu), "Vốn khác"),
        ("Vốn và thặng dư", abs(co_phieu_quy), "Cổ phiếu quỹ"),

        ("Các quỹ thuộc VCSH", abs(quy_dau_tu_phat_trien), "Quỹ đầu tư phát triển"),
        ("Các quỹ thuộc VCSH", abs(quy_ho_tro_sap_xep_doanh_nghiep), "Quỹ hỗ trợ sắp xếp doanh nghiệp"),
        ("Các quỹ thuộc VCSH", abs(quy_khac_thuoc_von_chu_so_huu), "Quỹ khác thuộc vốn chủ sở hữu"),
        ("Các quỹ thuộc VCSH", abs(nguon_kinh_phi_va_quy_khac), "Nguồn kinh phí và quỹ khác"),

        ("Lợi nhuận", abs(loi_nhuan_chua_phan_phoi), "Lợi nhuận sau thuế chưa phân phối"),
        ("Lợi nhuận", abs(loi_ich_co_dong_khong_kiem_soat), "Lợi ích cổ đông không kiểm soát"),
        ("Lợi nhuận", abs(chenh_lech_danh_gia_lai_tai_san), "Chênh lệch đánh giá lại tài sản"),
        ("Lợi nhuận", abs(chenh_lech_ty_gia_hoi_doai), "Chênh lệch tỷ giá hối đoái"),
    ]
    
    if plug_equity > 0:
        flows.append(("Lợi nhuận", plug_equity, "Thông tin khác"))

    # Threshold for displaying flows - 1% to filter out minor items
    THRESHOLD_PERCENT = 0.01
    threshold_value = tong_tai_san * THRESHOLD_PERCENT if tong_tai_san > 0 else 1
    
    output_lines = []
    for source, value, target in flows:
        if value >= threshold_value:
            output_lines.append(f"{source} [{value}] {target}")
    
    return "\n".join(output_lines)

def extract_flows_from_excel(file_input):
    """
    Xử lý file Excel và trả về chuỗi flows cho SankeyMATIC.
    file_input: Đường dẫn file (str) hoặc file object (bytes).
    """
    try:
        # Đọc file Excel
        # skiprows=4 như code cũ
        df = pd.read_excel(file_input, skiprows=4)
        
        # Use the DataFrame extraction function
        return extract_flows_from_dataframe(df)
        
    except Exception as e:
        return f"// Error processing file: {str(e)}"


# Giữ lại khả năng chạy script trực tiếp (nếu cần)
if __name__ == "__main__":
    file_path = os.path.join(os.path.abspath(''), 'BalanceSheet.xlsx')
    if os.path.exists(file_path):
        result = extract_flows_from_excel(file_path)
        print(result)
        # Ghi ra file
        with open('balance.txt', 'w', encoding='utf-8') as f:
            f.write(result)
    else:
        print("Không tìm thấy file BalanceSheet.xlsx")
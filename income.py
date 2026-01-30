import pandas as pd
import os
import re

def normalize_text(text):
    """
    Chuẩn hóa text để so sánh: bỏ số thứ tự, bỏ khoảng trắng dư, viết thường
    """
    if not isinstance(text, str):
        return ""
    # Bỏ các tiền tố như "I. ", "1. ", "A. ", "   - "
    text = re.sub(r'^[A-Z0-9\.\s\-IXV]+[\.\s\-]+', '', text)
    # Bỏ dấu ngoặc đơn và nội dung bên trong
    text = re.sub(r'\s*\(.*\)', '', text)
    # Bỏ khoảng trắng dư và chuyển về chữ thường
    text = " ".join(text.split()).lower()
    return text

def safe_extract_value_and_round(df, chi_tieu_dao, column, unit_factor=1_000_000_000, is_cost=False):
    """
    Trích xuất và làm tròn giá trị từ DataFrame bằng cách so sánh chuẩn hóa.
    chi_tieu_dao có thể là một chuỗi hoặc một list các chuỗi đồng nghĩa.
    """
    try:
        # Chuyển thành list nếu chỉ là một chuỗi
        if isinstance(chi_tieu_dao, str):
            targets = [chi_tieu_dao]
        else:
            targets = chi_tieu_dao
            
        targets_norm = [normalize_text(t) for t in targets]
        
        # Tạo bản chuẩn hóa của cột CHỈ TIÊU để tìm kiếm
        df_temp = df.copy()
        df_temp["NORM"] = df_temp["CHỈ TIÊU"].apply(normalize_text)
        
        # Tìm kiếm khớp chính xác
        row = df_temp.loc[df_temp["NORM"].isin(targets_norm)]
        
        if row.empty:
            # Thử tìm kiếm mờ
            for t_norm in targets_norm:
                row = df_temp[df_temp["NORM"].str.contains(t_norm, na=False)]
                if not row.empty:
                    break
        
        if row.empty:
            # Check ngược lại cho VCI (suffix đồng)
            for t_norm in targets_norm:
                mask = df_temp["NORM"].apply(lambda x: t_norm in x or x in t_norm)
                row = df_temp[mask]
                if not row.empty:
                    break
                    
        if row.empty:
            return 0
            
        value = row[column].iloc[0]
        if pd.notna(value):
            value = abs(value) if is_cost else value
            val_rounded = abs(round(value / unit_factor))
            return val_rounded
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

        first_col_name = df.columns[0]
        df = df.rename(columns={first_col_name: "CHỈ TIÊU"})
        df["CHỈ TIÊU"] = df["CHỈ TIÊU"].astype(str).str.strip()
        df = df.dropna(how='all')

        first_numeric_column = df.columns[1]

        # Trích xuất các giá trị (Sử dụng tên chuẩn trong vnstock v3.4.1)
        doanh_thu_thuan = safe_extract_value_and_round(df, ["Doanh thu thuần về bán hàng và cung cấp dịch vụ", "Doanh thu thuần", "Doanh thu"], first_numeric_column)
        gia_von_hang_ban = safe_extract_value_and_round(df, ["Giá vốn hàng bán"], first_numeric_column, is_cost=True)
        loi_nhuan_gop = safe_extract_value_and_round(df, ["Lợi nhuận gộp về bán hàng và cung cấp dịch vụ", "Lợi nhuận gộp", "Lãi gộp"], first_numeric_column)
        doanh_thu_tai_chinh = safe_extract_value_and_round(df, ["Doanh thu hoạt động tài chính", "Thu nhập tài chính", "Thu nhập lãi"], first_numeric_column)
        chi_phi_tai_chinh = safe_extract_value_and_round(df, ["Chi phí tài chính", "Chi phí tiền lãi vay"], first_numeric_column, is_cost=True)
        chi_phi_ban_hang = safe_extract_value_and_round(df, ["Chi phí bán hàng"], first_numeric_column, is_cost=True)
        chi_phi_quan_ly = safe_extract_value_and_round(df, ["Chi phí quản lý doanh nghiệp", "Chi phí quản lý DN"], first_numeric_column, is_cost=True)
        loi_nhuan = safe_extract_value_and_round(df, ["Lợi nhuận thuần từ hoạt động kinh doanh", "Lãi/Lỗ từ hoạt động kinh doanh", "LN trước thuế"], first_numeric_column)
        loi_nhuan_khac = safe_extract_value_and_round(df, ["Lợi nhuận khác"], first_numeric_column)
        thue_thu_nhap = safe_extract_value_and_round(df, ["Chi phí thuế TNDN hiện hành"], first_numeric_column, is_cost=True)
        loi_nhuan_sau_thue = safe_extract_value_and_round(df, ["Lợi nhuận sau thuế thu nhập doanh nghiệp", "Lợi nhuận thuần", "Lợi nhuận sau thuế của Cổ đông công ty mẹ (đồng)"], first_numeric_column)

        # Định nghĩa các luồng cho SankeyMATIC
        flows = [
            ("Doanh thu thuần", gia_von_hang_ban, "Giá vốn hàng bán"),
            ("Doanh thu thuần", loi_nhuan_gop, "Lợi nhuận gộp"),
            ("Lợi nhuận gộp", loi_nhuan_gop, "Lợi nhuận HĐKD"),
            ("Doanh thu tài chính", doanh_thu_tai_chinh, "Lợi nhuận HĐKD"),
            ("Lợi nhuận HĐKD", chi_phi_tai_chinh, "Chi phí tài chính"),
            ("Lợi nhuận HĐKD", chi_phi_ban_hang, "Chi phí bán hàng"),
            ("Lợi nhuận HĐKD", chi_phi_quan_ly, "Chi phí quản lý"),
            ("Lợi nhuận HĐKD", loi_nhuan, "Lợi nhuận trước thuế"),
            ("Lợi nhuận khác", loi_nhuan_khac, "Lợi nhuận trước thuế"),
            ("Lợi nhuận trước thuế", thue_thu_nhap, "Thuế thu nhập"),
            ("Lợi nhuận trước thuế", loi_nhuan_sau_thue, "Lợi nhuận sau thuế")
        ]

        # Tính ngưỡng là 0.1% của lợi nhuận sau thuế để bắt được nhiều chi tiết hơn
        THRESHOLD_PERCENT = 0.001
        threshold_value = loi_nhuan_sau_thue * THRESHOLD_PERCENT if loi_nhuan_sau_thue > 0 else 1

        # Xuất dữ liệu
        output_lines = []
        for source, value, target in flows:
            if value >= threshold_value:
                output_lines.append(f'{source} [{value}] {target}')
        
        return '\n'.join(output_lines)
        
    except Exception as e:
        return f"// Error processing DataFrame: {str(e)}"

def extract_flows_from_excel(file_input):
    """
    Xử lý file Excel và trả về chuỗi flows cho SankeyMATIC.
    file_input: Đường dẫn file (str) hoặc file object (bytes).
    """
    try:
        df = pd.read_excel(file_input, skiprows=4)
        return extract_flows_from_dataframe(df)
    except Exception as e:
        return f"// Error processing file: {str(e)}"

# Giữ lại khả năng chạy script trực tiếp (nếu cần)
if __name__ == "__main__":
    file_path = os.path.join(os.path.abspath(''), 'income.xlsx')
    if os.path.exists(file_path):
        result = extract_flows_from_excel(file_path)
        print(result)
        with open('income.txt', 'w', encoding='utf-8') as f:
            f.write(result)
    else:
        print("Không tìm thấy file income.xlsx")
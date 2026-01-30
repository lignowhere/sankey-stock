# Financial Sankey Diagram Web Application

Ứng dụng web tạo biểu đồ Sankey từ báo cáo tài chính của các công ty niêm yết trên thị trường chứng khoán Việt Nam.

## Tính năng

- 📊 Tạo biểu đồ Sankey cho 3 loại báo cáo tài chính:
  - Bảng Cân Đối Kế Toán (Balance Sheet)
  - Báo Cáo Kết Quả Kinh Doanh (Income Statement)
  - Báo Cáo Lưu Chuyển Tiền Tệ (Cash Flow)
- 🚀 **Tính năng mới**: Tạo cùng lúc cả 3 báo cáo trong một lần yêu cầu để có cái nhìn tổng quát.

- 🎯 Lấy dữ liệu trực tiếp từ thư viện `vnstock`
- 📅 Hỗ trợ xem theo Quý (Q1-Q4) hoặc cả Năm
- 🎨 Giao diện hiện đại với dark mode và hiệu ứng glassmorphism
- 📱 Responsive design, tương thích mọi thiết bị
- 💾 Tải xuống dữ liệu Sankey dạng text

## Cài đặt

1. Cài đặt các thư viện cần thiết:

```bash
pip install -r requirements.txt
```

2. Chạy ứng dụng:

```bash
python app.py
```

3. Mở trình duyệt và truy cập:

```
http://localhost:5000
```

## Sử dụng

1. Nhập mã cổ phiếu (VD: VNM, VCB, HPG...)
2. Chọn loại báo cáo tài chính
3. Chọn kỳ báo cáo (Quý I-IV hoặc Cả năm)
4. Nhập năm
5. Nhấn "Tạo Biểu Đồ"

## Cấu trúc thư mục

```
sankey-matic/
├── app.py                 # Flask application
├── data_fetcher.py        # vnstock integration
├── balance.py             # Balance sheet processor
├── cashflow.py            # Cash flow processor
├── income.py              # Income statement processor
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Main HTML template
└── static/
    ├── css/
    │   └── style.css     # Styles
    └── js/
        └── app.js        # Frontend logic
```

## Công nghệ sử dụng

- **Backend**: Flask, vnstock, pandas
- **Frontend**: HTML5, CSS3, JavaScript
- **Visualization**: D3.js, d3-sankey
- **Design**: Modern dark mode with glassmorphism

## Lưu ý

- Dữ liệu được lấy từ thư viện `vnstock`, phụ thuộc vào tính khả dụng của dữ liệu từ nguồn
- Một số mã cổ phiếu có thể không có đầy đủ dữ liệu cho tất cả các kỳ
- Biểu đồ chỉ hiển thị các luồng có giá trị >= 1% tổng giá trị để tránh quá tải thông tin

## Tác giả

Created with ❤️ for Vietnamese stock market analysis

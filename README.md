# auto-adjust-volumes-project
A small Python project to auto adjust the volume of output speaker when change/connect.

# 🔊 VolumeSetter - Trình điều chỉnh âm lượng mặc định (Bản thử nghiệm)
## Một Project nho nhỏ vibe coding bằng ngôn ngữ lập trình Python
### 📌 Tác giả: NamNguyen
### 🤖 Công cụ hỗ trợ: Microsoft Copilot, Claude.
### Code được thiết kế để chạy trên môi trường Windows. Nên biên dịch thành .exe, không khuyến khích phiên dịch trực tiếp file .py.

### 💬 Đôi lời:

    Có một thằng bạn của mình rất hay quên chỉnh âm lượng khi chuyển đổi giữa các thiết bị âm thanh (tai nghe, loa ngoài...), điều đó thật phiền phức và đôi khi gây ảnh hưởng đến thính giác nếu lỡ để quá to.

    Mình đã thử tìm kiếm phần mềm để giải quyết vấn đề này nhưng không thấy phần mềm nào phù hợp. Vì vậy, mình quyết định tự viết một phần mềm nhỏ để giúp bạn ấy và những người khác gặp vấn đề tương tự.

    Phần mềm này được phát triển để giải quyết vấn đề âm lượng không đồng nhất khi sử dụng nhiều thiết bị âm thanh khác nhau trên Windows. Mục tiêu là giúp người dùng dễ dàng quản lý và tự động áp dụng mức âm lượng yêu thích cho từng thiết bị khi chúng được kết nối lại.


### 🛠️ Chức năng:
- Tự động đặt âm lượng cho từng thiết bị âm thanh khi kết nối lại
- Lưu cấu hình theo ngữ cảnh (default, music, video...) (mới để ở đó chứ chưa có tính năng này)
- Khởi động cùng Windows

### 🧰📍 Code chưa tối ưu hoàn toàn, có thể còn bị lag hoặc bug
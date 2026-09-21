# Odoo Access Visualizer — Tài liệu tiếng Việt

Odoo Access Visualizer là module Odoo 19 giúp quản trị viên hiểu hệ thống
phân quyền phức tạp bằng snapshot, bản đồ quan hệ và các cảnh báo có bằng
chứng. Module chỉ đọc dữ liệu phân quyền; không tự ý sửa user, group, ACL,
record rule hoặc menu.

## Module giải quyết vấn đề gì?

Khi Odoo có nhiều module, việc trả lời các câu hỏi sau thường rất khó:

- User nào đang thuộc những group nào?
- Group quản lý có kế thừa thêm quyền nào không?
- Model nào có nhiều ACL chồng chéo?
- Record rule global và group rule có tương tác đáng chú ý không?
- Một finding cụ thể xuất phát từ những record nào?

Module biến các quan hệ này thành dữ liệu có thể lọc và điều tra theo từng
bước, thay vì hiển thị toàn bộ graph dày đặc ngay khi mở màn hình.

## Tính năng chính

### Màn hình Overview

Overview là điểm bắt đầu dành cho admin:

- Số lượng object phân quyền đã lập bản đồ.
- Số lượng quan hệ giữa các object.
- Số finding cần xem xét.
- Số finding Critical có bằng chứng cấu trúc mạnh.
- Permission path: Category → Privilege → User → Group → Model → ACL → Rule → Menu.
- Ba câu hỏi khởi đầu: có rủi ro gì, ai đang kế thừa quyền, ai có thể tác động vào model.

### Explore map

Graph chỉ mở sau khi admin chọn layer hoặc nhập từ khóa tìm kiếm. Cách này
giúp bản đồ dễ đọc và tránh làm trình duyệt phải layout hàng nghìn node cùng
lúc.

- Chọn Users, Security groups, Models, Access controls, Record rules hoặc Menus.
- Tìm theo tên hiển thị, technical name hoặc module.
- Chọn node để xem source record, module và metadata.
- Graph nhỏ dùng Cytoscape.js; graph lớn dùng SVG fallback an toàn.
- Response graph giới hạn 250 node và 1.500 edge.

### Findings

Finding được phân loại theo mức độ:

- **Critical:** bằng chứng xác định hoặc cấu trúc đủ mạnh.
- **Warning:** pattern đáng chú ý cần admin kiểm tra thêm.

Các nhóm finding hiện có:

- Implied group overlap.
- ACL redundancy và ACL complexity.
- Duplicate record rule.
- Potential interaction giữa global rule và group rule.

ACL được phân tích theo cơ chế cộng dồn quyền của Odoo. Record rule động
không bị gọi là conflict chắc chắn nếu analyzer không thể chứng minh an toàn.

## Cài đặt

### Cài qua giao diện Odoo

1. Đặt thư mục `odoo_access_visualizer` vào một thư mục thuộc `addons_path`.
2. Khởi động lại Odoo.
3. Bật developer mode nếu cần và cập nhật danh sách Apps.
4. Cài **Odoo Access Visualizer**.
5. Mở **Settings → Access Visualizer → Security Map**.

Module chỉ phụ thuộc `base` và `web`.

### Cài qua command line

```bash
python odoo-bin -c odoo.conf -d ten_database -i odoo_access_visualizer
```

Khi module đã cài:

```bash
python odoo-bin -c odoo.conf -d ten_database -u odoo_access_visualizer
```

## Bật giao diện tiếng Việt

Bản dịch nằm tại:

```text
i18n/vi.po
```

Thực hiện trong Odoo:

1. Vào **Settings → Translations → Languages**.
2. Cài ngôn ngữ **Vietnamese / Tiếng Việt** nếu database chưa có.
3. Mở menu người dùng ở góc phải và chọn ngôn ngữ **Tiếng Việt**.
4. Tải lại trang Access Visualizer.

Odoo dùng English làm fallback nếu một chuỗi chưa có bản dịch tiếng Việt.
Không sửa trực tiếp chuỗi tiếng Việt trong XML/JS; hãy cập nhật `i18n/vi.po`
để bản dịch vẫn đúng chuẩn Odoo và có thể tái sử dụng cho các ngôn ngữ khác.

## Quy trình scan

Nút **Run rescan** đưa một yêu cầu vào queue. Scheduled action của Odoo xử
lý scan ở background với các trạng thái:

```text
queued → running → completed
                 ↘ failed
```

Snapshot thành công gần nhất vẫn được giữ lại khi scan mới thất bại. Module
giữ từ 5 đến 10 snapshot thành công; mặc định là 5.

## Bảo mật

- Chỉ thành viên `base.group_system` được truy cập module.
- Scanner dùng quyền đọc có kiểm soát để xem metadata phân quyền.
- Không có thao tác sửa trực tiếp security source records trong MVP.
- Không đưa database dump, credential, local config hoặc security map thực tế
  vào repository public.

## Hiệu năng và giới hạn

Kiến trúc dùng snapshot để tránh quét toàn bộ security configuration trong web
request. Mục tiêu benchmark của project là khoảng 1.000 groups và 20.000
ACL/rule records với scan nền dưới 5 phút.

Graph lớn cần được điều tra theo layer hoặc search. Đây là chủ ý thiết kế:
hiển thị ít hơn nhưng hiểu được quan hệ quan trọng tốt hơn việc đổ hàng nghìn
node lên màn hình.

MVP chưa bao gồm:

- Phân tích Field-level security.
- Inline editing hoặc remediation.
- Export CSV/PDF/PNG.
- So sánh snapshot.
- Audit log.
- Incremental realtime scan.

## Phát triển và kiểm thử

Chạy test module trên Odoo 19:

```bash
python odoo-bin -c odoo.conf -d ten_database \
  -u odoo_access_visualizer --test-enable --stop-after-init
```

Kiểm tra bổ sung:

```bash
python -m compileall -q .
node --check static/src/js/access_visualizer_action.js
node --check static/src/js/graph_renderer.js
```

Pull request nên bao gồm test regression nếu thay đổi scanner, analyzer,
permission semantics hoặc lifecycle snapshot.

## License

Module phát hành theo MIT License. Cytoscape.js được vendored kèm license và
notice tương ứng trong `static/lib/`.


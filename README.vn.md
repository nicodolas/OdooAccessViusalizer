# Odoo Access Visualizer 19.0.1.2.0: Tài liệu tiếng Việt

Odoo Access Visualizer 19.0.1.1.0 là module Odoo 19 giúp quản trị viên hiểu hệ thống
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
- Mỗi lần hiển thị graph giới hạn 96 node và 800 edge để nhãn không chồng lấn; hãy lọc sâu hơn khi cần xem đầy đủ.
- Khi chọn layer hoặc object, graph mở rộng tối đa hai hop để hiển thị access path liên quan.
- Khi chọn node, detail panel hiển thị CRUD hiệu lực, ảnh hưởng của record rule và đường dẫn bằng chứng.
- Tab Compare hiển thị object, relationship và finding được thêm, xóa hoặc thay đổi giữa hai snapshot.

### Quy trình điều tra

1. Bắt đầu tại **Overview** và chọn câu hỏi hoặc finding.
2. Mở **Explore map**, chọn layer, module, từ khóa hoặc quyền cần kiểm tra.
3. Các record phù hợp trở thành seed của graph. Bản đồ mở rộng tối đa hai hop
   để giữ đường User, Group, ACL, Model và Record Rule liên quan.
4. Chọn một node để highlight access path và xem CRUD hiệu lực, ảnh hưởng của
   record rule cùng metadata nguồn.

Bộ lọc permission áp dụng cho nhóm seed Models, hỗ trợ các câu hỏi như “model
nào có ACL cấp quyền ghi?”. Module không sửa dữ liệu phân quyền Odoo.

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

## Giao diện tiếng Việt

Bản dịch nằm tại:

```text
i18n/vi.po
```

Khi ngôn ngữ **Vietnamese / Tiếng Việt** đã được bật trong Odoo, chọn
**Tiếng Việt** tại menu người dùng ở góc phải rồi tải lại Access Visualizer.

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

Graph lớn cần được điều tra theo layer, module, permission hoặc search. Đây là chủ ý thiết kế:
hiển thị ít hơn nhưng hiểu được quan hệ quan trọng tốt hơn việc đổ hàng nghìn
node lên màn hình.

Mỗi response graph giới hạn 96 node và 800 edge; khi vượt giới hạn, UI hiển thị
số node đang render trên tổng số node phù hợp.

MVP chưa bao gồm:

- Phân tích Field-level security.
- Inline editing hoặc remediation.
- Export CSV/PDF/PNG.
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
permission semantics hoặc lifecycle snapshot. CI cũng chạy kiểm tra syntax và
test Odoo trên database tạm.

## License

Module phát hành theo MIT License. Cytoscape.js được vendored kèm license và
notice tương ứng trong `static/lib/`.


# Odoo Access Visualizer

## English

Odoo Access Visualizer is a read-only Odoo 19 administration tool for
understanding users, security groups, implied groups, access control lists,
record rules, privileges, models and menus.

It creates background snapshots so a large security configuration is not
scanned inside a browser request. Findings are evidence-backed and separated
into deterministic and heuristic warnings.

The interactive map uses vendored Cytoscape.js 3.34.3 with a dependency-free
SVG fallback when the graph asset is unavailable.

### MVP scope

- Odoo 19.0 only.
- Access limited to Settings administrators (`base.group_system`).
- Read-only: the module never edits users, groups, ACLs, rules or menus.
- Background scan and manual rescan.
- Latest successful snapshot remains visible while a new scan runs.
- Five to ten successful snapshots are retained; the default is five.
- Field-level security analysis, inline remediation, exports, compare and
  real-time incremental scanning are not part of the MVP.

### Installation

1. Add the directory containing `odoo_access_visualizer` to `addons_path`.
2. Restart Odoo and update the Apps list.
3. Install **Odoo Access Visualizer**.
4. Open **Settings → Access Visualizer → Security Map**.

The module depends only on `base` and `web`.

### Scan lifecycle

The **Rescan** button queues a snapshot. Odoo's scheduled action processes one
queued scan in the background. The UI displays queued, running, completed and
failed states. A failed scan never replaces the latest successful snapshot.

### Findings

- **Implied group overlap:** cross-module groups share a transitive implied
  group.
- **ACL redundancy/complexity:** duplicate, structurally redundant or unusually
  dense ACL layouts. ACL permissions are additive in Odoo.
- **Record rule interaction:** duplicate rules and potential global/group rule
  interactions. Dynamic domains are warnings, not proofs of contradiction.

Every finding includes affected nodes and evidence. Use the standard Odoo
security screens to remediate a finding.

### Performance target

The documented benchmark targets approximately 1,000 groups and 20,000
ACL/rule records, with a background scan under five minutes and a filtered
snapshot view under five seconds. The browser render budget is bounded to
2,000 nodes and 10,000 edges per response; refine filters when the budget is
exceeded.

Focused map exploration expands up to three permission hops so a model or
group selection can reveal related ACLs, record rules, groups, users, menus
and privileges while keeping the rendered result bounded.

### Development

Run the Odoo test suite with the module installed and the repository's local
configuration. The test suite covers scanner normalization, security semantics,
snapshot lifecycle, access control, retention, graph query limits and UI
states.

Do not commit local database credentials, database dumps, private configuration
or workspace-specific files to the public module repository.

## Tiếng Việt

Odoo Access Visualizer là module quản trị chỉ-đọc dành cho Odoo 19, giúp trực
quan hóa user, security group, implied group, ACL, record rule, privilege,
model và menu.

Module tạo snapshot ở background để không quét toàn bộ phân quyền trong một
web request. Các cảnh báo luôn kèm bằng chứng và được phân biệt giữa kết quả
xác định chắc chắn với heuristic warning.

Bản đồ tương tác dùng Cytoscape.js 3.34.3 được vendored trong module và có
SVG fallback không phụ thuộc thư viện khi asset graph không tải được.

### Phạm vi MVP

- Chỉ hỗ trợ Odoo 19.0.
- Chỉ Settings Administrator (`base.group_system`) được truy cập.
- Chỉ-đọc: module không sửa user, group, ACL, rule hoặc menu.
- Scan nền và rescan thủ công.
- Snapshot thành công gần nhất vẫn được hiển thị khi scan mới đang chạy.
- Lưu từ năm đến mười snapshot thành công; mặc định là năm.
- Chưa bao gồm phân tích Field-level, sửa trực tiếp, export, compare và scan
  incremental realtime.

### Cài đặt

1. Thêm thư mục chứa `odoo_access_visualizer` vào `addons_path`.
2. Restart Odoo và cập nhật danh sách Apps.
3. Cài module **Odoo Access Visualizer**.
4. Mở **Settings → Access Visualizer → Security Map**.

Module chỉ phụ thuộc `base` và `web`.

### Vòng đời scan

Nút **Rescan** đưa một snapshot vào queue. Scheduled action của Odoo xử lý
scan ở background. UI hiển thị các trạng thái queued, running, completed và
failed. Nếu scan lỗi, snapshot thành công trước đó vẫn được giữ nguyên.

### Phân tích conflict

- **Implied group overlap:** các group khác module cùng kế thừa một group
  chung.
- **ACL redundancy/complexity:** ACL trùng, ACL có thể dư thừa hoặc cấu trúc
  ACL quá dày. ACL trong Odoo có quyền cộng dồn.
- **Record rule interaction:** rule trùng và tương tác có khả năng mâu thuẫn
  giữa global/group rule. Domain động chỉ là warning, không phải kết luận chắc
  chắn.

Mỗi finding có node liên quan và bằng chứng. Khi xử lý, dùng các màn hình phân
  quyền chuẩn của Odoo.

### Mục tiêu hiệu năng

Benchmark mục tiêu khoảng 1.000 group và 20.000 ACL/rule: scan nền dưới năm
phút và mở snapshot đã lọc dưới năm giây. Mỗi response graph giới hạn 2.000
node và 10.000 edge; hãy lọc hẹp hơn khi vượt giới hạn.

### Phát triển

Chạy test Odoo với module đã cài và cấu hình local của repository. Test bao phủ
scanner, semantics phân quyền, snapshot lifecycle, security, retention, giới
hạn graph query và UI state.

Không commit credential database, database dump, config riêng tư hoặc file
chỉ dùng cho workspace vào repository public.

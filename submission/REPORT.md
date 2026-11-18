# Báo cáo Day 09 — Nguyễn Thị Hồng Hạnh, 2A202603272

## 1. Kết luận trước
Pipeline kết luận: **HOLD**.
- Số lượng ảnh đầu vào: 224 ảnh thô (`data/raw/images`). Bước 1 (nhận dữ liệu) đã loại bỏ 31 ảnh (gồm 3 BAD_SIZE, 2 CORRUPT_IMAGE, 8 DUP_IMAGE_EXACT, 7 DUP_IMAGE_NEAR, 11 LEAK_TEST). Số ảnh hợp lệ đi tiếp vào các vòng kiểm tra nhãn là 193 ảnh.
- Số lượng ảnh xuất ra dataset: 193 ảnh (`submission/export/clean_v1`), đây là bản nháp thử nghiệm phục vụ kiểm tra/đo lường, chưa được phát hành chính thức do quyết định là HOLD.
- Lý do chính: Cửa chặn ghi nhận `n_errors = 0` (không còn lỗi bắt buộc sau khi autofix xử lý 35 lỗi cú pháp/hình học và 6 ảnh thiếu nhãn được người duyệt bổ sung). Tuy nhiên, còn 53/193 ảnh chứa cảnh báo chưa được duyệt (tỉ lệ 27.46%), đạt và vượt ngưỡng Hold 10.00% theo quy định dự án, do ngân sách người duyệt mô phỏng bị giới hạn ở 80 ảnh (không đủ bao quát toàn bộ 138 ảnh trong hàng đợi).

## 2. Lỗi và phân việc
Tổng hợp các lỗi phát hiện từ `02_error_list_v1` (gom theo mã lỗi có mặt trong lô):

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `BAD_CLASS_ID` | 6 dòng | Máy | Lỗi cú pháp: ID lớp ngoài phạm vi 0..3 (-1, 4, 7, 93), máy xóa dòng lỗi (`drop_line`) an toàn mà không ảnh hưởng box khác. |
| `BAD_CLASS_NAME` | 2 dòng | Máy | Lỗi tên lớp: 'Person' và 'Bus' trong `data.yaml` được máy chuẩn hóa thành 'person' và 'bus' theo quy tắc ánh xạ `class_aliases`. |
| `BAD_FORMAT` | 3 dòng | Máy | Lỗi cú pháp: Giá trị nan/inf hoặc thiếu cột tọa độ, máy xóa dòng hỏng (`drop_line`). |
| `BAD_SIZE` | 3 ảnh | Máy | Lỗi kích thước: Cạnh ngắn < 250 px, không đạt độ phân giải tối thiểu của guideline, máy loại bỏ ở Bước 1. |
| `BOX_OUT_OF_IMAGE` | 8 dòng | Máy | Lỗi hình học: Box tràn biên ảnh nhưng tâm nằm trong ảnh, máy tự động xén viền (`clip_box`) về đoạn [0, 1]. |
| `BOX_ZERO` | 4 dòng | Máy | Lỗi hình học: Chiều rộng hoặc chiều cao bằng 0 (không có diện tích), máy xóa dòng lỗi (`drop_line`). |
| `CORRUPT_IMAGE` | 2 ảnh | Máy | Lỗi file: Ảnh bị hỏng không đọc được byte (UnidentifiedImageError, OSError), máy loại bỏ ở Bước 1. |
| `DUP_BOX` | 7 dòng | Máy | Lỗi trùng lắp: Hai box cùng lớp trùng nhau (IoU >= 0.9), máy giữ box đầu và xóa box trùng sau (`drop_line`). |
| `DUP_IMAGE_EXACT` | 8 ảnh | Máy | Lỗi trùng lặp: Trùng khớp md5 từng byte với ảnh đã quét, máy giữ ảnh đầu và loại bỏ ảnh sau ở Bước 1. |
| `DUP_IMAGE_NEAR` | 7 ảnh | Máy | Lỗi trùng lặp: Khoảng cách pHash <= 16 (ảnh resize hoặc nén lại), máy giữ ảnh đầu và loại bỏ ảnh sau ở Bước 1. |
| `LEAK_TEST` | 11 ảnh | Máy | Lỗi rò rỉ: Trùng md5 hoặc pHash với ảnh trong kho `test` hoặc `gold_val`, máy loại bỏ ở Bước 1 để tránh thiên lệch đánh giá. |
| `MISSING_LABEL_FILE` | 6 ảnh | Người | Lỗi thiếu nhãn: Ảnh thiếu file nhãn hoàn toàn; máy không thể tự bịa đặt nhãn mà phải chuyển người gán (`needs_label`). |
| `BOX_HUGE` | 3 dòng | Người | Cảnh báo: Box chiếm > 95% diện tích ảnh; cần người xác nhận là vật thể góc rộng cận cảnh hay người gán kéo nhầm. |
| `BOX_TINY` | 6 dòng | Người | Cảnh báo: Cạnh ngắn < 12 px; guideline quy định không gán vật quá nhỏ, cần người cân nhắc giữ hay xóa. |
| `CLASS_RARE` | 4 dòng | Người | Cảnh báo: Mất cân bằng dữ liệu mức dataset; cần người/quản lý dữ liệu bổ sung thêm ảnh cho các lớp hiếm. |
| `EMPTY_LABEL` | 11 ảnh | Người | Cảnh báo: File nhãn rỗng (0 byte); cần người xác nhận là ảnh nền không có vật thể hay người gán bỏ sót. |
| `POSSIBLE_FALSE_POS` | 28 dòng | Người | Cảnh báo: Nhãn có box nhưng model checker không phát hiện; cần người kiểm tra xem nhãn ảo hay model sót. |
| `POSSIBLE_LOOSE_BOX` | 43 dòng | Người | Cảnh báo: Cùng lớp nhưng IoU giữa nhãn và model < 0.5; cần người chỉnh lại viền bounding box cho khít vật thể. |
| `POSSIBLE_MISSING` | 148 dòng | Người | Cảnh báo: Model checker tìm thấy vật thể tin cậy nhưng nhãn không có; cần người duyệt xác định có bỏ sót không. |
| `POSSIBLE_WRONG_CLASS` | 20 dòng | Người | Cảnh báo ngữ nghĩa: IoU >= 0.5 nhưng nhãn và model bất đồng về tên lớp (như car vs truck); bắt buộc người quyết định. |

Hàng đợi duyệt (`05_review_queue.csv`):
- Cách xếp ảnh đầu hàng: Hàm `build_queue` tính điểm ưu tiên dựa trên trọng số lỗi nhân với độ tin cậy của model: `score = sum(w[code] * (1 + conf))` và cộng dồn điểm phạt từ các sửa đổi tự động (`FIXED_DROP_LINE` +2, `FIXED_CLIP_BOX` +1, `NEEDS_LABEL` +10). Nhờ vậy, ảnh đầu hàng là những ảnh tích tụ nhiều lỗi nghiêm trọng nhất:
  + Ảnh `#1` (`img_0160`, ưu tiên 35.692) và `#2` (`img_0127`, ưu tiên 22.753) đều chứa hàng loạt lỗi ngữ nghĩa phức tạp (`POSSIBLE_MISSING`, `POSSIBLE_WRONG_CLASS`, `POSSIBLE_LOOSE_BOX`).
  + Toàn bộ 6 ảnh thiếu file nhãn (`NEEDS_LABEL`) đều nhận điểm cơ sở 10.0 và được đưa lên top đầu hàng đợi (từ vị trí 18 đến 23) để đảm bảo người duyệt không bỏ sót.
- Với ngân sách 80 ảnh, người xem được bao nhiêu lỗi ngữ nghĩa?
  Trong tổng số 138 ảnh của hàng đợi, ngân sách 80 ảnh (58% hàng đợi) đã giúp người duyệt:
  + Gán nhãn thành công 100% (6/6) ảnh thiếu file nhãn (`NEEDS_LABEL`).
  + Giải quyết 10/20 lỗi `POSSIBLE_WRONG_CLASS` (giảm 50%, từ 20 xuống 10).
  + Giải quyết 58/148 lỗi `POSSIBLE_MISSING` (giảm 39.2%, từ 148 xuống 90).
  + Giải quyết 11/43 lỗi `POSSIBLE_LOOSE_BOX` (giảm 25.6%, từ 43 xuống 32).
  + Giải quyết 4/28 lỗi `POSSIBLE_FALSE_POS` (giảm 14.3%, từ 28 xuống 24).
  + Xác minh 4/11 ảnh `EMPTY_LABEL` (giảm từ 11 xuống 7).
  Tổng cộng người duyệt đã xử lý dứt điểm 87 lỗi ngữ nghĩa phức tạp trên 80 ảnh có độ rủi ro cao nhất.

## 3. Calibration (2 ngưỡng)
| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | 16 | DUP_IMAGE_NEAR: 1.00 / 0.50 → 1.00 / 0.83 (F1: 0.67 → 0.91) | Tăng từ 2 lên 16 giúp Recall phát hiện ảnh trùng gần đúng tăng mạnh từ 50% lên 83.3% trong khi Precision vẫn duy trì 100% trên tập calib. Ngưỡng 20 làm giảm Recall về 0.50 do gộp sai, nên 16 là điểm tối ưu. |
| `second_opinion.conf` | 0.25 | 0.25 | POSSIBLE_MISSING: 0.50 / 1.00; POSSIBLE_LOOSE_BOX: 0.29 / 0.40 | Ưu tiên **Recall** tối đa cho khâu QC: ở conf 0.25, Recall của missing đạt 100% và loose box đạt 40%. Nếu nâng lên 0.50, Precision của missing tăng nhẹ (0.50 → 0.57) nhưng Recall của loose box sụt giảm một nửa (0.40 → 0.20, bỏ sót 80% box lỏng). Ta chấp nhận cảnh báo thừa để người duyệt thay vì để lọt dữ liệu bẩn. |

Chỗ calibration có thể đánh lừa:
- Tập calib chỉ có 39 ảnh được chèn lỗi nhân tạo có chủ đích nên phân bố không phản ánh hết độ phức tạp của dữ liệu thực tế 224 ảnh.
- Bằng chứng từ dữ liệu:
  Với `phash_dist = 16`, trên tập calib pHash đạt Precision tuyệt đối 1.00. Nhưng khi áp dụng vào tập thực tế `data/raw`, bước 1 loại 7 ảnh `DUP_IMAGE_NEAR`, trong đó các cặp `img_0011` - `img_0008`, `img_0084` - `img_0074`, `img_0177` - `img_0113` đều chạm khoảng cách pHash đúng bằng 16 (ngưỡng biên). Khi đối chiếu trực quan, các cặp ảnh này có thể chỉ có cùng tông màu nền hoặc bố cục chung chứ không phải cùng một cảnh chụp. Do tập calib thiếu các cặp âm tính khó (hard negative pairs), calibration cho ta ảo giác rằng ngưỡng 16 an toàn 100% không bắt nhầm.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
(a) Chứng minh gate chặn đúng:
- Khi chạy pipeline với ngân sách người duyệt bằng 0:
  `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb`
- Kết quả thu được: Do không có người duyệt gán nhãn, 6 ảnh thiếu nhãn (`MISSING_LABEL_FILE`) chuyển thành `needs_label` vẫn còn nguyên ở vòng 3 (`n_errors = 6`).
- Cửa chặn `gate` phát hiện lỗi bắt buộc còn tồn tại, đưa ra kết luận **REWORK** ("Còn 6 lỗi bắt buộc; cần sửa trước khi phát hành."), trả về mã thoát **20**.
- Pipeline chặn hoàn toàn việc xuất dữ liệu: thư mục `work/exp_nb` không được tạo ra (`exported: null` trong `work/rep_nb/08_summary.json`). Điều này chứng minh cửa chặn hoạt động nghiêm ngặt, không cho phép dữ liệu lỗi lọt vào tập xuất.

(b) Các điểm mù của pipeline (kèm bằng chứng):
1. **Box lỏng nhẹ hoặc lệch viền**: Cấu hình cố định `iou_loose: 0.5`. Nếu bounding box của annotator bị rộng hoặc lệch viền nhưng IoU với checker model vẫn đạt từ 0.5 trở lên (ví dụ IoU = 0.6–0.7), pipeline coi đây là match bình thường và hoàn toàn không cảnh báo `POSSIBLE_LOOSE_BOX`.
2. **Lỗi nhầm lẫn ngữ nghĩa mà cả model checker cũng đoán sai**: Check `second_opinion` dựa vào sự bất đồng giữa nhãn và model yolo26l. Nếu cả annotator lẫn checker model cùng nhận diện nhầm một vật thể (ví dụ một chiếc xe tải nhỏ/SUV bị cả hai gán thành `car` thay vì `truck`), hai bên đồng thuận (`agreement`) và lỗi ngữ nghĩa này bị bỏ qua hoàn toàn.
3. **Ảnh trùng bị cắt cúp sâu hoặc xoay góc**: pHash chỉ phát hiện được ảnh resize tỷ lệ hoặc nén ảnh. Nếu ảnh trùng bị crop > 20% hoặc xoay góc, khoảng cách pHash sẽ vượt xa 16 và bước 1 không thể nhận biết.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Chưa chạy trên Colab/GPU do bài làm tập trung hoàn thiện pipeline kiểm định chất lượng dữ liệu, sửa lỗi tự động và kiểm tra cửa chặn tự động trên máy local theo đúng hướng dẫn của rubric (mục 5 là phần tùy chọn chấm riêng 15 điểm, không chặn phần lõi). Thư mục `submission/results/` hiện để trống.

## 6. Quyết định và ghi chú AI
- Quyết định cuối: **HOLD**.
- Điều kiện để chuyển thành **RELEASE**:
  Cần tăng ngân sách người duyệt (`budget_images`) từ 80 lên ít nhất 120–138 ảnh để người duyệt xử lý nốt 58 ảnh còn lại trong hàng đợi `05_review_queue.csv`. Khi số lượng ảnh còn cảnh báo chưa duyệt giảm xuống dưới 10% tổng số ảnh (dưới 19 ảnh), tỉ lệ cảnh báo sẽ đạt `warn_ratio < 0.10`, đồng thời `n_errors = 0`, gate sẽ tự động chuyển kết luận sang **Release** và dataset sạch chính thức được phát hành.

- Ghi chú AI:
  - Prompt chính: Triển khai 4 module (`label_format.py`, `second_opinion.py`, `autofix.py`, `gate.py`) theo hướng dẫn TDD trong `GUIDE.md` và kiểm thử tương ứng trong `tests/`.
  - Cách kiểm code AI: Chạy 50 unit test riêng của 4 module (đạt 50/50); chạy toàn bộ test suite và đối chiếu sha1 với các file bảo vệ (`scripts/_protected.json`).
  - Lần AI sai: Khi chạy test trên môi trường Windows thuần, AI ban đầu chẩn đoán sai rằng check `duplicates` bị lỗi logic; sau khi phân tích chi tiết mới nhận ra `imagehash.phash` bị lỗi tải DLL C-extension của NumPy (`_common.cp313-win_amd64.pyd`) do chính sách Windows Application Control (WDAC), trong khi chạy trên môi trường Linux/WSL thì toàn bộ 79/79 test đều xanh hoàn toàn.

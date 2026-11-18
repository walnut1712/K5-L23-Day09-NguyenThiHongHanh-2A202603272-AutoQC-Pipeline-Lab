"""BƯỚC 4 — Cửa chặn: quyết định Release / Hold / Rework.   ★

Test:  pytest tests/test_gate.py -q

Cây quyết định Day 07 (slide Day 09: "Lỗi bắt buộc chặn pipeline; lỗi cảnh báo chuyển người xem"):

  còn ≥ 1 lỗi bắt buộc (severity ERROR)                          -> "Rework"
  không còn lỗi bắt buộc, nhưng tỉ lệ ẢNH còn cảnh báo
      >= cfg["gate"]["warn_ratio_hold"]                          -> "Hold"
  còn lại                                                        -> "Release"

Tỉ lệ cảnh báo = (số ẢNH khác nhau có ≥ 1 cảnh báo) / (tổng số ảnh).  Chú ý:
- chỉ đếm issue có `image` nằm trong `image_stems` (bỏ "<dataset>", "data.yaml");
- bỏ qua ảnh nằm trong `reviewed` (người đã xem, cảnh báo của ảnh đó coi như đã xử lý) — nhưng LỖI BẮT BUỘC thì không bao giờ được bỏ qua;
- mẫu số là số ảnh, không phải số issue.

Trả về dict: decision, n_errors, n_warn_images, n_images, warn_ratio (làm tròn 4 chữ số), reasons (list[str], giải thích bằng tiếng Việt, có số liệu).
"""
from ..common import ERROR, WARN  # noqa: F401


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    stems = set(image_stems)
    reviewed = set(reviewed)
    n_images = len(stems)
    n_errors = 0
    warned_images = set()

    for issue in issues:
        if issue.severity == ERROR:
            n_errors += 1
        elif issue.severity == WARN and issue.image in stems and issue.image not in reviewed:
            warned_images.add(issue.image)

    n_warn_images = len(warned_images)
    ratio = n_warn_images / n_images if n_images else 0.0
    warn_ratio = round(ratio, 4)
    hold_threshold = cfg["gate"]["warn_ratio_hold"]

    if n_errors:
        decision = "Rework"
        reasons = [f"Còn {n_errors} lỗi bắt buộc; cần sửa trước khi phát hành."]
    elif ratio >= hold_threshold:
        decision = "Hold"
        reasons = [
            f"{n_warn_images}/{n_images} ảnh còn cảnh báo chưa duyệt "
            f"({ratio:.2%}), đạt hoặc vượt ngưỡng Hold {hold_threshold:.2%}."
        ]
    else:
        decision = "Release"
        reasons = [
            f"Không còn lỗi bắt buộc; {n_warn_images}/{n_images} ảnh còn cảnh báo "
            f"chưa duyệt ({ratio:.2%}), dưới ngưỡng Hold {hold_threshold:.2%}."
        ]

    return {
        "decision": decision,
        "n_errors": n_errors,
        "n_warn_images": n_warn_images,
        "n_images": n_images,
        "warn_ratio": warn_ratio,
        "reasons": reasons,
    }

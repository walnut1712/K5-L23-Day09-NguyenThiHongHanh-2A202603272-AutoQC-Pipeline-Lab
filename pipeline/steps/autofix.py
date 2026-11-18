"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict  # noqa: F401

import yaml  # noqa: F401

from ..common import ERROR, parse_yolo_line  # noqa: F401


def fix(ds, issues, cfg):
    drop_codes = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
    remove_codes = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}

    errors = [issue for issue in issues if issue.severity == ERROR]
    removed_stems = {
        issue.image
        for issue in errors
        if issue.code.startswith("DUP_IMAGE_") or issue.code in remove_codes
    }
    fixes = []

    for stem in sorted(removed_stems):
        image_paths = [path for path in ds.image_files() if path.stem == stem]
        label_path = ds.label_path(stem)
        existing = [path.name for path in image_paths]
        if label_path.exists():
            existing.append(label_path.name)
        if not existing:
            continue
        for path in image_paths:
            path.unlink()
        label_path.unlink(missing_ok=True)
        fixes.append({
            "image": stem,
            "line": None,
            "action": "remove_image",
            "before": ", ".join(existing),
            "after": "",
        })

    line_issues = {}
    needs_label = set()
    rename_classes = any(issue.code == "BAD_CLASS_NAME" for issue in errors)
    for issue in errors:
        if issue.image in removed_stems:
            continue
        if issue.code == "MISSING_LABEL_FILE":
            needs_label.add(issue.image)
        elif issue.code in drop_codes or issue.code == "BOX_OUT_OF_IMAGE":
            if issue.line is not None:
                line_issues.setdefault(issue.image, {}).setdefault(issue.line, set()).add(issue.code)

    for stem in sorted(needs_label):
        if not ds.label_path(stem).exists():
            fixes.append({
                "image": stem,
                "line": None,
                "action": "needs_label",
                "before": "(không có file)",
                "after": "chuyển người gán",
            })

    if rename_classes:
        yaml_path = ds.yaml_path
        if yaml_path.exists():
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            before_names = data.get("names") if isinstance(data, dict) else data
        else:
            data = {}
            before_names = "(không có file)"
        if not isinstance(data, dict):
            data = {}

        class_names = list(cfg["classes"])
        if before_names != class_names:
            data["names"] = class_names
            yaml_path.write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            fixes.append({
                "image": "data.yaml",
                "line": None,
                "action": "rename_classes",
                "before": str(before_names),
                "after": str(class_names),
            })

    for stem in sorted(line_issues):
        label_path = ds.label_path(stem)
        if not label_path.exists():
            continue
        original_text = label_path.read_text(encoding="utf-8", errors="replace")
        original_lines = original_text.splitlines()
        updated_lines = list(original_lines)
        for line_no, codes in sorted(line_issues[stem].items()):
            index = line_no - 1
            if index < 0 or index >= len(original_lines):
                continue
            before = original_lines[index]
            if codes & drop_codes:
                updated_lines[index] = None
                fixes.append({
                    "image": stem,
                    "line": line_no,
                    "action": "drop_line",
                    "before": before,
                    "after": "",
                })
                continue

            if "BOX_OUT_OF_IMAGE" in codes:
                class_id, cx, cy, width, height = parse_yolo_line(before)
                left = max(0.0, cx - width / 2)
                top = max(0.0, cy - height / 2)
                right = min(1.0, cx + width / 2)
                bottom = min(1.0, cy + height / 2)
                if right <= left or bottom <= top:
                    updated_lines[index] = None
                    fixes.append({
                        "image": stem,
                        "line": line_no,
                        "action": "drop_line",
                        "before": before,
                        "after": "",
                    })
                    continue

                clipped = (
                    class_id,
                    (left + right) / 2,
                    (top + bottom) / 2,
                    right - left,
                    bottom - top,
                )
                after = " ".join(
                    [str(clipped[0])] + [format(value, ".12g") for value in clipped[1:]]
                )
                updated_lines[index] = after
                fixes.append({
                    "image": stem,
                    "line": line_no,
                    "action": "clip_box",
                    "before": before,
                    "after": after,
                })

        if updated_lines != original_lines:
            trailing_newline = original_text.endswith(("\n", "\r"))
            text = "\n".join(line for line in updated_lines if line is not None)
            if trailing_newline and text:
                text += "\n"
            label_path.write_text(text, encoding="utf-8")

    return fixes

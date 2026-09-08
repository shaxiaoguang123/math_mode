#!/usr/bin/env python3
"""Audit a rendered PDF against Huawei Cup page and chapter rules.

The audit is deliberately conservative. It reports confidence and unknowns
rather than pretending that broken Chinese PDF CMaps yield reliable text.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    import pymupdf
except ImportError:  # compatibility with older installations
    import fitz as pymupdf


IDENTITY_RE = re.compile(
    r"学校|学院|实验室|参赛队号|队员姓名|指导教师|学号|邮箱|email|"
    r"\\b(?:school|student|team|member|advisor)\\b|C:\\\\Users\\\\",
    re.IGNORECASE,
)
REFERENCE_RE = re.compile(r"^\\s*(参考文献|References?)\\s*$", re.IGNORECASE)
APPENDIX_RE = re.compile(r"^\\s*(附录|Appendix)\\s*[A-ZＡ-Ｚ0-9０-９]*\\s*$", re.IGNORECASE)
PAGE_RE = re.compile(r"(?<!\\d)(\\d{1,3})(?!\\d)")


def pdf_pages(pdf: Path) -> int:
    doc = pymupdf.open(str(pdf))
    count = len(doc)
    doc.close()
    return count


def extract_page_records(pdf: Path):
    doc = pymupdf.open(str(pdf))
    records = []
    for physical, page in enumerate(doc, 1):
        text_dict = page.get_text("dict")
        blocks = page.get_text("blocks")
        text = "\n".join(str(block[4]) for block in blocks if len(block) >= 5)
        spans = []
        layout_boxes = []
        image_count = 0
        for block in text_dict.get("blocks", []):
            if block.get("type") == 1 and block.get("bbox"):
                image_count += 1
                layout_boxes.append(block["bbox"])
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if str(span.get("text", "")).strip() and span.get("bbox"):
                        layout_boxes.append(span["bbox"])
                    spans.append({
                        "text": span.get("text", ""),
                        "font": span.get("font", ""),
                        "size": span.get("size", 0),
                        "bbox": span.get("bbox", []),
                    })
        drawings = page.get_drawings()
        drawing_count = 0
        for drawing in drawings:
            rect = drawing.get("rect")
            if rect and rect.get_area() >= 4:
                drawing_count += 1
                layout_boxes.append((rect.x0, rect.y0, rect.x1, rect.y1))
        width, height = float(page.rect.width), float(page.rect.height)
        cols, rows = 48, 68
        occupied = set()
        for bbox in layout_boxes:
            x0, y0, x1, y1 = (float(value) for value in bbox)
            if x1 <= x0 or y1 <= y0:
                continue
            c0 = max(0, min(cols - 1, int(cols * x0 / width)))
            c1 = max(0, min(cols - 1, int(cols * max(x0, x1 - 0.01) / width)))
            r0 = max(0, min(rows - 1, int(rows * y0 / height)))
            r1 = max(0, min(rows - 1, int(rows * max(y0, y1 - 0.01) / height)))
            for row in range(r0, r1 + 1):
                for col in range(c0, c1 + 1):
                    occupied.add((row, col))
        records.append({
            "physical_page": physical,
            "text": text,
            "spans": spans,
            "layout": {
                "occupied_fraction": round(len(occupied) / (rows * cols), 4),
                "text_characters": len(re.sub(r"\s+", "", text)),
                "image_count": image_count,
                "drawing_count": drawing_count,
            },
        })
    doc.close()
    return records


def first_page_text(page):
    return " ".join(line.strip() for line in page["text"].splitlines() if line.strip())


def detect_heading_pages(records, heading_manifest):
    output = []
    for item in heading_manifest:
        title = item.get("rendered_title") or item.get("title", "")
        aliases = [title, item.get("title", ""), *item.get("aliases", [])]
        # Word heading JSON records the exact visible title text and its page.
        # Keep all exact matches; the next heading determines the range.
        matches = []
        for record in records:
            text = first_page_text(record)
            if any(alias and alias in text for alias in aliases):
                matches.append(record["physical_page"])
        output.append({**item, "physical_pages": matches, "confidence": "high" if matches else "unknown"})
    return output


def detect_heading_pages_from_manifest(records, chapters):
    """Use rendered titles supplied by the generator when PDF CMaps are broken."""
    output = []
    for item in chapters:
        title = item.get("rendered_title") or item.get("title", "")
        normalized = re.sub(r"^[0-9.\s]+", "", title)
        matches = []
        for record in records:
            text = first_page_text(record)
            if normalized and normalized in text:
                matches.append(record["physical_page"])
        output.append({**item, "physical_pages": matches, "confidence": "medium" if matches else "unknown"})
    return output


def detect_heading_pages_from_toc(toc: Path, records):
    """Read section starts from XeLaTeX's .toc when PDF text is unusable."""
    if not toc.exists():
        return []
    offset = printed_page_offset(records)
    output = []
    pattern = re.compile(r"\\contentsline \{section\}\{(?:\\numberline \{([^}]+)\})?(.*?)\}\{(\d+)\}\{section\.")
    raw = toc.read_bytes()
    candidates = []
    for encoding in ("utf-8-sig", "gb18030", "cp936"):
        try:
            candidates.append(raw.decode(encoding))
        except UnicodeDecodeError:
            pass
    toc_text = max(candidates, key=lambda value: sum(value.count(token) for token in ("问题", "参考文献", "附录", "结论")), default="")
    entries = []
    for line in toc_text.splitlines():
        match = pattern.search(line)
        if not match:
            continue
        number_token = (match.group(1) or "").strip()
        title = re.sub(r"\\[A-Za-z@]+|[{}]", "", match.group(2)).strip()
        printed = int(match.group(3))
        physical = printed - offset
        if not 1 <= physical <= len(records):
            continue
        entries.append({"number_token": number_token, "title": title, "printed": printed, "physical": physical})
    appendix_index = next((index for index, entry in enumerate(entries) if entry["number_token"] and not re.fullmatch(r"\d+(?:\.\d+)*", entry["number_token"])), len(entries))
    reference_index = next((index for index, entry in enumerate(entries) if REFERENCE_RE.match(entry["title"])), None)
    if reference_index is None and appendix_index:
        numeric_before_appendix = [index for index, entry in enumerate(entries[:appendix_index]) if re.fullmatch(r"\d+(?:\.\d+)*", entry["number_token"])]
        reference_index = numeric_before_appendix[-1] if numeric_before_appendix else None
    for index, entry in enumerate(entries):
        role = "appendix" if index >= appendix_index else "references" if reference_index is not None and index >= reference_index else "body"
        output.append({
            "title": entry["title"] or f"section@{entry['printed']}",
            "rendered_title": entry["title"],
            "role": role,
            "level": 1,
            "physical_pages": [entry["physical"]],
            "confidence": "high",
        })
    return output


def printed_page_offset(records):
    # Look near the footer; page labels are often the only short numeric block.
    for record in records[:8]:
        candidates = []
        for span in record["spans"]:
            text = span["text"].strip()
            if PAGE_RE.fullmatch(text):
                y = span["bbox"][3] if len(span["bbox"]) >= 4 else 0
                if y > 700:
                    candidates.append(int(text))
        if candidates:
            return candidates[0] - record["physical_page"]
    return 0


def role_ranges(chapters, records):
    # Use heading starts and the next heading, with references/appendix as body boundaries.
    starts = []
    for chapter in chapters:
        pages = chapter.get("physical_pages", [])
        if pages:
            starts.append((min(pages), chapter))
    starts.sort(key=lambda x: x[0])
    result = []
    for index, (start, chapter) in enumerate(starts):
        end = (starts[index + 1][0] - 1) if index + 1 < len(starts) else len(records)
        end = max(start, end)
        result.append({
            "title": chapter.get("title"),
            "role": chapter.get("role"),
            "level": chapter.get("level", 1),
            "start_physical_page": start,
            "end_physical_page": end,
            "touched_pages": max(0, end - start + 1),
        })
    return result


def body_pages(chapter_ranges):
    body = [item for item in chapter_ranges if item.get("role") not in {"references", "appendix"}]
    if not body:
        return {"start": None, "end": None, "pages": 0}
    start = min(item["start_physical_page"] for item in body)
    end = max(item["end_physical_page"] for item in body)
    return {"start": start, "end": end, "pages": end - start + 1}


def body_layout_density(records, body):
    """Summarize page occupancy without turning visual density into a score.

    This is a warning-only structural signal. Sparse pages may be legitimate
    chapter endings, so the audit focuses on consecutive runs and the late
    third rather than failing an isolated page.
    """
    if not body.get("start") or not body.get("end"):
        return {"pages": [], "longest_sparse_run": 0, "late_sparse_ratio": None}
    selected = records[body["start"] - 1:body["end"]]
    pages = []
    longest = current = 0
    for record in selected:
        layout = dict(record["layout"])
        visual_evidence = layout["image_count"] > 0 or layout["drawing_count"] >= 10
        sparse = (
            layout["occupied_fraction"] < 0.12
            and layout["text_characters"] < 650
            and layout["image_count"] == 0
        )
        current = current + 1 if sparse else 0
        longest = max(longest, current)
        pages.append({"physical_page": record["physical_page"], **layout, "visual_evidence": visual_evidence, "sparse": sparse})
    late_start = max(0, (2 * len(pages)) // 3)
    late = pages[late_start:]
    late_sparse_ratio = (sum(page["sparse"] for page in late) / len(late)) if late else 0.0
    mean_occupancy = sum(page["occupied_fraction"] for page in pages) / len(pages)
    late_mean_occupancy = sum(page["occupied_fraction"] for page in late) / len(late) if late else 0.0
    visual_pages = [page["physical_page"] for page in pages if page["visual_evidence"]]
    late_visual_pages = [page["physical_page"] for page in late if page["visual_evidence"]]
    return {
        "pages": pages,
        "mean_occupied_fraction": round(mean_occupancy, 4),
        "late_third_start_physical_page": late[0]["physical_page"] if late else None,
        "late_mean_occupied_fraction": round(late_mean_occupancy, 4),
        "late_sparse_ratio": round(late_sparse_ratio, 4),
        "longest_sparse_run": longest,
        "visual_evidence_pages": visual_pages,
        "late_visual_evidence_pages": late_visual_pages,
        "interpretation": "warning-only; inspect the rendered contact sheet before restructuring",
    }


def pdfinfo(pdf: Path) -> dict[str, str]:
    try:
        proc = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return {}
    values = {}
    for line in proc.stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--heading-json", type=Path)
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--toc", type=Path)
    ap.add_argument("--targets", type=Path)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--source", type=Path)
    args = ap.parse_args()
    pdf = args.pdf.resolve()
    records = extract_page_records(pdf)
    headings = json.loads(args.heading_json.read_text(encoding="utf-8-sig")) if args.heading_json and args.heading_json.exists() else {"headings": []}
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig")) if args.manifest and args.manifest.exists() else {"chapters": []}
    matched = detect_heading_pages(records, headings.get("headings", [])) if headings.get("headings") else []
    if not matched and manifest.get("chapters"):
        matched = detect_heading_pages(records, manifest["chapters"])
    if not any(item.get("physical_pages") for item in matched) and manifest.get("chapters"):
        matched = detect_heading_pages_from_manifest(records, manifest["chapters"])
    toc = args.toc.resolve() if args.toc else pdf.with_suffix(".toc")
    heading_source = "pdf_or_manifest"
    if not any(item.get("physical_pages") for item in matched):
        matched = detect_heading_pages_from_toc(toc, records)
        if matched:
            heading_source = "xelatex_toc"
    ranges = role_ranges(matched, records)
    body = body_pages(ranges)
    density = body_layout_density(records, body)
    targets = json.loads(args.targets.read_text(encoding="utf-8-sig")) if args.targets and args.targets.exists() else {}
    required_body = int(targets.get("required_body_pages", 45))
    role_targets = targets.get("role_targets", {})
    issues = []
    for chapter in ranges:
        role_target = role_targets.get(chapter.get("role"), {})
        pages = chapter.get("touched_pages", 0)
        if role_target and (pages < role_target.get("min_pages", 0) or pages > role_target.get("max_pages", 10**9)):
            issues.append({
                "code": "chapter_pages_outside_role_window",
                "severity": "warning",
                "title": chapter.get("title"),
                "role": chapter.get("role"),
                "actual": pages,
                "min": role_target.get("min_pages"),
                "max": role_target.get("max_pages"),
            })
    if body["pages"] < required_body:
        issues.append({"code": "body_pages_below_minimum", "severity": "error", "actual": body["pages"], "required": required_body})
    if density.get("longest_sparse_run", 0) >= 2:
        issues.append({
            "code": "consecutive_sparse_body_pages",
            "severity": "warning",
            "longest_run": density["longest_sparse_run"],
            "message": "正文存在连续低占用页；请从逐页联系表确认是否为后置审计内容、短表或强制分页，并优先重构科学证据。",
        })
    if density.get("late_sparse_ratio") is not None and density["late_sparse_ratio"] >= 0.25:
        issues.append({
            "code": "late_body_sparse_ratio_high",
            "severity": "warning",
            "actual": density["late_sparse_ratio"],
            "message": "正文后 1/3 稀疏页比例偏高；不得用放大图表消除告警，应把真实验证、误差、敏感性或边界证据前移到对应问题。",
        })
    if len(density.get("visual_evidence_pages", [])) >= 4 and not density.get("late_visual_evidence_pages"):
        issues.append({
            "code": "late_body_visual_evidence_absent",
            "severity": "warning",
            "visual_pages": density["visual_evidence_pages"],
            "message": "正文已有多页图形证据，但后 1/3 没有图形证据；请检查图是否过度集中，并把真实诊断、敏感性或边界结果放回对应问题。",
        })
    if not matched:
        issues.append({"code": "headings_not_detected", "severity": "warning", "message": "未检测到可靠的章节标题；请提供 Word 标题 JSON 或开启 OCR 复核。"})
    full_text = "\n".join(record["text"] for record in records)
    identity_hits = sorted(set(IDENTITY_RE.findall(full_text)))
    if identity_hits:
        issues.append({"code": "possible_identity_text", "severity": "error", "matches": identity_hits[:20]})
    # We cannot prove font correctness from a PDF with broken CMaps, but can flag obvious fonts.
    fonts = sorted({span["font"] for record in records for span in record["spans"] if span.get("font")})
    forbidden_fonts = [font for font in fonts if any(token in font.lower() for token in ("lishu", "kaiti"))]
    if forbidden_fonts:
        issues.append({"code": "non_body_font_detected", "severity": "warning", "fonts": forbidden_fonts, "message": "标签可使用隶书；正文/关键词内容应人工确认是否为宋体。"})
    report = {
        "pdf": str(pdf),
        "pdfinfo": pdfinfo(pdf),
        "physical_pages": len(records),
        "printed_page_offset": printed_page_offset(records),
        "heading_source": heading_source,
        "body": body,
        "body_layout_density": density,
        "chapter_ranges": ranges,
        "detected_fonts": fonts,
        "issues": issues,
        "status": "FAIL" if any(item["severity"] == "error" for item in issues) else "PASS_WITH_WARNINGS" if issues else "PASS",
        "limitations": [
            "最终页数以本 PDF 为准；DOCX docProps/app.xml 的 Pages 不参与验收。",
            "中文字体 CMap 损坏时，章节/身份检测可能需要 OCR 或 Word 标题 JSON 交叉验证。",
            "问题章节区间是样例先验，不是要求所有章节等长。",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(1 if report["status"] == "FAIL" else 0)


if __name__ == "__main__":
    main()

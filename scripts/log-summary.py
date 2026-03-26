#!/usr/bin/env python3
"""
Extract installation summary from log for QR code generation.
Outputs compressed, QR-friendly log with only essential information.
"""

import re
import sys
import gzip
import base64
import urllib.parse


def extract_summary(full_log):
    """Extract [N/N], warnings and errors from log text."""
    lines = full_log.split("\n")
    summary_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if re.match(r"\[PROGRESS \d+/\d+\]", line):
            summary_lines.append(line)
        elif "[ERROR]" in line or "[FATAL]" in line:
            summary_lines.append(line)
        elif "WARNING:" in line or "Warning:" in line or "WARNING |" in line:
            summary_lines.append(line)
        elif line.startswith("[OK]"):
            summary_lines.append(line)
        elif "error:" in line.lower() or "failed" in line.lower():
            if "WARNING:" not in line and "error handling" not in line.lower():
                summary_lines.append(line)

    return "\n".join(summary_lines)


def compress_for_qr(text, max_base64_length=2500):
    """
    Compress text and encode to base64 for QR compatibility.
    Truncates if necessary to fit QR limits.
    """
    compressed = gzip.compress(text.encode("utf-8"), compresslevel=9)
    b64 = base64.b64encode(compressed).decode("ascii")

    if len(b64) > max_base64_length:
        truncated = b64[: max_base64_length - 20]
        return truncated + "...[TRUNCATED]"

    return b64


def create_log_summary(log_path):
    """Read log file, extract summary, return compressed base64."""
    try:
        with open(log_path, "r", errors="replace") as f:
            full_log = f.read()
    except Exception as e:
        return None, None, str(e)

    summary = extract_summary(full_log)
    compressed = compress_for_qr(summary)

    errors = len([l for l in summary.split("\n") if "[ERROR]" in l or "[FATAL]" in l])
    warnings = len([l for l in summary.split("\n") if "WARNING" in l])
    ok_count = len([l for l in summary.split("\n") if l.startswith("[OK]")])
    steps = len(
        [l for l in summary.split("\n") if re.match(r"\[PROGRESS \d+/\d+\]", l)]
    )

    stats = {"steps": steps, "errors": errors, "warnings": warnings, "ok": ok_count}

    return compressed, stats, None


def generate_decoder_url(compressed_data):
    """Generate URL with data encoded in hash fragment."""
    base_url = "https://madoslinux.github.io/mados-installer/log-decoder.html"
    return f"{base_url}#{compressed_data}"


def generate_qr_api_url(data, size=300):
    """Generate QR code URL using public API."""
    encoded = urllib.parse.quote(data)
    return (
        f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded}"
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: log-summary.py <log_file>")
        sys.exit(1)

    compressed, stats, error = create_log_summary(sys.argv[1])
    if error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Compressed log ({stats['steps']} steps, {stats['errors']} errors, {stats['warnings']} warnings, {stats['ok']} ok):"
    )
    print(compressed)
    print()
    print(f"Decoder URL: {generate_decoder_url(compressed)}")
    print(f"QR API URL: {generate_qr_api_url(generate_decoder_url(compressed))}")

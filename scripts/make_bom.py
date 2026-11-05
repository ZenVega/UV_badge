#!/usr/bin/env python3
"""Regenerate BOM.md (and the BOM section of README.md) from the KiCad schematic.

Usage: python3 scripts/make_bom.py
Requires kicad-cli on PATH (or set KICAD_CLI).
"""
import csv, os, re, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCH = ROOT / "PCB" / "UV_badge.kicad_sch"
OUT = ROOT / "BOM.md"
README = ROOT / "README.md"
README_START, README_END = "<!-- BOM:START -->", "<!-- BOM:END -->"
BATCH = 50  # number of PCBs for the batch quantity column
KICAD_CLI = os.environ.get("KICAD_CLI", "kicad-cli")

url_re = re.compile(r"https?://\S+")

with tempfile.TemporaryDirectory() as tmp:
    csv_path = Path(tmp) / "bom.csv"
    subprocess.run([KICAD_CLI, "sch", "export", "bom",
                    "--fields", "Reference,Value,Footprint,${QUANTITY},Description,MPN,link",
                    "--labels", "Reference,Value,Footprint,Qty,Description,MPN,link",
                    "--group-by", "Value,Footprint",
                    "--ref-range-delimiter", "",
                    "-o", str(csv_path), str(SCH)],
                   check=True, stdout=subprocess.DEVNULL)
    rows = list(csv.DictReader(open(csv_path)))

out = [["Ref", "Qty", f"Qty x{BATCH}", "Value", "MPN", "Footprint", "Description", "Link"]]
for r in rows:
    desc = r["Description"]
    links = url_re.findall(desc)
    desc = url_re.sub("", desc).replace("Source:", "").strip(" -.")
    if r["link"]:
        links.append(r["link"])
    # strip tracking query from aliexpress links
    links = [l.split("?")[0] if "aliexpress" in l else l for l in links]
    out.append([r["Reference"], r["Qty"], str(int(r["Qty"]) * BATCH), r["Value"], r["MPN"],
                r["Footprint"].split(":")[-1], desc, " ".join(links)])

w = [max(len(row[i]) for row in out) for i in range(len(out[0]))]
fmt = lambda row: "| " + " | ".join(c.ljust(w[i]) for i, c in enumerate(row)) + " |"
table = [fmt(out[0]), "|" + "|".join("-" * (x + 2) for x in w) + "|"] + [fmt(r) for r in out[1:]]
OUT.write_text("\n".join(["# UV Badge – Bill of Materials", ""] + table) + "\n")
print(f"Wrote {OUT.relative_to(ROOT)} ({len(out) - 1} rows)")

# replace the table between the BOM markers in the README
readme = README.read_text()
if README_START in readme and README_END in readme:
    head, rest = readme.split(README_START, 1)
    _, tail = rest.split(README_END, 1)
    README.write_text(head + README_START + "\n" + "\n".join(table) + "\n" + README_END + tail)
    print(f"Updated BOM section in {README.relative_to(ROOT)}")

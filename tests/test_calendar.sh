#!/usr/bin/env bash
# Tests for the calendar-builder scripts against fictional Brightwell fixtures.
# Usage: bash tests/test_calendar.sh   (exits non-zero on any failure)
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
S="$ROOT/skills/calendar-builder/scripts"
F="$ROOT/tests/fixtures/calendar"
EX="$ROOT/skills/calendar-builder/examples/sample-rows.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fails=0

check() {  # check <name> <expected exit> <actual exit> [<file> <pattern that must appear>]
  local name="$1" want="$2" got="$3"
  if [ "$want" != "$got" ]; then
    echo "FAIL $name: exit $got, expected $want"; fails=$((fails + 1)); return
  fi
  if [ $# -ge 5 ] && ! grep -qE -- "$5" "$4"; then
    echo "FAIL $name: output does not match '$5'"; fails=$((fails + 1)); return
  fi
  echo "ok   $name"
}

# Usage text on missing arguments
python3 "$S/tab_guard.py" >/dev/null 2>"$TMP/u1"; check "tab_guard usage" 2 $? "$TMP/u1" "Usage"
python3 "$S/verify_calendar.py" >/dev/null 2>"$TMP/u2"; check "verify_calendar usage" 2 $? "$TMP/u2" "Usage"
python3 "$S/build_calendar.py" >/dev/null 2>"$TMP/u3"; check "build_calendar usage" 2 $? "$TMP/u3" "Usage"

# tab_guard: nothing changed, every write accepted
python3 "$S/tab_guard.py" "$F/ideas_before.json" "$F/ideas_fresh_same.json" "$F/ideas_writes.json" \
  --key "Idea (one line)" --config "$F/workspace.json" >"$TMP/g1"
check "tab_guard accepts unchanged rows" 0 $? "$TMP/g1" '"range": "Ideas!G2"'
grep -q '"range": "Ideas!F3"' "$TMP/g1" && echo "ok   tab_guard exact range for row 3" || { echo "FAIL tab_guard row 3 range"; fails=$((fails + 1)); }

# tab_guard: row 2 Status set to Declined, rows 3 and 4 sorted during the run
python3 "$S/tab_guard.py" "$F/ideas_before.json" "$F/ideas_fresh_changed.json" "$F/ideas_writes.json" \
  --key "Idea (one line)" >"$TMP/g2"
check "tab_guard skips changed rows" 1 $? "$TMP/g2" "Status on Ideas row 2"
grep -q "deleted, inserted or sorted" "$TMP/g2" && echo "ok   tab_guard reports sorted row" || { echo "FAIL tab_guard sorted row"; fails=$((fails + 1)); }
python3 -c "import json,sys; d=json.load(open('$TMP/g2')); sys.exit(0 if d['accepted']==[] and len(d['skipped'])==5 and len(d['brief_lines'])==2 else 1)"
check "tab_guard writes a row in full or not at all" 0 $?

# tab_guard: milestone cancelled during the run
python3 "$S/tab_guard.py" "$F/milestones_before.json" "$F/milestones_fresh.json" "$F/milestones_writes.json" \
  --key "Milestone" >"$TMP/g3"
check "tab_guard milestone cancelled" 1 $? "$TMP/g3" "Confirmed on Milestones row 2"

# tab_guard: unknown key
python3 "$S/tab_guard.py" "$F/milestones_before.json" "$F/milestones_fresh.json" "$F/milestones_writes.json" \
  --key "Nope" >/dev/null 2>&1
check "tab_guard rejects unknown key" 2 $?

# verify_calendar: matching JSON export (formatted dates)
python3 "$S/verify_calendar.py" "$F/plan_layout.txt" "$F/calendar.json" --config "$F/workspace.json" --expect 13 >"$TMP/v1"
check "verify_calendar match (json)" 0 $? "$TMP/v1" "Mismatches: 0"
grep -q "Plan rows parsed: 13; calendar rows: 13" "$TMP/v1" && echo "ok   verify_calendar parses wrapped rows" || { echo "FAIL verify_calendar row count"; fails=$((fails + 1)); }

# verify_calendar: two mismatches and a wrong stated count
python3 "$S/verify_calendar.py" "$F/plan_layout.txt" "$F/calendar_mismatch.json" --expect 14 >"$TMP/v2"
check "verify_calendar mismatch" 1 $? "$TMP/v2" "Mismatches: 3"
grep -q "W01-03) AM/PM" "$TMP/v2" && grep -q "W02-02) title" "$TMP/v2" && echo "ok   verify_calendar names each mismatch" || { echo "FAIL verify_calendar mismatch lines"; fails=$((fails + 1)); }

# build_calendar (needs openpyxl) and an end-to-end verify on the .xlsx
if python3 -c "import openpyxl" 2>/dev/null; then
  python3 "$S/build_calendar.py" "$EX" "$TMP/cal.xlsx" --config "$F/workspace.json" >"$TMP/b1" 2>"$TMP/b1e"
  check "build_calendar builds" 0 $? "$TMP/b1" "13 rows, 2 milestones, 2 ideas"
  [ ! -s "$TMP/b1e" ] && echo "ok   build_calendar maps every content type" || { echo "FAIL build_calendar warnings: $(cat "$TMP/b1e")"; fails=$((fails + 1)); }
  python3 "$S/verify_calendar.py" "$F/plan_layout.txt" "$TMP/cal.xlsx" --config "$F/workspace.json" >"$TMP/v3"
  check "verify_calendar match (xlsx)" 0 $? "$TMP/v3" "Mismatches: 0"
  python3 - "$TMP/cal.xlsx" <<'EOF'
import sys
from openpyxl import load_workbook
wb = load_workbook(sys.argv[1])
assert wb.sheetnames == ["This Week", "Calendar", "Ideas", "Milestones", "How to use"], wb.sheetnames
ws = wb["Calendar"]
hdr = [c.value for c in ws[1]]
assert len(hdr) == 22 and hdr[0] == "Date" and hdr[21] == "Original draft", hdr
assert ws["M2"].value == "W01-01" and ws["N2"].value == 1
assert ws["C2"].value == "LinkedIn post: partner news" and ws["D2"].value == "Partner & Customer Proof"
assert ws["G2"].value is None and ws["H2"].value is None
row = {ws.cell(r, 13).value: r for r in range(2, ws.max_row + 1)}
assert ws.cell(row["W03-04"], 3).value == "LinkedIn post: Guide promotion"
assert ws.cell(row["W01-02"], 10).value.startswith("The team writes this")
print("ok   build_calendar layout")
EOF
  [ $? -eq 0 ] || { echo "FAIL build_calendar layout"; fails=$((fails + 1)); }
  python3 "$S/build_calendar.py" "$EX" "$TMP/cal2.xlsx" --config "$F/workspace.json" --sheets-formulas >/dev/null 2>&1
  python3 -c "
from openpyxl import load_workbook
ws = load_workbook('$TMP/cal2.xlsx')['Calendar']
assert 'Publish|Newsletter|Distribute' in ws['G2'].value and ws['H2'].value.startswith('=ARRAYFORMULA')
" && echo "ok   build_calendar --sheets-formulas" || { echo "FAIL build_calendar --sheets-formulas"; fails=$((fails + 1)); }
else
  echo "skip build_calendar tests (openpyxl not installed)"
fi

echo
if [ "$fails" -gt 0 ]; then echo "$fails test(s) failed"; exit 1; fi
echo "All calendar tests passed"

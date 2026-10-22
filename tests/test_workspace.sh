#!/usr/bin/env bash
# Tests for skills/workspace-setup/scripts/check_workspace.py
set -u
cd "$(dirname "$0")/.."
S=skills/workspace-setup/scripts/check_workspace.py
F=tests/fixtures/workspace
pass=0; fail=0
check() { if [ "$1" = "$2" ]; then echo "ok   $3"; pass=$((pass+1)); else echo "FAIL $3 (exit $1, expected $2)"; fail=$((fail+1)); fi; }

python3 $S >/dev/null 2>&1; check $? 2 "usage without arguments"
python3 $S tests/fixtures/orchestrator/workspace.json >/dev/null; check $? 0 "complete fixture config passes"
python3 $S templates/workspace.example.json >/dev/null; check $? 1 "template with placeholders fails"
out=$(python3 $S templates/workspace.example.json)
echo "$out" | grep -q "no TEST copy"; check $? 0 "missing TEST copy reported"
python3 $S $F/bad_regex.json >/dev/null; check $? 1 "bad regex and non-Monday week 1 fail"
python3 $S $F/bad_regex.json | grep -q "not a Monday"; check $? 0 "non-Monday reported"
python3 $S $F/missing_sources.json | grep -q "Required source 'calendar'"; check $? 0 "missing required source reported"

echo "passed $pass, failed $fail"
[ $fail -eq 0 ]

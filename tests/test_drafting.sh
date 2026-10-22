#!/usr/bin/env bash
# Tests for the short-form-drafter and proof-intake scripts against fictional fixtures.
# Run from anywhere: bash tests/test_drafting.sh. Exits non-zero on any failure.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FX="$ROOT/tests/fixtures/drafting"
SFD="$ROOT/skills/short-form-drafter/scripts"
PI="$ROOT/skills/proof-intake/scripts"
PASS=0; FAIL=0

ok()   { PASS=$((PASS+1)); echo "ok   $1"; }
bad()  { FAIL=$((FAIL+1)); echo "FAIL $1"; }

# expect_exit <name> <code> <command...>
expect_exit() {
  local name="$1" code="$2"; shift 2
  OUT="$("$@" 2>&1)"; local got=$?
  if [ "$got" = "$code" ]; then ok "$name (exit $got)"; else bad "$name (exit $got, want $code)"; echo "$OUT" | head -20; fi
}
# expect_text <name> <text> : checks the last OUT contains text
expect_text() { if printf '%s' "$OUT" | grep -qF -- "$2"; then ok "$1"; else bad "$1: missing '$2'"; fi; }
expect_no_text() { if printf '%s' "$OUT" | grep -qF -- "$2"; then bad "$1: unexpected '$2'"; else ok "$1"; fi; }
# json_eq <name> <python expression on d> <expected>
json_eq() {
  local got; got="$(printf '%s' "$OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print($2)")"
  if [ "$got" = "$3" ]; then ok "$1"; else bad "$1: got '$got', want '$3'"; fi
}

cd "$FX" || exit 1

echo "# The two copies of check_draft.py are identical"
if cmp -s "$SFD/check_draft.py" "$PI/check_draft.py"; then ok "check_draft.py identical"; else bad "check_draft.py copies differ"; fi

echo "# check_draft.py"
expect_exit "usage without --config" 2 python3 "$SFD/check_draft.py" draft_pass.json
expect_exit "usage without draft" 2 python3 "$SFD/check_draft.py" --config workspace.json
expect_exit "clean UK post passes" 0 python3 "$SFD/check_draft.py" draft_pass.json --config workspace.json --facts facts_e01_hold.json
expect_exit "bad post fails" 1 python3 "$SFD/check_draft.py" draft_fail.json --config workspace.json --facts facts_e01_hold.json
for t in "Word count 64" "Opening sentence has 16 words" "Em dash" "'metermate'" "'seamless'" \
         "'optimize' is not UK" "'miles'" "R-01:" "Webinar mentioned" "Link in the post body" \
         "First mention of Priya" "2 hashtags on the last line" "Missing #EnergyReporting"; do
  expect_text "bad post: $t" "$t"
done
expect_text "figure warning" "Figure found"
expect_no_text "UK 'colour' allowed under UK spelling" "'colour'"
expect_exit "on-hold topic clears when fact approved" 1 python3 "$SFD/check_draft.py" draft_fail.json --config workspace.json --facts facts_e01_approved.json
expect_no_text "webinar not flagged when E01 approved" "Webinar mentioned"
expect_exit "no facts file: topic on hold" 1 python3 "$SFD/check_draft.py" draft_fail.json --config workspace.json
expect_text "no facts file: webinar flagged" "Webinar mentioned"
expect_exit "poll limits" 1 python3 "$SFD/check_draft.py" draft_poll_bad.json --config workspace.json
expect_text "poll question limit" "Poll question missing or over 140"
expect_text "poll option limit" "Poll option over 30 characters"
expect_exit "US config fails UK spelling and metric" 1 python3 "$SFD/check_draft.py" draft_us.json --config workspace_us.json
expect_text "US: colour fails" "'colour' is not US spelling"
expect_text "imperial: km fails" "'12 km'"
expect_text "video uses post word count" "Word count 14"
expect_exit "minimal config: only generic checks" 1 python3 "$SFD/check_draft.py" draft_fail.json --config workspace_min.json
expect_no_text "minimal config: no competitor check" "metermate"
expect_no_text "minimal config: no hashtag check" "hashtags on the last line"
expect_text "minimal config: em dash still fails" "Em dash"

echo "# check_proof_post.py"
expect_exit "proof usage without --config" 2 python3 "$PI/check_proof_post.py" proof_draft_pass.json proof_item.json
expect_exit "proof post passes" 0 python3 "$PI/check_proof_post.py" proof_draft_pass.json proof_item.json --config workspace.json --facts facts_e01_hold.json
expect_exit "proof post passes check_draft" 0 python3 "$PI/check_draft.py" proof_draft_pass.json --config workspace.json
expect_exit "edited quote fails" 1 python3 "$PI/check_proof_post.py" proof_draft_fail.json proof_item.json --config workspace.json
expect_text "quote word for word" "not the approved quote word for word"
expect_text "unknown name warning" "Capitalized word 'Westmoor'"
expect_text "figure not in item" "Figure '30'"
expect_exit "organization name" 1 python3 "$PI/check_proof_post.py" proof_draft_org.json proof_item.json --config workspace.json
expect_text "organization exact" "Organization not named exactly"
expect_exit "TEST item on live" 1 python3 "$PI/check_proof_post.py" proof_draft_pass.json proof_item.json --config workspace.json --live
expect_text "TEST item on live message" "TEST item used for a live draft"

echo "# match_proof.py"
expect_exit "match usage without --config" 2 python3 "$PI/match_proof.py" calendar.json proof_log.json
expect_exit "match runs" 0 python3 "$PI/match_proof.py" calendar.json proof_log.json --config workspace.json --as-of 2026-03-02
json_eq "slots in date order, Cancelled skipped" "','.join(s['row_id'] for s in d['slots'])" "W01-01,W01-02,W02-02"
json_eq "W01-01 drafted from row 2" "d['slots'][0]['action'], d['slots'][0]['proof_row']" "draft 2"
json_eq "approver note is a condition" "d['slots'][0]['person_note']" "Sam, first reseller partner only."
json_eq "placeholder detected" "d['slots'][0]['title_placeholder'], d['slots'][2]['title_placeholder']" "True False"
json_eq "W01-02 cut-off passed" "d['slots'][1]['pending'][0]['signoff_cutoff'], d['slots'][1]['pending'][0]['cutoff_passed']" "28 FEB 26 True"
json_eq "W01-02 swap proposed" "d['slots'][1]['propose_swap']" "True"
json_eq "W02-02 cut-off ahead, no swap" "d['slots'][2]['pending'][0]['cutoff_passed'], d['slots'][2]['propose_swap']" "False False"
json_eq "sign-off No marked" "[i['proof_row'] for i in d['mark_not_used_signoff_no']]" "[4]"
json_eq "bad type reported" "d['proof_log_problems'][0]['proof_row']" "5"
expect_no_text "Cancelled row never reported" "W02-01"
expect_exit "match flagged calendar" 0 python3 "$PI/match_proof.py" calendar_flagged.json proof_log.json --config workspace.json --as-of 2026-03-02
json_eq "already flagged slots" "[s.get('already_flagged') for s in d['slots'][1:]]" "[True, True]"
expect_exit "match later run" 0 python3 "$PI/match_proof.py" calendar_flagged.json proof_log.json --config workspace.json --as-of 2026-03-08
json_eq "cut-off passing re-flags the slot" "d['slots'][0]['row_id'], d['slots'][0]['already_flagged'], d['slots'][0]['pending'][0]['cutoff_passed']" "W02-02 False True"

echo "# Writing standards in this area"
EMDASH=$(printf '\342\200\224')
if grep -rn "$EMDASH" "$ROOT/skills/short-form-drafter" "$ROOT/skills/proof-intake" "$FX" ; then
  bad "em dash found"
else
  ok "no em dashes"
fi

echo "passed $PASS, failed $FAIL"
[ "$FAIL" -eq 0 ]

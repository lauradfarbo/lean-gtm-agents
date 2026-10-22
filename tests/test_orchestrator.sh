#!/usr/bin/env bash
# Tests for the weekly-orchestrator scripts against fictional Brightwell fixtures.
# Usage: bash tests/test_orchestrator.sh   (exits non-zero on any failure)
set -u
export PYTHONDONTWRITEBYTECODE=1
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
S="$ROOT/skills/weekly-orchestrator/scripts"
F="$ROOT/tests/fixtures/orchestrator"
CFG="$F/workspace.json"
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
absent() {  # absent <name> <file> <pattern that must not appear>
  if grep -qE -- "$3" "$2"; then echo "FAIL $1: found '$3'"; fails=$((fails + 1)); else echo "ok   $1"; fi
}
py() { python3 -c "$1"; }

# check_draft.py comes from the short-form drafter; the orchestrator keeps a copy for check bundles.
if [ ! -f "$S/check_draft.py" ]; then
  echo "FAIL check_draft.py is missing from $S (copy it from skills/short-form-drafter/scripts)"; fails=$((fails + 1))
fi

# ---- Usage text on missing arguments ----
for s in calendar_writes select_rows plan_check swap_slots visuals make_bundles check_compliance extract_final doc_text; do
  python3 "$S/$s.py" >/dev/null 2>"$TMP/u_$s"; check "$s usage" 2 $? "$TMP/u_$s" "Usage"
done

# ---- select_rows ----
python3 "$S/select_rows.py" "$F/calendar.json" --config "$CFG" --facts "$F/facts.json" --as-of 2026-03-16 \
  --briefs 2026-03-02 > "$TMP/select.json"; check "select_rows runs" 0 $? "$TMP/select.json" '"W04-01"'
py "
import json; d=json.load(open('$TMP/select.json')); a={r['row_id']:r['action'] for r in d['rows']}
want={'W02-02':'overdue','W03-01':'proof','W03-02':'team_owned','W03-03':'blocked','W03-04':'in_review',
      'W03-06':'blocked','W04-01':'draft','W04-02':'proof','W04-03':'proposed','W04-04':'draft','W04-05':'team_owned'}
assert a==want, a
assert d['missed_runs']==['09 MAR 26'], d['missed_runs']
assert [x['row_id'] for x in d['final_text']]==['W02-01']
assert [x['row_id'] for x in d['approved_gaps']]==['W03-04'] and 'Sam Ortega to confirm' in d['approved_gaps'][0]['brief_line']
assert d['same_day_brief'] is False and d['stop'] is False
assert 'cancelled' not in d['counts'] and d['_internal']['cancelled_skipped']==1
blk={r['row_id']:r.get('reason','') for r in d['rows']}
assert blk['W03-06'].startswith('On hold:'), blk['W03-06']
assert 'Sam Ortega to review' in [r for r in d['rows'] if r['row_id']=='W04-03'][0]['reason']
" ; check "select_rows actions, gaps, final text, missed runs" 0 $?
absent "select_rows never names the Cancelled row" "$TMP/select.json" 'W03-05|"Cancelled"'

python3 "$S/select_rows.py" "$F/calendar.json" --config "$CFG" --as-of 2026-03-16 --briefs 2026-03-09,2026-03-16 > "$TMP/same.json"
check "select_rows same-day brief stops the run" 0 $? "$TMP/same.json" '"stop": true'
grep -q '"same_day_brief": true' "$TMP/same.json"; check "select_rows same_day_brief true" 0 $?
python3 "$S/select_rows.py" "$F/calendar.json" --config "$CFG" --as-of 2026-03-16 --briefs 2026-03-16 --rerun > "$TMP/rerun.json"
check "select_rows rerun continues with suffix (2)" 0 $? "$TMP/rerun.json" '"brief_suffix": " \(2\)"'
python3 "$S/select_rows.py" "$F/calendar.json" --config "$CFG" --as-of 2026-03-16 --shadow > "$TMP/shadow_sel.json"
check "select_rows shadow drafts Approved rows" 0 $? "$TMP/shadow_sel.json" '"live_status": "Approved"'
python3 "$S/select_rows.py" "$F/calendar.json" --as-of 2026-03-16 > "$TMP/nocfg.json"
check "select_rows without a config uses defaults" 0 $? "$TMP/nocfg.json" 'The approver to review'

# ---- plan_check ----
python3 "$S/plan_check.py" "$F/calendar.json" "$F/facts.json" "$F/proof_log.json" --config "$CFG" \
  --milestones "$F/milestones.json" --as-of 2026-03-16 > "$TMP/plan.json"; check "plan_check runs" 0 $?
py "
import json; d=json.load(open('$TMP/plan.json'))
notes=[(n['row_id'],n['kind'],n['body']) for n in d['row_notes']]
txt=' '.join(b for _,_,b in notes); br=' '.join(d['brief_risks'])
assert any(r=='W05-01' and 'Partner Win in odd weeks' in b for r,_,b in notes), notes
assert any(r=='W05-05' and 'more than one Poll' in b for r,_,b in notes), notes
assert any(r=='W05-05' and 'Good Friday (UK public holiday)' in b for r,_,b in notes), notes
assert any(r=='W06-01' and 'Easter Monday' in b for r,_,b in notes), notes
assert any(r=='W06-03' and 'Thursday slot rotates' in b for r,_,b in notes), notes
assert any(r=='W03-03' and k=='conditional_swap_date' and '19 MAR 26' in b and '18 MAR 26' in b for r,k,b in notes), notes
assert 'webinar topic (fact E01) is not approved' in br, br
assert 'W06-02 (07 APR 26): no Customer Proof item' in br, br
assert 'Spring Energy Forum' in br and 'W06-04' in br, br
assert 'W03-05' not in txt + br
assert 'Sam Ortega' in txt
assert d['holiday_market']=='UK' and d['notes']==[]
"; check "plan_check cadence, holidays, conditional swap date, dependency, proof, milestone" 0 $?
python3 "$S/plan_check.py" "$F/calendar.json" "$F/facts.json" --config "$CFG" --as-of 2026-03-20 > "$TMP/plan2.json"
check "plan_check dependency past deadline adds a swap note" 0 $? "$TMP/plan2.json" '"kind": "dependency_swap"'
py "
import json; c=json.load(open('$CFG')); c['company']['holiday_market']='DE'; json.dump(c,open('$TMP/ws_de.json','w'))
c2=json.load(open('$CFG')); c2['company'].pop('approver'); c2.pop('plan'); json.dump(c2,open('$TMP/ws_min.json','w'))"
python3 "$S/plan_check.py" "$F/calendar.json" "$F/facts.json" --config "$TMP/ws_de.json" --as-of 2026-03-16 > "$TMP/plan_de.json"
check "plan_check skips holidays for other markets with a note" 0 $? "$TMP/plan_de.json" "Holiday check skipped: no built-in public holidays for market 'DE'"
absent "plan_check DE has no holiday notes" "$TMP/plan_de.json" 'public holiday\)'
python3 "$S/plan_check.py" "$F/calendar.json" "$F/facts.json" --config "$TMP/ws_min.json" --as-of 2026-03-16 > "$TMP/plan_min.json"
check "plan_check with no plan section skips cadence checks" 0 $? "$TMP/plan_min.json" 'The approver'
absent "plan_check minimal config has no cadence notes" "$TMP/plan_min.json" 'odd weeks|rotates'
(cd "$S" && py "
import plan_check as p
from datetime import date
uk, nl, us = p.uk_holidays(2026), p.nl_holidays(2026), p.us_holidays(2026)
assert uk[date(2026,4,3)]=='Good Friday' and uk[date(2026,5,25)]=='Spring bank holiday' and uk[date(2026,12,28)].startswith('Boxing Day')
assert nl[date(2026,4,27)]==\"King's Day\" and nl[date(2026,5,14)]=='Ascension Day' and date(2025,5,5) in p.nl_holidays(2025)
assert us[date(2026,11,26)]=='Thanksgiving Day' and us[date(2026,9,7)]=='Labor Day'
assert p.easter(2027)==date(2027,3,28)
"); check "plan_check built-in US, UK and NL holidays" 0 $?

# ---- swap_slots ----
python3 "$S/swap_slots.py" "$F/calendar.json" "$TMP/select.json" "$F/match.json" --config "$CFG" --as-of 2026-03-16 > "$TMP/swaps.json"
check "swap_slots runs" 0 $?
py "
import json; d=json.load(open('$TMP/swaps.json')); s={x['row_id']:x for x in d['swaps']}
assert set(s)=={'W03-01','W03-03'}, s.keys()
assert s['W03-03']['existing'] and s['W03-03']['type']=='Poll' and s['W03-03']['chapter']=='2'
assert s['W03-03']['conditional'].endswith('by the morning of 18 MAR 26')
n=s['W03-01']; assert not n['existing'] and n['type'] in ('Industry POV','Poll','Guide push')
assert n['chapter']=='3' and '8' not in n['chapters_available'] and '1' not in n['chapters_available']
assert all(x['fallback'] for x in d['swaps'])
"; check "swap_slots candidates, existing proposal, chapters, conditional date" 0 $?
python3 "$S/swap_slots.py" "$F/calendar.json" "$TMP/select.json" "$F/match.json" --config "$CFG" --as-of 2026-03-16 --max-fallbacks 1 > "$TMP/swaps1.json"
py "import json; assert json.load(open('$TMP/swaps1.json'))['fallbacks_skipped']==['W03-03']"
check "swap_slots respects the fallback cap" 0 $?

# ---- visuals ----
python3 "$S/visuals.py" "$F/calendar.json" "$F/assets.txt" "$F/return_W04-01.json" "$F/return_W04-04.json" "$F/return_W04-02.json" \
  --config "$CFG" > "$TMP/vis.json"; check "visuals reports the real-photo clash (exit 1)" 1 $?
py "
import json; d=json.load(open('$TMP/vis.json')); r={x['row_id']:x for x in d['resolved']}
assert r['W04-01']['changed'] and 'dashboard-hero.png' in r['W04-01']['visual'], r
assert r['W04-01']['visual_alternatives']==[]
assert r['W04-04']['visual'].startswith('Needed: ImageGen image of') and not r['W04-04']['changed']
assert [u['row_id'] for u in d['unresolved']]==['W04-02'] and 'Real photo' in d['unresolved'][0]['reason']
"; check "visuals skips the Cancelled row's file, keeps the AI image, flags real-photo rows" 0 $?
py "
import json; c=json.load(open('$CFG')); c['visuals']['ai_image_tool']=None; json.dump(c,open('$TMP/ws_noai.json','w'))
r=json.load(open('$F/return_W04-01.json')); r['visual_alternatives']=[]; r['row_id']='W04-01'; json.dump(r,open('$TMP/W04-01.json','w'))"
python3 "$S/visuals.py" "$F/calendar.json" "$F/assets.txt" "$TMP/W04-01.json" --config "$TMP/ws_noai.json" > "$TMP/vis_noai.json"
check "visuals without an AI image tool asks for a photo or graphic" 0 $? "$TMP/vis_noai.json" 'Needed: photo or graphic'

# ---- make_bundles ----
RUN="$TMP/run"; SH="$RUN/shared"; mkdir -p "$SH"
for f in workspace.json calendar.json proof_log.json facts.json rules.md plan_rules.md voice.md assets.txt long_form.md brightwell-chapter-map.md milestones.json; do cp "$F/$f" "$SH/"; done
python3 "$S/make_bundles.py" "$RUN" "$ROOT" plan > "$TMP/mb_plan.json"; check "make_bundles plan" 0 $?
for f in workspace.json plan_check.py milestones.json calendar.json; do
  [ -f "$RUN/plan/$f" ]; check "plan bundle has $f" 0 $?
done
python3 "$S/make_bundles.py" "$RUN" "$ROOT" draft --rows W04-01 > /dev/null; check "make_bundles draft" 0 $?
for f in workspace.json row.json long_form.md chapter-map.md facts_approved.json recent.txt visuals_recent.txt assets.txt; do
  [ -f "$RUN/draft/W04-01/$f" ]; check "draft bundle has $f" 0 $?
done
[ ! -f "$RUN/draft/W04-01/guide.md" ]; check "draft bundle has no guide.md" 0 $?
grep -q "map for drafters" "$RUN/draft/W04-01/chapter-map.md"; check "chapter map copied from the config-named file" 0 $?
py "
import json; f=json.load(open('$SH/facts_approved.json'))
assert [x['id'] for x in f]==['A01','A04','C02'] and set(f[0])=={'id','claim','comments'}, f
"; check "facts_approved.json has approved facts only" 0 $?
absent "visuals_recent.txt skips the Cancelled row" "$RUN/draft/W04-01/visuals_recent.txt" 'W03-05'
grep -q "W02-01" "$RUN/draft/W04-01/visuals_recent.txt"; check "visuals_recent.txt lists rows in the window" 0 $?
python3 "$S/make_bundles.py" "$RUN" "$ROOT" proof --rows W03-01 --proof-rows 2 > /dev/null; check "make_bundles proof" 0 $?
grep -q "Northgate" "$RUN/proof/W03-01/proof_item.json" && [ -f "$RUN/proof/W03-01/workspace.json" ]; check "proof bundle has proof item and workspace.json" 0 $?
python3 "$S/make_bundles.py" "$RUN" "$ROOT" draft --rows W03-04 --shadow > /dev/null
grep -q '"Live status": "Approved"' "$RUN/draft/W03-04/row.json"; check "make_bundles shadow keeps the live status" 0 $?
py "
import json; d=json.load(open('$TMP/swaps.json'))
for x in d['swaps']: x['angle']=x.get('angle') or 'Why one dashboard beats twelve spreadsheets'
json.dump(d,open('$TMP/swaps_final.json','w'))"
python3 "$S/make_bundles.py" "$RUN" "$ROOT" fallback --rows W03-01 --swaps "$TMP/swaps_final.json" > /dev/null; check "make_bundles fallback" 0 $?
py "
import json; r=json.load(open('$RUN/fallback/W03-01/row.json')); fb=json.load(open('$RUN/fallback/W03-01/fallback.json'))
assert r['Status']=='Planned' and r['Title / angle'].startswith('Why one dashboard') and 'Guide ch3' in r['Spec'], r
assert 'Sam Ortega decides' in fb['note'] and fb['chapter']=='3'
"; check "fallback bundle carries the swap, not the original row" 0 $?
python3 "$S/make_bundles.py" "$RUN" "$ROOT" check --draft "$F/draft_pass.json" > /dev/null; check "make_bundles check (pass draft)" 0 $?
python3 "$S/make_bundles.py" "$RUN" "$ROOT" check --draft "$F/draft_fail.json" > /dev/null; check "make_bundles check (fail draft)" 0 $?
for f in workspace.json draft.json check_compliance.py check_draft.py assets.txt visuals_recent.txt facts.json; do
  [ -f "$RUN/check/W04-01/$f" ]; check "check bundle has $f" 0 $?
done
echo '{"row_id":"W04-01"}' > "$TMP/prev.json"; echo '[{"n":1,"fix":"x"}]' > "$TMP/fixes.json"
python3 "$S/make_bundles.py" "$RUN" "$ROOT" redraft --from draft/W04-01 --previous "$TMP/prev.json" --fixes "$TMP/fixes.json" > /dev/null
[ -f "$RUN/redraft/W04-01-2/fixes.json" ] && [ -f "$RUN/redraft/W04-01-2/workspace.json" ]; check "make_bundles redraft" 0 $?

# ---- check_compliance (run from the check bundle, as the checker agent does) ----
B="$RUN/check/W04-01"
python3 "$B/check_compliance.py" "$B/draft.json" "$B/facts.json" --config "$B/workspace.json" > "$TMP/cc_pass.json"
check "check_compliance passes a clean draft" 0 $? "$TMP/cc_pass.json" '"pass": true'
B2="$RUN/check/W04-04"
python3 "$B2/check_compliance.py" "$B2/draft.json" "$B2/facts.json" --config "$B2/workspace.json" > "$TMP/cc_fail.json"
check "check_compliance fails a bad draft" 1 $? "$TMP/cc_fail.json" '"pass": false'
py "
import json; d=json.load(open('$TMP/cc_fail.json')); t=json.dumps(d)
rules=[f['rule'] for f in d['fixes']]
assert 'R-01' in rules, rules
assert 'Competitors' in rules, rules
assert 'Product timing' in rules, rules
assert any('X09' in f['issue'] for f in d['fixes']), t
assert any(\"Figure '75%'\" in f['issue'] for f in d['fixes']), t
assert any('alternate hook' in f['issue'] for f in d['fixes']), t
assert any('meter-room.jpg' in f['issue'] for f in d['fixes']), t
"; check "check_compliance fixes: custom rule, competitor, timing, fact, figure, hook, repeat visual" 0 $?
python3 "$B/check_compliance.py" "$B/draft.json" "$B/facts.json" > "$TMP/cc_auto.json"
check "check_compliance finds workspace.json in its bundle" 0 $? "$TMP/cc_auto.json" '"pass": true'

# ---- calendar_writes: plan, guard, verify, shadow ----
python3 "$S/calendar_writes.py" plan "$F/calendar.json" "$F/writes.json" --config "$CFG" > "$TMP/cw_plan.json"
check "calendar_writes plan accepts allowed writes" 0 $? "$TMP/cw_plan.json" '"Calendar!B4:B12"'
py "
import json; d=json.load(open('$TMP/cw_plan.json')); a={(x['row_id'],x['col']):x['value'] for x in d['accepted']}
assert a[('W04-01','Status')]=='Draft ready' and a[('W03-01','Title / angle')].startswith('Partner news:')
assert d['guard_ranges']==['Calendar!B4:B12','Calendar!J4:M12'], d['guard_ranges']
"; check "calendar_writes plan values and guard ranges" 0 $?
python3 "$S/calendar_writes.py" plan "$F/calendar.json" "$F/writes_bad.json" --config "$CFG" > "$TMP/cw_bad.json"
check "calendar_writes plan refuses locked writes (exit 1)" 1 $?
py "
import json; d=json.load(open('$TMP/cw_bad.json'))
assert not d['accepted'] and len(d['refused'])==5, d
r=' '.join(x['reason'] for x in d['refused'])
assert 'locked' in r and 'only to Draft ready' in r and 'Cancelled' in r and 'proof placeholder' in r and 'does not exist' in r
"; check "calendar_writes refusal reasons" 0 $?

mkfresh() {  # mkfresh <out prefix> <python edits on rows (list of dicts keyed by header)>
  py "
import json
v=json.load(open('$F/calendar.json'))['values']; h=v[0]; rows=[dict(zip(h,r)) for r in v[1:]]
$2
g=[[r[k] for k in h] for r in rows]
b=[[g[i-2][h.index('Status')]] for i in range(4,13)]
jm=[g[i-2][h.index('Notes'):h.index('Row ID')+1] for i in range(4,13)]
json.dump({'range':'Calendar!B4:B12','values':b},open('$1_b.json','w'))
json.dump({'range':'Calendar!J4:M12','values':jm},open('$1_jm.json','w'))"
}
mkfresh "$TMP/clean" "pass"
python3 "$S/calendar_writes.py" guard "$F/calendar.json" "$F/writes.json" "$TMP/clean_b.json" "$TMP/clean_jm.json" --config "$CFG" > "$TMP/guard.json"
check "guard: clean fresh read accepts every write" 0 $? "$TMP/guard.json" '"refused": \[\]'
mkfresh "$TMP/moved" "rows.pop(7)"   # a person deleted W03-06 (row 9): rows below shift up
python3 "$S/calendar_writes.py" guard "$F/calendar.json" "$F/writes.json" "$TMP/moved_b.json" "$TMP/moved_jm.json" --config "$CFG" > "$TMP/guard_moved.json"
check "guard: row moved is refused (exit 1)" 1 $? "$TMP/guard_moved.json" 'Row ID changed: expected W04-01'
mkfresh "$TMP/status" "rows[2]['Status']='Cancelled'"   # a person cancelled W03-01 (row 4)
python3 "$S/calendar_writes.py" guard "$F/calendar.json" "$F/writes.json" "$TMP/status_b.json" "$TMP/status_jm.json" --config "$CFG" > "$TMP/guard_status.json"
check "guard: status changed is refused (exit 1)" 1 $? "$TMP/guard_status.json" "Status changed during the run \('Planned' to 'Cancelled'\)"
mkfresh "$TMP/note" "rows[10]['Notes']='Sam: keep this one.'"   # a person wrote a note on W04-03 (row 12)
python3 "$S/calendar_writes.py" guard "$F/calendar.json" "$F/writes.json" "$TMP/note_b.json" "$TMP/note_jm.json" --config "$CFG" > "$TMP/guard_note.json"
check "guard: a person's note is kept and the new note appended" 0 $? "$TMP/guard_note.json" 'Sam: keep this one. Orchestrator 16 MAR 26: due 25 MAR 26'

apply() {  # apply <guard.json> <out after.json> [extra python]
  py "
import json
v=json.load(open('$F/calendar.json'))['values']; h=v[0]
for a in json.load(open('$1'))['accepted']:
    v[a['row']-1][h.index(a['col'])]=a['value']
${3:-}
json.dump({'values':v},open('$2','w'))"
}
apply "$TMP/guard.json" "$TMP/after.json"
python3 "$S/calendar_writes.py" verify "$F/calendar.json" "$TMP/after.json" "$F/writes.json" --guard "$TMP/guard.json" --config "$CFG" > "$TMP/verify.json"
check "verify: clean read-back" 0 $? "$TMP/verify.json" '"unexpected_changes": \[\]'
apply "$TMP/guard.json" "$TMP/after_bad.json" "v[14][h.index('Date')]='Wed 25 MAR 26'"
python3 "$S/calendar_writes.py" verify "$F/calendar.json" "$TMP/after_bad.json" "$F/writes.json" --guard "$TMP/guard.json" --config "$CFG" > "$TMP/verify_bad.json"
check "verify: unexpected change is reported (exit 1)" 1 $? "$TMP/verify_bad.json" '"cell": "A15"'
apply "$TMP/guard.json" "$TMP/after_del.json" "v.pop(8)"
python3 "$S/calendar_writes.py" verify "$F/calendar.json" "$TMP/after_del.json" "$F/writes.json" --guard "$TMP/guard.json" --config "$CFG" > "$TMP/verify_del.json"
check "verify: deleted row reported (exit 1)" 1 $?
py "import json; d=json.load(open('$TMP/verify_del.json')); assert d['deleted_row_ids']==['W03-06'] and not d['unexpected_changes'], d"
check "verify: deleted row reported once by Row ID, no shifted cells" 0 $?
python3 "$S/calendar_writes.py" verify "$F/calendar.json" "$F/calendar.json" "$F/writes.json" --config "$CFG" > "$TMP/verify_nw.json"
check "verify: writes missing from the read-back (exit 1)" 1 $?
py "import json; assert len(json.load(open('$TMP/verify_nw.json'))['not_written'])==6"
check "verify: every missing write listed" 0 $?

python3 "$S/calendar_writes.py" shadow "$F/calendar.json" "$F/writes.json" --config "$CFG" > "$TMP/shadow.json"
check "shadow lists would-be writes" 0 $? "$TMP/shadow.json" 'W04-01 Status: Draft ready'
python3 "$S/calendar_writes.py" shadow "$F/calendar.json" "$F/writes_bad.json" --config "$CFG" > "$TMP/shadow_bad.json"
check "shadow lists would-be refusals" 0 $? "$TMP/shadow_bad.json" 'would be refused'
py "
import json; d=json.load(open('$TMP/shadow_bad.json'))
assert not any('W03-05' in l or 'Cancelled' in l for l in d['brief_lines']), d['brief_lines']
"; check "shadow brief lines never mention the Cancelled row" 0 $?
python3 "$S/calendar_writes.py" verify "$F/calendar.json" "$F/calendar.json" --shadow --config "$CFG" > "$TMP/verify_sh.json"
check "verify --shadow: no change" 0 $? "$TMP/verify_sh.json" '"unexpected_changes": \[\]'
python3 "$S/calendar_writes.py" verify "$F/calendar.json" "$TMP/after.json" --shadow --config "$CFG" > "$TMP/verify_sh2.json"
check "verify --shadow: any change is reported (exit 1)" 1 $?

# ---- doc_text and extract_final ----
python3 "$S/doc_text.py" "$F/docs.json" "$TMP/doc.md" --expect "End of draft" > "$TMP/dt.json"
check "doc_text extracts tabs and tables" 0 $? "$TMP/doc.md" 'Fact \| A01'
python3 "$S/doc_text.py" "$F/docs.json" "$TMP/doc2.md" --expect "Pre-publish checklist" > "$TMP/dt2.json"
check "doc_text flags a cut-off doc (exit 1)" 1 $? "$TMP/dt2.json" 'MISSING'
python3 "$S/extract_final.py" "$F/docs.json" "https://docs.example.com/d/TEST-drafts-002?tab=t.w0401" > "$TMP/ef.json"
check "extract_final returns the text above the dashed line" 0 $? "$TMP/ef.json" '"final_text": "Final post text line one.\\nLine two."'
python3 "$S/extract_final.py" "$F/docs.json" "t.nope" > "$TMP/ef2.json"
check "extract_final reports a missing tab (exit 1)" 1 $? "$TMP/ef2.json" 'not found'

echo
if [ "$fails" -eq 0 ]; then echo "All orchestrator tests passed."; else echo "$fails orchestrator test(s) failed."; fi
[ "$fails" -eq 0 ]

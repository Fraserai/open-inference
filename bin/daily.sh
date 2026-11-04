#!/bin/zsh
# Build the daily Open Inference report and commit it locally (no remote).
#   bin/daily.sh            run now
#   bin/daily.sh --if-due   what launchd runs (6pm Brisbane and at login): skips if today's
#                           report exists, or if it's before 6pm and yesterday's exists, so a
#                           run missed while the Mac was off is caught up at the next login.
set -e
cd "${0:A:h}/.."
PY=/Library/Frameworks/Python.framework/Versions/3.11/bin/python3
[[ -x $PY ]] || PY=python3
TODAY=$(TZ=Australia/Brisbane date +%F)
YESTERDAY=$(TZ=Australia/Brisbane date -v-1d +%F)
HOUR=$(TZ=Australia/Brisbane date +%H)

if [[ "$1" == "--if-due" ]]; then
  [[ -f reports/$TODAY.md ]] && exit 0
  (( 10#$HOUR < 18 )) && [[ -f reports/$YESTERDAY.md ]] && exit 0
fi
LOCK=data/daily.lock
if ! mkdir $LOCK 2>/dev/null; then echo "already running"; exit 0; fi
trap 'rmdir $LOCK' EXIT

echo "== $(date '+%Y-%m-%d %H:%M') daily report"
$PY -m unittest discover -s tests -q
$PY -m tracker
git add data reports
git diff --cached --quiet || git commit -q -m "Daily report $TODAY"
echo "done"

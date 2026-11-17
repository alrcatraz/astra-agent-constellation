#!/bin/bash
# Blueprint publication guard: the blueprint is a concept document and must
# carry zero fleet-private facts. Run before every commit/push.
set -e
words="angelia iris eunomia tyche astralab HomeCentre01 SUSETLearn00 BuildCentre01 HC01 ds425plus nb.internal fleet-constellation harmonia"
fail=0
for w in $words; do
  hits=$(git grep -li "$w" -- . 2>/dev/null | grep -v scripts/check-privacy.sh | head -3)
  if [ -n "$hits" ]; then
    echo "PRIVACY: \"$w\" found in:"; echo "$hits"; fail=1
  fi
done
[ $fail -eq 0 ] && echo "privacy check: clean"
exit $fail

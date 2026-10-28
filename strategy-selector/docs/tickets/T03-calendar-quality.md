# T03 Calendar + quality + coverage
- NYSE calendar (holidays/early closes); timestamps → America/New_York
- `cli data check`: missing minutes, zero-volume days, split-like jumps, duplicates → bad_days (flag, not delete)
- Coverage per symbol; short history → `learn=false`
Accept: compact table. Test (justified): early-close session end.

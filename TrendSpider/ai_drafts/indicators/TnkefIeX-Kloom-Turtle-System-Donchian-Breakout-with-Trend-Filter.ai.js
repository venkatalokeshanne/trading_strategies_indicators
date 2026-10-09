describe_indicator('Kloom Turtle System', 'price');

// ── Inputs ──────────────────────────────────────────────────────────────────
const mySysTab = input.tab('Turtle System');
const myEntryLen = mySysTab.number('Entry length', 20, { min: 5, max: 200 });
const myExitLen = mySysTab.number('Exit length', 10, { min: 3, max: 100 });
const myUseTrend = mySysTab.boolean('Trend EMA filter', true);
const myTrendLen = mySysTab.number('Trend EMA length', 200, { min: 20, max: 500 });

const myVizTab = input.tab('Display');
const myShowCh = myVizTab.boolean('Show channels', true);
const myShowSig = myVizTab.boolean('Show markers', true);

// ── Donchian channels, computed off the PREVIOUS bar (classic Turtle logic) ──
const myEntryHi = shift(highest(high, myEntryLen), 1);
const myEntryLo = shift(lowest(low, myEntryLen), 1);
const myExitHi = shift(highest(high, myExitLen), 1);
const myExitLo = shift(lowest(low, myExitLen), 1);

const myTrendEma = ema(close, myTrendLen);

const myLongOk = myUseTrend
	? for_every(close, myTrendEma, (_c, _e) => _c > _e)
	: for_every(close, (_c) => true);

const myShortOk = myUseTrend
	? for_every(close, myTrendEma, (_c, _e) => _c < _e)
	: for_every(close, (_c) => true);

// ── Position state machine (sequential, depends on previous bar's position) ──
// pos: 1 = long, -1 = short, 0 = flat. Starts flat (pos = 0 on the first bar).
const myPos = for_every(high, low, myLongOk, myShortOk, myEntryHi, myEntryLo, myExitHi, myExitLo,
	(_h, _l, _lok, _sok, _eHi, _eLo, _xHi, _xLo, _prevPos, _idx) => {
		const myPrevPosValue = _idx === 0 ? 0 : (_prevPos || 0);
		const myLongEntry = _h > _eHi && _lok && myPrevPosValue <= 0;
		const myShortEntry = _l < _eLo && _sok && myPrevPosValue >= 0;
		const myLongExit = myPrevPosValue === 1 && _l < _xLo;
		const myShortExit = myPrevPosValue === -1 && _h > _xHi;

		if (myLongEntry) {
			return 1;
		}
		else if (myShortEntry) {
			return -1;
		}
		else if (myLongExit || myShortExit) {
			return 0;
		}
		return myPrevPosValue;
	});

// previous bar's position, needed to re-derive the exact same entry/exit flags
const myPrevPosSeries = shift(myPos, 1);

const myLongEntryFlag = for_every(high, myEntryHi, myLongOk, myPrevPosSeries,
	(_h, _eHi, _lok, _p) => _h > _eHi && _lok && (_p || 0) <= 0);

const myShortEntryFlag = for_every(low, myEntryLo, myShortOk, myPrevPosSeries,
	(_l, _eLo, _sok, _p) => _l < _eLo && _sok && (_p || 0) >= 0);

const myLongExitFlag = for_every(low, myExitLo, myPrevPosSeries,
	(_l, _xLo, _p) => (_p || 0) === 1 && _l < _xLo);

const myShortExitFlag = for_every(high, myExitHi, myPrevPosSeries,
	(_h, _xHi, _p) => (_p || 0) === -1 && _h > _xHi);

const myExitFlag = for_every(myLongExitFlag, myShortExitFlag, (_le, _se) => _le || _se);

// ── Channels and Trend EMA ───────────────────────────────────────────────────
const myEntryHiToPaint = myShowCh ? myEntryHi : constants.empty_series;
const myEntryLoToPaint = myShowCh ? myEntryLo : constants.empty_series;
const myExitHiToPaint = myShowCh ? myExitHi : constants.empty_series;
const myExitLoToPaint = myShowCh ? myExitLo : constants.empty_series;
const myTrendEmaToPaint = myUseTrend ? myTrendEma : constants.empty_series;

const myEntryHiPainted = paint(myEntryHiToPaint, { name: 'Entry High', color: 'teal', style: 'line' });
const myEntryLoPainted = paint(myEntryLoToPaint, { name: 'Entry Low', color: 'teal', style: 'line' });
fill(myEntryHiPainted, myEntryLoPainted, 'teal', 0.06);

paint(myExitHiToPaint, { name: 'Exit High', color: 'orange', style: 'dotted' });
paint(myExitLoToPaint, { name: 'Exit Low', color: 'orange', style: 'dotted' });
paint(myTrendEmaToPaint, { name: 'Trend EMA', color: 'gray', thickness: 2 });

// ── Entry and exit markers ────────────────────────────────────────────────────
const myLongMarks = for_every(myLongEntryFlag, _f => _f ? 1 : null);
const myShortMarks = for_every(myShortEntryFlag, _f => _f ? 1 : null);
const myExitMarks = for_every(myExitFlag, _f => _f ? 1 : null);

// Note: paint() and register_signal() names share one namespace, so names used
// here (Long Entry Marker, etc.) are kept distinct from the register_signal()
// names below (Long Entry Signal, etc.) to avoid "already exists" errors.
paint(myShowSig ? myLongMarks : constants.empty_series, { name: 'Long Entry Marker', style: 'labels_below', color: 'teal' });
paint(myShowSig ? myShortMarks : constants.empty_series, { name: 'Short Entry Marker', style: 'labels_above', color: 'red' });
paint(myShowSig ? myExitMarks : constants.empty_series, { name: 'Exit Signal Marker', style: 'labels_above', color: 'orange' });

// ── Visual scripting signals ─────────────────────────────────────────────────
register_signal(myLongEntryFlag, 'Long Entry Signal');
register_signal(myShortEntryFlag, 'Short Entry Signal');
register_signal(myLongExitFlag, 'Long Exit Signal');
register_signal(myShortExitFlag, 'Short Exit Signal');
register_signal(myExitFlag, 'Any Exit Signal');
register_signal(for_every(myPos, _p => _p === 1), 'Is Long');
register_signal(for_every(myPos, _p => _p === -1), 'Is Short');
register_signal(for_every(myPos, _p => _p === 0), 'Is Flat');
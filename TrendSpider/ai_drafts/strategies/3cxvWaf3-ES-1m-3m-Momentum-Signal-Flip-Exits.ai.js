describe_indicator('ES 3m Momentum - Signal Flip (Indicator)', 'price');

// NOTE: TrendSpider Custom JS indicators cannot place trades, manage
// positions, exits, limit orders or flatten positions at EOD. Pine's
// strategy.* calls (entries, partial TP exits, EOD flatten) cannot be
// reproduced here. This script reproduces the exact Pine SIGNAL LOGIC
// (EMAs, RSI smoothing, MACD confirmation, volume filter, RTH session
// filter, crossover/crossunder entries) and exposes Long/Short entry
// signals via register_signal() for use in scanners/alerts/backtests.

const myMoment = library('moment-timezone');

// Renamed tab, since "Inputs" is a reserved tab name on the platform
const myTab = input.tab('Settings');

const myEmaGroup = myTab.group('EMAs');
const myEmaFast = myEmaGroup.number('Fast EMA', 8, { min: 1, max: 200 });
const myEmaSlow = myEmaGroup.number('Slow EMA', 21, { min: 1, max: 300 });
const myEmaFilter = myEmaGroup.number('Trend Filter EMA', 50, { min: 1, max: 500 });

const myRsiGroup = myTab.group('RSI');
const myRsiLen = myRsiGroup.number('RSI Length', 14, { min: 2, max: 100 });
const myRsiSmooth = myRsiGroup.number('RSI Smooth', 3, { min: 1, max: 50 });

const myVolGroup = myTab.group('Volume');
const myVolMult = myVolGroup.number('Min Volume vs MA mult', 1.2, { min: 0.1, max: 10, step: 0.1 });
const myVolLen = myVolGroup.number('Volume MA Length', 20, { min: 5, max: 300 });

const mySessionGroup = myTab.group('Session');
const myTradeDir = mySessionGroup.select('Direction', 'Both', ['Long', 'Short', 'Both']);
const myRthOnly = mySessionGroup.boolean('RTH only (08:30-15:00 CT)', true);

// ── Indicators ──────────────────────────────────────────────────────────
const myFast = ema(close, myEmaFast);
const mySlow = ema(close, myEmaSlow);
const myTrend = ema(close, myEmaFilter);

const myRsiRaw = rsi(close, myRsiLen);
const myRsi = ema(myRsiRaw, myRsiSmooth);

const myVolMA = sma(volume, myVolLen);

// MACD-style momentum confirmation (Pine: ta.macd(close, fast, slow, smooth))
const myMacdLine = sub(ema(close, myEmaFast), ema(close, myEmaSlow));
const mySignalLine = ema(myMacdLine, myRsiSmooth);

// ── RTH session filter (America/Chicago 08:30-15:00) ─────────────────────
const myInRTH = time.map(_t => {
	if (!myRthOnly) {
		return true;
	}
	const myLocalTime = myMoment.tz(_t * 1000, 'America/Chicago');
	const myMinutesOfDay = myLocalTime.hours() * 60 + myLocalTime.minutes();
	return myMinutesOfDay >= (8 * 60 + 30) && myMinutesOfDay <= (15 * 60);
});

// ── Filters ───────────────────────────────────────────────────────────────
const myAboveTrend = for_every(close, myTrend, (_c, _t) => _c > _t);
const myBelowTrend = for_every(close, myTrend, (_c, _t) => _c < _t);

const myRsiLong = for_every(myRsi, _r => _r > 50);
const myRsiShort = for_every(myRsi, _r => _r < 50);

const myVolOK = for_every(volume, myVolMA, (_v, _vma) => _v > _vma * myVolMult);

const myMacdBull = for_every(myMacdLine, mySignalLine, (_m, _s) => _m > _s);
const myMacdBear = for_every(myMacdLine, mySignalLine, (_m, _s) => _m < _s);

// ── Crossover / Crossunder of Fast vs Slow EMA ──────────────────────────
const myCrossOver = for_every(myFast, mySlow, (_f, _s, _prev, _idx) => {
	if (_idx === 0) {
		return false;
	}
	return _f > _s && myFast[_idx - 1] <= mySlow[_idx - 1];
});

const myCrossUnder = for_every(myFast, mySlow, (_f, _s, _prev, _idx) => {
	if (_idx === 0) {
		return false;
	}
	return _f < _s && myFast[_idx - 1] >= mySlow[_idx - 1];
});

// ── Entry conditions ─────────────────────────────────────────────────────
const myLongEntryRaw = for_every(
	myCrossOver, myAboveTrend, myRsiLong, myMacdBull, myVolOK, myInRTH,
	(_co, _at, _rl, _mb, _vo, _rth) => _co && _at && _rl && _mb && _vo && _rth
);

const myShortEntryRaw = for_every(
	myCrossUnder, myBelowTrend, myRsiShort, myMacdBear, myVolOK, myInRTH,
	(_cu, _bt, _rs, _mb, _vo, _rth) => _cu && _bt && _rs && _mb && _vo && _rth
);

const myLongEntry = for_every(myLongEntryRaw, _l => _l && (myTradeDir === 'Long' || myTradeDir === 'Both'));
const myShortEntry = for_every(myShortEntryRaw, _s => _s && (myTradeDir === 'Short' || myTradeDir === 'Both'));

// ── Plots ────────────────────────────────────────────────────────────────
paint(myFast, { name: 'EMA Fast', color: '#00BCD4', thickness: 1 });
paint(mySlow, { name: 'EMA Slow', color: '#FF9800', thickness: 2 });
paint(myTrend, { name: 'EMA Trend', color: '#9E9E9E', thickness: 2, style: 'ladder' });

const myLongMarks = for_every(myLongEntry, low, (_l, _lo) => _l ? _lo : null);
const myShortMarks = for_every(myShortEntry, high, (_s, _hi) => _s ? _hi : null);

paint(myLongMarks, { name: 'Long Entry', style: 'labels_below', color: 'lime' });
paint(myShortMarks, { name: 'Short Entry', style: 'labels_above', color: 'red' });

// ── Bar coloring by trend/momentum ─────────────────────────────────────
const myBarColors = for_every(myAboveTrend, myBelowTrend, myRsiLong, myRsiShort, (_at, _bt, _rl, _rs) => {
	if (_at && _rl) {
		return 'rgba(0,255,0,0.4)';
	}
	if (_bt && _rs) {
		return 'rgba(255,0,0,0.4)';
	}
	return null;
});
color_candles(myBarColors);

// ── Signals for scanners / alerts / strategy tester ─────────────────────
// Renamed signal names to avoid a name collision with a line already
// painted as "Long Entry" / "Short Entry" above (labels_below/labels_above
// marks), which was the root cause of the "already exists" error.
register_signal(myLongEntry, 'Long Entry Signal');
register_signal(myShortEntry, 'Short Entry Signal');
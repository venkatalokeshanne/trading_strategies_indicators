describe_indicator('EMA Ride V2 Strategy', 'price');

// NOTE: TrendSpider custom indicators cannot execute a backtesting
// engine (no strategy.entry/strategy.close equivalents). This script
// reproduces the Pine Script math and signal logic exactly, and
// simulates the strategy position state (flat/long) using the same
// entry/exit rules, so entry and exit bars match the Pine strategy.

const myEmaTab = input.tab('EMA Settings');
const myLen9 = myEmaTab.number('EMA9', 9, { min: 1, max: 500 });
const myLen21 = myEmaTab.number('EMA21', 21, { min: 1, max: 500 });
const myLen50 = myEmaTab.number('EMA50', 50, { min: 1, max: 500 });

const myStratTab = input.tab('Strategy Settings');
const myMinWeeks = myStratTab.number('Min Weeks on EMA21', 4, { min: 1, max: 100 });
const myDipPct = myStratTab.number('Entry Dip % above EMA9', 3.0, { min: 0, max: 100 });
const myMinBounces = myStratTab.number('Min Bounces (90 bars)', 2, { min: 0, max: 90 });
// shortened title, since the full one exceeded the input name length limit
const myMinPctEma9 = myStratTab.number('Min % Above EMA9', 60.0, { min: 0, max: 100 });
const myMinAtrPct = myStratTab.number('Min ATR %', 3.0, { min: 0, max: 100 });
const myMin52wlPct = myStratTab.number('Min % above 52W Low', 50.0, { min: 0, max: 1000 });

const myExitTab = input.tab('Exit Settings');
const myExitMode = myExitTab.select('Exit Mode', 'EMA21 Close', ['EMA21 Close', 'EMA9 Trail', 'Both']);

// ═══════════════════════════════════════════
// CORE CALCULATIONS
// ═══════════════════════════════════════════
const myEma9 = ema(close, myLen9);
const myEma21 = ema(close, myLen21);
const myEma50 = ema(close, myLen50);

// EMA Stack
const myStack = for_every(myEma9, myEma21, myEma50, (_e9, _e21, _e50) => _e9 > _e21 && _e21 > _e50);

// Consecutive bars above EMA21 (stateful counter, same as Pine's var int)
const myBarsEma21 = for_every(close, myEma21, (_c, _e21, _prev, _i) => {
	const myPrevCount = _i === 0 ? 0 : (_prev || 0);
	return _c > _e21 ? myPrevCount + 1 : 0;
});

// % of last 60 bars above EMA9
const myAboveEma9Flag = for_every(close, myEma9, (_c, _e9) => _c > _e9 ? 1 : 0);
const myEma9Above60 = sum(myAboveEma9Flag, 60);
const myEma9PctAbove = mult(div(myEma9Above60, 60), 100);

// Cloud bounces in last 90 bars
const myGenuineBounce = for_every(low, myEma21, close, myEma9, (_l, _e21, _c, _e9) => {
	const myCloudTested = _l <= _e21 * 1.02;
	const myCloudBounced = _c > _e9;
	return (myCloudTested && myCloudBounced) ? 1 : 0;
});
const myBounces90 = sum(myGenuineBounce, 90);

// Distance from EMA9
const myDistEma9 = mult(div(sub(close, myEma9), myEma9), 100);

// EMA9 rising (compared to 3 bars ago)
const myEma9Rising = for_every(myEma9, shift(myEma9, 3), (_e9, _e9prev3) => _e9 > _e9prev3);

// Min bars from weeks
const myMinBars = myMinWeeks * 5;

// ATR % (V2)
const myAtr14 = atr(high, low, close, 14);
const myAtrPct = mult(div(myAtr14, close), 100);

// % above 52-week low (V2)
const myLow52 = lowest(low, 252);
const myPct52wl = mult(div(sub(close, myLow52), myLow52), 100);

// ═══════════════════════════════════════════
// ENTRY CONDITIONS
// ═══════════════════════════════════════════

// Long ride established
const myLongRide = for_every(myBarsEma21, myEma9PctAbove, myBounces90, myStack, (_b21, _pctAbove, _bounces, _stack) =>
	(_b21 >= myMinBars) && (_pctAbove >= myMinPctEma9) && (_bounces >= myMinBounces) && _stack);

// At EMA9 dip right now
const myAtDip = for_every(myDistEma9, myBarsEma21, myBounces90, myStack, myEma9Rising, (_dist, _b21, _bounces, _stack, _rising) =>
	(_dist >= 0) && (_dist <= myDipPct) && (_b21 >= myMinBars) && (_bounces >= myMinBounces) && _stack && _rising);

// VCPSwing quality filters
const myVcpsPass = for_every(myAtrPct, myPct52wl, myStack, (_atrPct, _pct52wl, _stack) =>
	(_atrPct >= myMinAtrPct) && (_pct52wl >= myMin52wlPct) && _stack);

// Final entry signal
const myEntrySignal = for_every(myAtDip, myVcpsPass, (_dip, _vcps) => _dip && _vcps);

// ═══════════════════════════════════════════
// EXIT CONDITIONS
// ═══════════════════════════════════════════
const myExitEma21 = for_every(close, myEma21, (_c, _e21) => _c < _e21);
const myExitEma9 = for_every(close, myEma9, (_c, _e9) => _c < _e9);

const myDoExit = for_every(myExitEma21, myExitEma9, (_x21, _x9) => {
	if (myExitMode === 'EMA21 Close') return _x21;
	if (myExitMode === 'EMA9 Trail') return _x9;
	return _x21 || _x9;
});

// ═══════════════════════════════════════════
// STRATEGY POSITION SIMULATION
// Mirrors strategy.position_size > 0 / == 0 logic
// ═══════════════════════════════════════════
const myPositionState = for_every(myEntrySignal, myDoExit, (_entry, _exit, _prevPos, _i) => {
	const myPrevPos = _i === 0 ? 0 : (_prevPos || 0);
	if (myPrevPos > 0) {
		return _exit ? 0 : 1;
	}
	return _entry ? 1 : 0;
});

const myPrevPositionState = shift(myPositionState, 1);
const myEntryTrigger = for_every(myPositionState, myPrevPositionState, (_pos, _prevPos) => _pos > 0 && !((_prevPos || 0) > 0));
const myExitTrigger = for_every(myPositionState, myPrevPositionState, (_pos, _prevPos) => _pos === 0 && (_prevPos || 0) > 0);

// ═══════════════════════════════════════════
// VISUALS
// ═══════════════════════════════════════════
const myEma9LinePainted = paint(myEma9, { name: 'EMA9', color: '#2ecc71', thickness: 1 });
const myEma21LinePainted = paint(myEma21, { name: 'EMA21', color: '#3498db', thickness: 1 });
paint(myEma50, { name: 'EMA50', color: '#e67e22', thickness: 1, forceUsePriceAxis: true });

fill(myEma9LinePainted, myEma21LinePainted, 'green', 0.15);

const myEntryMarker = for_every(myEntryTrigger, low, (_e, _l) => _e ? _l : null);
const myExitMarker = for_every(myExitTrigger, high, (_x, _h) => _x ? _h : null);

paint(myEntryMarker, { name: 'Entry', style: 'labels_below', color: '#27ae60' });
paint(myExitMarker, { name: 'Exit', style: 'labels_above', color: '#c0392b' });

// Signals for scanners/alerts/strategy tester
register_signal(myEntryTrigger, 'Entry Signal');
register_signal(myExitTrigger, 'Exit Signal');
register_signal(for_every(myPositionState, _p => _p > 0), 'In Position');
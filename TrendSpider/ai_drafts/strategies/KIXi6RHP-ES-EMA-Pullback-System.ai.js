// ============================================================================
// This indicator reproduces the logic of the supplied Pine Script strategy
// "ES EMA Pullback System" as closely as the Custom JS API allows.
// It is a signal/plotting indicator (TrendSpider custom scripts cannot place
// broker orders or run a backtest engine like Pine's strategy.* calls), so
// strategy.entry/strategy.exit are approximated: we plot the EMAs, flag the
// SELL signal bar with a label, and compute the stop/target ATR-based levels
// as reference lines. The signal itself is exposed via register_signal() so
// it can be used in Scanners, Alerts and the Strategy Tester.
//
// Fix note: register_signal() and paint() names must be alphanumeric only
// (no spaces/punctuation) per the engine rules. The previous names like
// "Sell Signal", "Short Stop" etc. were invalid and caused the engine to
// mis-handle naming, triggering the "already exists" error. All names below
// were changed to single alphanumeric words.
// ============================================================================
describe_indicator('ES EMA Pullback System', 'price');

const tab = input.tab('Settings');

const emaGroup = tab.group('EMAs');
const emaRow = emaGroup.row();
const myFastLength = emaRow.number('Fast EMA', 9, { min: 1, max: 500 });
const myMidLength = emaRow.number('Mid EMA', 21, { min: 1, max: 500 });
const mySlowLength = emaRow.number('Slow EMA', 50, { min: 1, max: 500 });

const atrGroup = tab.group('ATR / Risk');
const atrRow = atrGroup.row();
const myAtrLength = atrRow.number('ATR Length', 14, { min: 1, max: 200 });
const myStopMultiplier = atrRow.number('Stop ATR Mult', 1.6, { min: 0.1, max: 20, step: 0.1 });
const myTargetMultiplier = atrRow.number('Target ATR Mult', 3.2, { min: 0.1, max: 20, step: 0.1 });

const sessionGroup = tab.group('Session');
const mySession1Start = sessionGroup.text('Session 1 Start (HHMM)', '0930');
const mySession1End = sessionGroup.text('Session 1 End (HHMM)', '1130');
const mySession2Start = sessionGroup.text('Session 2 Start (HHMM)', '1330');
const mySession2End = sessionGroup.text('Session 2 End (HHMM)', '1600');

// ===== EMAs =====
const myEma9 = ema(close, myFastLength);
const myEma21 = ema(close, myMidLength);
const myEma50 = ema(close, mySlowLength);

paint(myEma9, { name: 'EMA9', color: '#2962FF', thickness: 1 });
paint(myEma21, { name: 'EMA21', color: '#FF9800', thickness: 1 });
paint(myEma50, { name: 'EMA50', color: '#EF5350', thickness: 1 });

// ===== ATR =====
const myAtr = atr(high, low, close, myAtrLength);
const myShortStop = add(close, mult(myAtr, myStopMultiplier));
const myShortTarget = sub(close, mult(myAtr, myTargetMultiplier));

paint(myShortStop, { name: 'ShortStop', color: '#B71C1C', style: 'dotted', thickness: 1 });
paint(myShortTarget, { name: 'ShortTarget', color: '#1B5E20', style: 'dotted', thickness: 1 });

// ===== Helper: parse "HHMM" string into {hours, minutes} =====
function myParseHHMM(_text) {
	const myDigits = (_text || '').replace(/[^0-9]/g, '').padStart(4, '0');
	return {
		hours: parseInt(myDigits.slice(0, 2), 10),
		minutes: parseInt(myDigits.slice(2, 4), 10)
	};
}

const mySession1StartParsed = myParseHHMM(mySession1Start);
const mySession1EndParsed = myParseHHMM(mySession1End);
const mySession2StartParsed = myParseHHMM(mySession2Start);
const mySession2EndParsed = myParseHHMM(mySession2End);

function myMinutesOfDay(_hours, _minutes) {
	return _hours * 60 + _minutes;
}

const mySession1StartMin = myMinutesOfDay(mySession1StartParsed.hours, mySession1StartParsed.minutes);
const mySession1EndMin = myMinutesOfDay(mySession1EndParsed.hours, mySession1EndParsed.minutes);
const mySession2StartMin = myMinutesOfDay(mySession2StartParsed.hours, mySession2StartParsed.minutes);
const mySession2EndMin = myMinutesOfDay(mySession2EndParsed.hours, mySession2EndParsed.minutes);

// ===== In-session flag, per candle (exchange time zone) =====
const myInSession = time.map(_t => {
	const myTimeInfo = time_of(_t);
	const myMinuteOfDay = myMinutesOfDay(myTimeInfo.hours, myTimeInfo.minutes);
	const myInSession1 = myMinuteOfDay >= mySession1StartMin && myMinuteOfDay <= mySession1EndMin;
	const myInSession2 = myMinuteOfDay >= mySession2StartMin && myMinuteOfDay <= mySession2EndMin;
	return myInSession1 || myInSession2;
});

// ===== Trend / Pullback / Momentum / Entry conditions =====
const mySellSignal = for_every(myEma9, myEma21, myEma50, high, close, open, (_e9, _e21, _e50, _high, _close, _open) => {
	const myBearTrend = _e9 < _e21 && _e21 < _e50;
	const myPullback = _high >= _e9;
	const myBearMomentum = _close < _open;
	return myBearTrend && myPullback && myBearMomentum;
});

const myFinalSellSignal = for_every(mySellSignal, myInSession, (_sell, _session) => _sell && _session);

// ===== Label on SELL candles =====
const mySellMarks = for_every(myFinalSellSignal, high, (_signal, _high) => _signal ? _high : null);
paint(mySellMarks, { name: 'SellSignalMark', style: 'labels_above', color: 'red' });

// ===== Signals for Scanners, Alerts, Strategy Tester =====
register_signal(myFinalSellSignal, 'SellSignal');
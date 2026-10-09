describe_indicator('High Beta RSI Reversal Model', 'price');

// ── Inputs ────────────────────────────────────────────────────────────
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });
const myLowerLevel = input.number('Lower Level', 25, { min: 1, max: 99 });
const myUpperLevel = input.number('Upper Level', 75, { min: 1, max: 99 });
const myVolLength = input.number('Volume MA Length', 20, { min: 1, max: 500 });
const myVolMultiplier = input.number('Volume Multiplier', 1.5, { min: 0.1, max: 10, step: 0.1 });

// ── Core series (computed outside loops, as required) ───────────────
const myRsi = rsi(close, myRsiLength);
const myVolMA = sma(volume, myVolLength);

// Session-anchored VWAP, resetting every new trading day, replicating
// Pine's ta.vwap(close) behavior (cumulative within the session).
// Note: we approximate "session" using bar_at() daily session id, which
// should match regular daily session boundaries for most assets.
const mySessionId = time.map(myTime => bar_at(myTime).session);

const myVwap = series_of(null);
{
	let myCumPV = 0;
	let myCumVol = 0;
	let myPrevSession = null;

	for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
		if (mySessionId[myIndex] !== myPrevSession) {
			myCumPV = 0;
			myCumVol = 0;
			myPrevSession = mySessionId[myIndex];
		}

		myCumPV += close[myIndex] * volume[myIndex];
		myCumVol += volume[myIndex];

		myVwap[myIndex] = myCumVol !== 0 ? myCumPV / myCumVol : close[myIndex];
	}
}

// ── Entry conditions (replicates Pine logic exactly) ────────────────
// capitulation = rsi < lowerLevel and volume > volMA * 1.5
// bullConfirm  = close > high[1]
// longCondition = capitulation and bullConfirm
const myCapitulation = for_every(myRsi, volume, myVolMA, (_rsi, _vol, _volMa) => _rsi < myLowerLevel && _vol > _volMa * myVolMultiplier);
const myBullConfirm = for_every(close, shift(high, 1), (_close, _prevHigh) => _close > _prevHigh);
const myLongCondition = for_every(myCapitulation, myBullConfirm, (_cap, _bull) => Boolean(_cap && _bull));

// blowoff = rsi > upperLevel and volume > volMA * 1.5
// bearConfirm = close < low[1]
// shortCondition = blowoff and bearConfirm
const myBlowoff = for_every(myRsi, volume, myVolMA, (_rsi, _vol, _volMa) => _rsi > myUpperLevel && _vol > _volMa * myVolMultiplier);
const myBearConfirm = for_every(close, shift(low, 1), (_close, _prevLow) => _close < _prevLow);
const myShortCondition = for_every(myBlowoff, myBearConfirm, (_blow, _bear) => Boolean(_blow && _bear));

// ── Position/exit simulation (requires sequential state, like a strategy) ──
// Replicates: entry on condition, exit on VWAP target or stop loss,
// one position at a time, Pine's strategy.entry()/strategy.close() order.
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);

{
	let myPositionSize = 0; // 1 = long, -1 = short, 0 = flat
	let myStopLevel = null;

	for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
		myLongEntrySignal[myIndex] = false;
		myShortEntrySignal[myIndex] = false;
		myLongExitSignal[myIndex] = false;
		myShortExitSignal[myIndex] = false;

		// Entries (Pine allows stacking entry calls, but a single
		// strategy.entry per direction simply (re)opens that position)
		if (myLongCondition[myIndex]) {
			myPositionSize = 1;
			myStopLevel = low[myIndex];
			myLongEntrySignal[myIndex] = true;
		}

		if (myShortCondition[myIndex]) {
			myPositionSize = -1;
			myStopLevel = high[myIndex];
			myShortEntrySignal[myIndex] = true;
		}

		// Exits
		if (myPositionSize > 0) {
			if (close[myIndex] >= myVwap[myIndex]) {
				myLongExitSignal[myIndex] = true;
				myPositionSize = 0;
				myStopLevel = null;
			}
			else if (myStopLevel !== null && close[myIndex] < myStopLevel) {
				myLongExitSignal[myIndex] = true;
				myPositionSize = 0;
				myStopLevel = null;
			}
		}
		else if (myPositionSize < 0) {
			if (close[myIndex] <= myVwap[myIndex]) {
				myShortExitSignal[myIndex] = true;
				myPositionSize = 0;
				myStopLevel = null;
			}
			else if (myStopLevel !== null && close[myIndex] > myStopLevel) {
				myShortExitSignal[myIndex] = true;
				myPositionSize = 0;
				myStopLevel = null;
			}
		}
	}
}

// ── Visuals ──────────────────────────────────────────────────────────
paint(myVwap, { name: 'VWAP', color: '#4DA3FF', thickness: 2, forceUsePriceAxis: true });

const myLongMarks = for_every(myLongEntrySignal, low, (_flag, _low) => _flag ? _low : null);
const myShortMarks = for_every(myShortEntrySignal, high, (_flag, _high) => _flag ? _high : null);
const myLongExitMarks = for_every(myLongExitSignal, high, (_flag, _high) => _flag ? _high : null);
const myShortExitMarks = for_every(myShortExitSignal, low, (_flag, _low) => _flag ? _low : null);

paint(myLongMarks, { name: 'LongEntry', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(myShortMarks, { name: 'ShortEntry', style: 'labels_above', color: '#EF5350', thickness: 3 });
paint(myLongExitMarks, { name: 'LongExit', style: 'labels_above', color: '#80CBC4', thickness: 2 });
paint(myShortExitMarks, { name: 'ShortExit', style: 'labels_below', color: '#FFAB91', thickness: 2 });

// ── Signals for scanners/alerts/strategy tester ─────────────────────
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');
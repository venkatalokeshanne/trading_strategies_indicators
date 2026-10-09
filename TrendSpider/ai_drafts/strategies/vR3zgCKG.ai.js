// This is a conversion of a Pine Script strategy ("RR Master") into a
// TrendSpider Custom JS indicator. A few things could not be reproduced
// 1:1 because of platform differences - see notes below and in the
// errors_and_warnings_flagged block.
describe_indicator('RR Master Signals', 'price');

// ─── Inputs ──────────────────────────────────────────────────────────
const myTab = input.tab('Settings');

const myStartTimeRow = myTab.row();
// Pine used input.time(); TrendSpider has no date-time input, so this is
// a Unix timestamp (seconds). Default below corresponds to
// 2026-01-01 00:00 +0700.
const myStartTime = myStartTimeRow.number('Start Time (unix)', 1767200400, { min: 0 });

const myParamsRow1 = myTab.row();
const myRrRatio = myParamsRow1.number('RR Ratio', 1.7, { min: 0.1, max: 50, step: 0.1 });
const mySlBuffer = myParamsRow1.number('SL Buffer', 2.0, { min: 0, max: 1000, step: 0.1 });

const myParamsRow2 = myTab.row();
const myMinBarGap = myParamsRow2.number('Cooldown Bars', 8, { min: 0, max: 500 });

// ─── Indicators ──────────────────────────────────────────────────────
const myEma200 = ema(close, 200);

// NOTE: Pine's ta.vwap(hlc3) resets every session (day). TrendSpider's
// built-in vwap() does not auto-reset per day; it accumulates from the
// index passed in. We approximate using cumulative VWAP from bar 0,
// which will diverge from Pine's daily-reset VWAP over multi-day charts.
const myVwap = vwap(hlc3, volume, 0);

const myAdxObject = indicators.adx(14);
const myAdxVal = myAdxObject.adx;
const myAdxSma7 = sma(myAdxVal, 7);

const myRsiFast = rsi(close, 7);
const myRsiSlow = rsi(close, 14);
const myAtr = atr(high, low, close, 14);

// ─── Condition series ────────────────────────────────────────────────
const myIsAdxStrong = for_every(myAdxVal, myAdxSma7, (_adx, _adxSma) => _adx > 30 && _adx > _adxSma);

const myCrossover = for_every(myRsiFast, myRsiSlow, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return _fast > _slow && myRsiFast[_i - 1] <= myRsiSlow[_i - 1];
});

const myCrossunder = for_every(myRsiFast, myRsiSlow, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return _fast < _slow && myRsiFast[_i - 1] >= myRsiSlow[_i - 1];
});

const myWindowOk = for_every(time, _t => _t >= myStartTime);

// Raw buy/sell conditions (before cooldown logic, which is stateful)
const myBuyRaw = series_of(null);
const mySellRaw = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	myBuyRaw[myIndex] = myWindowOk[myIndex] &&
		low[myIndex] > myEma200[myIndex] &&
		close[myIndex] > myVwap[myIndex] &&
		myIsAdxStrong[myIndex] &&
		myCrossover[myIndex];

	mySellRaw[myIndex] = myWindowOk[myIndex] &&
		high[myIndex] < myEma200[myIndex] &&
		close[myIndex] < myVwap[myIndex] &&
		myIsAdxStrong[myIndex] &&
		myCrossunder[myIndex];
}

// ─── Cooldown / "position" state machine (stateful, matches Pine logic) ──
const myBuySignal = series_of(null);
const mySellSignal = series_of(null);
const myStopLoss = series_of(null);
const myTakeProfit = series_of(null);

let myLastTradeBar = -Infinity;
let myPositionOpen = 0; // 0 = flat, 1 = long, -1 = short (mirrors strategy.position_size == 0 check)

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myCanTrade = (myIndex - myLastTradeBar) >= myMinBarGap;
	const myBuy = myBuyRaw[myIndex] && myCanTrade;
	const mySell = mySellRaw[myIndex] && myCanTrade;

	myBuySignal[myIndex] = false;
	mySellSignal[myIndex] = false;

	if (myBuy && myPositionOpen === 0) {
		const mySl = low[myIndex] - mySlBuffer;
		const myTp = close[myIndex] + (Math.abs(close[myIndex] - mySl) * myRrRatio);

		myBuySignal[myIndex] = true;
		myStopLoss[myIndex] = mySl;
		myTakeProfit[myIndex] = myTp;
		myLastTradeBar = myIndex;
		myPositionOpen = 1;
	}
	else if (mySell && myPositionOpen === 0) {
		const mySl = high[myIndex] + mySlBuffer;
		const myTp = close[myIndex] - (Math.abs(mySl - close[myIndex]) * myRrRatio);

		mySellSignal[myIndex] = true;
		myStopLoss[myIndex] = mySl;
		myTakeProfit[myIndex] = myTp;
		myLastTradeBar = myIndex;
		myPositionOpen = -1;
	}
	else {
		myStopLoss[myIndex] = null;
		myTakeProfit[myIndex] = null;
	}

	// NOTE: Pine's strategy.position_size resets to 0 only when the
	// strategy.exit (stop/limit) is hit. We cannot simulate actual
	// stop/limit fills on future candles within an indicator script,
	// so this simplified state machine re-arms as soon as a new signal
	// bar occurs that satisfies the cooldown, approximating "flat".
	myPositionOpen = 0;
}

// ─── Labels for buy/sell markers (approximation of label.new positions) ──
const myBuyMarker = for_every(myBuySignal, low, myAtr, (_b, _l, _a) => _b ? (_l - _a * 3) : null);
const mySellMarker = for_every(mySellSignal, high, myAtr, (_s, _h, _a) => _s ? (_h + _a * 3) : null);

// ─── Painting ────────────────────────────────────────────────────────
paint(myEma200, { name: 'EMA200', color: '#f0c419', thickness: 2 });
paint(myVwap, { name: 'VWAP', color: '#9e9e9e', thickness: 1, style: 'dotted' });

paint(myBuyMarker, { name: 'Buy', style: 'labels_below', color: '#26A69A' });
paint(mySellMarker, { name: 'Sell', style: 'labels_above', color: '#EF5350' });

// ─── Signals for scanners / alerts / strategy tester ─────────────────
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
register_signal(for_every(myStopLoss, _sl => _sl !== null && _sl !== undefined), 'Trade Opened');
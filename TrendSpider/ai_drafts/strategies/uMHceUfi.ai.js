describe_indicator('EXPMA3 Line Pullback Long1 Long2 Long3', 'price');

// NOTE: TrendSpider Custom JS API has no strategy.*/backtesting engine
// (no position sizing, commissions, equity curve). This script
// reproduces the Pine Script's indicator logic (EMA lines, the three
// entry conditions sig1/sig2/sig3) exactly, and additionally
// simulates the Pine strategy's entry/exit RULES (next-bar entry,
// stop loss, trailing stop, time stop, partial take profits) using a
// plain state machine loop, exposing Buy/Close signals for scanning.
// Position sizing, commissions and equity are not modeled.

const myTab = input.tab('Signal Filters');
const myVolGroup = myTab.group('Volume');
const myVolRow = myVolGroup.row();
const myMinVolMult = myVolRow.number('Min Volume Multiplier', 1.0, { min: 0, max: 10, step: 0.1 });
const myMaxVolMult = myVolRow.number('Max Volume Multiplier', 3.5, { min: 0, max: 10, step: 0.1 });

const myBiasGroup = myTab.group('EXPMA Bias');
const myBiasRow = myBiasGroup.row();
const myMinBias = myBiasRow.number('Min EXPMA Bias Percent', 0.0, { min: -10, max: 10, step: 0.1 });
const myMaxBias = myBiasRow.number('Max EXPMA Bias Percent', 2.5, { min: -10, max: 10, step: 0.1 });

const myShadowGroup = myTab.group('Upper Shadow');
const myMaxUpperShadow = myShadowGroup.number('Max Upper Shadow Percent', 0.8, { min: 0, max: 10, step: 0.1 });

const myStopTab = input.tab('Stop Loss');
const myStopRow = myStopTab.row();
const myStopLossP1 = myStopRow.number('Long1 Stop Loss Percent', 3.5, { min: 0, max: 50, step: 0.1 });
const myStopLossP2 = myStopRow.number('Long2 Stop Loss Percent', 3.0, { min: 0, max: 50, step: 0.1 });
const myStopLossP3 = myStopRow.number('Long3 Stop Loss Percent', 2.2, { min: 0, max: 50, step: 0.1 });

const myTpTab = input.tab('Take Profit');
const myTpRow1 = myTpTab.row();
const myTp1P1 = myTpRow1.number('Long1 TP1 Percent', 7.0, { min: 0, max: 100, step: 0.1 });
const myTp2P1 = myTpRow1.number('Long1 TP2 Percent', 13.0, { min: 0, max: 100, step: 0.1 });
const myTpRow2 = myTpTab.row();
const myTp1P2 = myTpRow2.number('Long2 TP1 Percent', 6.0, { min: 0, max: 100, step: 0.1 });
const myTp2P2 = myTpRow2.number('Long2 TP2 Percent', 11.0, { min: 0, max: 100, step: 0.1 });
const myTpRow3 = myTpTab.row();
const myTp1P3 = myTpRow3.number('Long3 TP1 Percent', 5.0, { min: 0, max: 100, step: 0.1 });
const myTp2P3 = myTpRow3.number('Long3 TP2 Percent', 9.0, { min: 0, max: 100, step: 0.1 });

const myLen10 = 10;
const myLen20 = 20;
const myVolMaLen = 20;

// Core indicators
const myExpma10 = ema(close, myLen10);
const myExpma20 = ema(close, myLen20);
const myVolMa = sma(volume, myVolMaLen);
const myHighest3 = highest(high, 3);

// Derived conditions, computed per-candle
const myMaBias = for_every(myExpma10, myExpma20, (_e10, _e20) => ((_e10 - _e20) / _e20) * 100);
const myUpperShadowPct = for_every(high, close, (_h, _c) => ((_h - _c) / _c) * 100);
const myDayGain = roc(close, 1);

const myCondVol = for_every(volume, myVolMa, (_v, _vma) => _v >= _vma * myMinVolMult && _v <= _vma * myMaxVolMult);
const myCondBias = for_every(myMaBias, _b => _b >= myMinBias && _b <= myMaxBias);
const myCondShadow = for_every(myUpperShadowPct, _s => _s < myMaxUpperShadow);
const myCondUp = for_every(myDayGain, _g => _g > 0);
const myCondTrend = for_every(myExpma10, myExpma20, (_e10, _e20) => _e10 > _e20);

// Three signal types
const mySig1 = for_every(myCondTrend, open, myExpma10, low, myExpma20, close, myCondUp, myCondBias, myCondShadow, myCondVol,
	(_trend, _o, _e10, _l, _e20, _c, _up, _bias, _shadow, _vol) =>
		_trend && _o > _e10 && _l <= _e20 && _c > _e10 && _up && _bias && _shadow && _vol
);

const mySig2 = for_every(myCondTrend, open, myExpma10, myExpma20, low, close, myCondUp, myCondBias, myCondShadow, myCondVol,
	(_trend, _o, _e10, _e20, _l, _c, _up, _bias, _shadow, _vol) =>
		_trend && _o > _e20 && _o < _e10 && _l <= _e20 && _c > _e10 && _up && _bias && _shadow && _vol
);

const mySig3 = for_every(myCondTrend, open, myExpma10, low, close, myCondUp, myCondBias, myCondShadow, myCondVol,
	(_trend, _o, _e10, _l, _c, _up, _bias, _shadow, _vol) =>
		_trend && _o > _e10 && _l <= _e10 && _c > _e10 && _up && _bias && _shadow && _vol
);

// Shifted signals (entry happens on bar AFTER the signal bar, per Pine's sig[1])
const mySig1Prev = shift(mySig1, 1);
const mySig2Prev = shift(mySig2, 1);
const mySig3Prev = shift(mySig3, 1);

// State machine simulating the Pine strategy's entry/exit rules
const myN = close.length;
const myBuyMark = series_of(null);
const myCloseMark = series_of(null);

let myEntryPrice = null;
let myPosType = 0;
let myHoldDays = 0;
let myStopPrice = null;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	// Entry on this bar if prior bar had a signal and we are flat
	if (myPosType === 0) {
		if (mySig1Prev[myIndex]) {
			myEntryPrice = open[myIndex];
			myPosType = 1;
			myHoldDays = 0;
			myBuyMark[myIndex] = low[myIndex];
		}
		else if (mySig2Prev[myIndex]) {
			myEntryPrice = open[myIndex];
			myPosType = 2;
			myHoldDays = 0;
			myBuyMark[myIndex] = low[myIndex];
		}
		else if (mySig3Prev[myIndex]) {
			myEntryPrice = open[myIndex];
			myPosType = 3;
			myHoldDays = 0;
			myBuyMark[myIndex] = low[myIndex];
		}
	}

	if (myPosType > 0) {
		myHoldDays += 1;

		const myStopLossPercent = myPosType === 1 ? myStopLossP1 : (myPosType === 2 ? myStopLossP2 : myStopLossP3);
		myStopPrice = myEntryPrice * (1 - myStopLossPercent / 100);

		const myCloseVal = close[myIndex];

		if (myCloseVal / myEntryPrice >= 1.05) {
			myStopPrice = Math.max(myStopPrice, myEntryPrice);
		}
		if (myCloseVal / myEntryPrice >= 1.10) {
			myStopPrice = Math.max(myStopPrice, myEntryPrice + (myCloseVal - myEntryPrice) / 2);
		}

		const myExitStop = myCloseVal <= myStopPrice || myCloseVal <= myExpma20[myIndex];
		const myTimeExit = myHoldDays >= 3 && (myHighest3[myIndex] / myEntryPrice) < 1.05;

		const myTp1 = myPosType === 1 ? myTp1P1 : (myPosType === 2 ? myTp1P2 : myTp1P3);
		const myTp2 = myPosType === 1 ? myTp2P1 : (myPosType === 2 ? myTp2P2 : myTp2P3);

		let myFullExit = false;

		if (myCloseVal / myEntryPrice >= 1 + myTp2 / 100) {
			myFullExit = true;
		}
		else if (myExitStop || myTimeExit) {
			myFullExit = true;
		}

		if (myFullExit) {
			myCloseMark[myIndex] = high[myIndex];
			myPosType = 0;
			myEntryPrice = null;
			myHoldDays = 0;
			myStopPrice = null;
		}
		else if (myCloseVal / myEntryPrice >= 1 + myTp1 / 100) {
			// partial take profit, position stays open (qty not modeled)
			myCloseMark[myIndex] = high[myIndex];
		}
	}
}

// Plot the two EMAs
paint(myExpma10, { name: 'EXPMA10', color: '#FF9800', thickness: 2 });
paint(myExpma20, { name: 'EXPMA20', color: '#009688', thickness: 2 });

// Signal labels below bar
const mySig1Labels = for_every(mySig1, _s => _s ? 1 : null);
const mySig2Labels = for_every(mySig2, _s => _s ? 1 : null);
const mySig3Labels = for_every(mySig3, _s => _s ? 1 : null);

paint(mySig1Labels, { name: 'Long1', style: 'labels_below', color: 'green' });
paint(mySig2Labels, { name: 'Long2', style: 'labels_below', color: 'blue' });
paint(mySig3Labels, { name: 'Long3', style: 'labels_below', color: 'purple' });

paint(myBuyMark, { name: 'EntryMark', style: 'labels_below', color: 'lime' });
paint(myCloseMark, { name: 'ExitMark', style: 'labels_above', color: 'red' });

// Signals for scanners/alerts/strategy tester
register_signal(mySig1, 'Long1 Signal');
register_signal(mySig2, 'Long2 Signal');
register_signal(mySig3, 'Long3 Signal');
register_signal(for_every(myBuyMark, _v => _v !== null), 'Entry Triggered');
register_signal(for_every(myCloseMark, _v => _v !== null), 'Exit Triggered');
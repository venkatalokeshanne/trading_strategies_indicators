describe_indicator('Pro Structure Momentum Bot A Plus', 'price');

// This is a straightforward translation of the Pine Script
// strategy logic into TrendSpider Custom JS. Entries are
// exposed as register_signal() outputs (Buy/Sell) so they can
// be used in Scanners, Alerts and Strategy Tester. Stop Loss
// and Take Profit lines are painted as reference overlays, but
// TrendSpider indicators cannot place real broker orders or
// simulate strategy.exit() fills; that part of the Pine script
// (the actual trade management) has no equivalent here.

const myLookback = input.number('Structure Lookback', 10, { min: 1, max: 200 });
const mySlTpLookback = input.number('Stop Loss Lookback', 3, { min: 1, max: 200 });
const myRiskReward = input.number('Risk Reward Multiple', 2, { min: 0.1, max: 10 });

const myEma9 = ema(close, 9);
const myEma21 = ema(close, 21);
const mySwingHigh = highest(high, myLookback);
const mySwingLow = lowest(low, myLookback);
const myLongSl = lowest(low, mySlTpLookback);
const myShortSl = highest(high, mySlTpLookback);

const myLength = close.length;
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);
const myLongTp = series_of(null);
const myShortTp = series_of(null);
const myLongSlOut = series_of(null);
const myShortSlOut = series_of(null);

let myLongLevel = null;
let myShortLevel = null;

for (let myIndex = 1; myIndex < myLength; myIndex += 1) {
	const myBullTrend = myEma9[myIndex] > myEma21[myIndex];
	const myBearTrend = myEma9[myIndex] < myEma21[myIndex];
	const myBreakUp = close[myIndex] > mySwingHigh[myIndex - 1];
	const myBreakDown = close[myIndex] < mySwingLow[myIndex - 1];

	if (myBreakUp) {
		myLongLevel = mySwingHigh[myIndex - 1];
	}
	if (myBreakDown) {
		myShortLevel = mySwingLow[myIndex - 1];
	}

	const myPullbackLong = myLongLevel != null && low[myIndex] <= myLongLevel && close[myIndex] > myLongLevel;
	const myPullbackShort = myShortLevel != null && high[myIndex] >= myShortLevel && close[myIndex] < myShortLevel;

	const myBullConfirm = close[myIndex] > open[myIndex] && close[myIndex] > close[myIndex - 1];
	const myBearConfirm = close[myIndex] < open[myIndex] && close[myIndex] < close[myIndex - 1];

	const myBuy = myBullTrend && myPullbackLong && myBullConfirm;
	const mySell = myBearTrend && myPullbackShort && myBearConfirm;

	myBuySignal[myIndex] = myBuy;
	mySellSignal[myIndex] = mySell;

	if (myBuy) {
		myLongLevel = null;
		const myLongRisk = close[myIndex] - myLongSl[myIndex];
		myLongSlOut[myIndex] = myLongSl[myIndex];
		myLongTp[myIndex] = close[myIndex] + myLongRisk * myRiskReward;
	}
	if (mySell) {
		myShortLevel = null;
		const myShortRisk = myShortSl[myIndex] - close[myIndex];
		myShortSlOut[myIndex] = myShortSl[myIndex];
		myShortTp[myIndex] = close[myIndex] - myShortRisk * myRiskReward;
	}
}

paint(myEma9, { name: 'EMA9', color: '#FFD54F', thickness: 2 });
paint(myEma21, { name: 'EMA21', color: '#EF5350', thickness: 2 });

const myBuyMarks = for_every(myBuySignal, low, (_buy, _low) => _buy ? _low : null);
const mySellMarks = for_every(mySellSignal, high, (_sell, _high) => _sell ? _high : null);

// Note: paint() names and register_signal() names share the
// same namespace, so they must all be unique. The painted
// marker lines keep the "Signal" wording while the registered
// signals (used in Scanners/Alerts/Strategy Tester) are now
// named "Buy Entry" and "Sell Entry" to avoid the collision.
paint(myBuyMarks, { name: 'Buy Signal Marker', style: 'labels_below', color: '#26A69A' });
paint(mySellMarks, { name: 'Sell Signal Marker', style: 'labels_above', color: '#EF5350' });

paint(myLongSlOut, { name: 'Long Stop Loss', style: 'dotted', color: '#26A69A' });
paint(myLongTp, { name: 'Long Take Profit', style: 'dotted', color: '#26A69A' });
paint(myShortSlOut, { name: 'Short Stop Loss', style: 'dotted', color: '#EF5350' });
paint(myShortTp, { name: 'Short Take Profit', style: 'dotted', color: '#EF5350' });

register_signal(myBuySignal, 'Buy Entry');
register_signal(mySellSignal, 'Sell Entry');
// This is a conversion of a TradingView Pine strategy into a
// TrendSpider indicator. Only buy/sell signals, zero-lag EMA,
// VWAP bands and simulated SL/TP lines are reproduced - actual
// order execution/backtesting must be done via TrendSpider's own
// Strategy Tester, using the register_signal() outputs below.
describe_indicator('Clean VWAP ZL Scalper Single Trigger', 'price');

const myZlLenInput = input.number('Zero Lag Length', 34, { min: 2, max: 300 });
const myAtrLenInput = input.number('ATR Length', 14, { min: 1, max: 100 });
const myStopAtrMultInput = input.number('ATR Stop Mult', 1.2, { min: 0.1, max: 10, step: 0.1 });
const myTargetRrInput = input.number('Target RR', 1.5, { min: 0.1, max: 10, step: 0.1 });
const myVwapBand1Input = input.number('VWAP Band 1 Sigma', 1.0, { min: 0.1, max: 5, step: 0.25 });
const myVwapBand2Input = input.number('VWAP Band 2 Sigma', 2.0, { min: 0.1, max: 5, step: 0.25 });
const myShowBgInput = input.boolean('Background Shading', true);
const myShowStopsInput = input.boolean('Plot SL TP', true);

// Zero-Lag EMA: ema(src + (src - src[lag]), len)
function myZlema(_mySrc, _myLen) {
	const myLag = Math.floor((_myLen - 1) / 2);
	const myShifted = shift(_mySrc, myLag);
	const myInput = add(_mySrc, sub(_mySrc, myShifted));
	return ema(myInput, _myLen);
}

const myZl = myZlema(close, myZlLenInput);
const myAtr = atr(high, low, close, myAtrLenInput);
const myDev = stdev(hlc3, 50);

// Session-anchored VWAP, resets every new trading session (like ta.vwap)
const myVwap = series_of(null);
let mySessionSum = 0;
let mySessionVol = 0;
let myPrevSession = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const mySessionId = bar_at(time[myIndex]).session;
	if (mySessionId !== myPrevSession) {
		mySessionSum = 0;
		mySessionVol = 0;
		myPrevSession = mySessionId;
	}
	mySessionSum += hlc3[myIndex] * volume[myIndex];
	mySessionVol += volume[myIndex];
	myVwap[myIndex] = mySessionVol > 0 ? mySessionSum / mySessionVol : hlc3[myIndex];
}

const myUpper1 = add(myVwap, mult(myDev, myVwapBand1Input));
const myLower1 = sub(myVwap, mult(myDev, myVwapBand1Input));
const myUpper2 = add(myVwap, mult(myDev, myVwapBand2Input));
const myLower2 = sub(myVwap, mult(myDev, myVwapBand2Input));

// Bias
const myBullBias = for_every(close, myZl, myVwap, (_c, _z, _v) => _c > _z && _c > _v);
const myBearBias = for_every(close, myZl, myVwap, (_c, _z, _v) => _c < _z && _c < _v);

// Pullback zones
const myPullbackLong = for_every(low, myVwap, myLower1, myZl, (_l, _v, _l1, _z) => _l <= _v || _l <= _l1 || _l <= _z);
const myPullbackShort = for_every(high, myVwap, myUpper1, myZl, (_h, _v, _u1, _z) => _h >= _v || _h >= _u1 || _h >= _z);

// Rejection candle logic
const myBody = for_every(close, open, (_c, _o) => Math.abs(_c - _o));
const myLowerWick = for_every(open, close, low, (_o, _c, _l) => Math.min(_o, _c) - _l);
const myUpperWick = for_every(high, open, close, (_h, _o, _c) => _h - Math.max(_o, _c));

const myBullReject = for_every(myBody, myLowerWick, myUpperWick, (_b, _lw, _uw) => _b > 0 && _lw > _b * 1.0 && _uw <= _b * 1.2);
const myBearReject = for_every(myBody, myUpperWick, myLowerWick, (_b, _uw, _lw) => _b > 0 && _uw > _b * 1.0 && _lw <= _b * 1.2);

const myRejectionLong = for_every(myBullReject, close, open, (_r, _c, _o) => _r || _c > _o);
const myRejectionShort = for_every(myBearReject, close, open, (_r, _c, _o) => _r || _c < _o);

// Confirmation (uses previous candle open)
const myPrevOpen = shift(open, 1);
const myConfirmLong = for_every(close, open, myPrevOpen, (_c, _o, _po) => _c > _o && _c >= _po);
const myConfirmShort = for_every(close, open, myPrevOpen, (_c, _o, _po) => _c < _o && _c <= _po);

// Stateful single-trigger / position simulation loop
const myBuyTrigger = series_of(false);
const mySellTrigger = series_of(false);
const myLongSlSeries = series_of(null);
const myLongTpSeries = series_of(null);
const myShortSlSeries = series_of(null);
const myShortTpSeries = series_of(null);

let myLastSignal = 0; // 1 buy, -1 sell, 0 none
let myPositionSize = 0; // >0 long, <0 short, 0 flat
let myLongSl = null;
let myLongTp = null;
let myShortSl = null;
let myShortTp = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	// check existing position for SL/TP hit (simulated intrabar exit)
	if (myPositionSize > 0) {
		if (low[myIndex] <= myLongSl || high[myIndex] >= myLongTp) {
			myPositionSize = 0;
		}
	}
	else if (myPositionSize < 0) {
		if (high[myIndex] >= myShortSl || low[myIndex] <= myShortTp) {
			myPositionSize = 0;
		}
	}

	const myBuyCondition = myBullBias[myIndex] && myPullbackLong[myIndex] && myRejectionLong[myIndex] && myConfirmLong[myIndex] && myLastSignal !== 1;
	const mySellCondition = myBearBias[myIndex] && myPullbackShort[myIndex] && myRejectionShort[myIndex] && myConfirmShort[myIndex] && myLastSignal !== -1;

	if (myBuyCondition) {
		const myEntry = close[myIndex];
		const myRisk = myAtr[myIndex] * myStopAtrMultInput;
		myLongSl = myEntry - myRisk;
		myLongTp = myEntry + myRisk * myTargetRrInput;
		myLastSignal = 1;
		myPositionSize = 1;
		myBuyTrigger[myIndex] = true;
	}

	if (mySellCondition) {
		const myEntry = close[myIndex];
		const myRisk = myAtr[myIndex] * myStopAtrMultInput;
		myShortSl = myEntry + myRisk;
		myShortTp = myEntry - myRisk * myTargetRrInput;
		myLastSignal = -1;
		myPositionSize = -1;
		mySellTrigger[myIndex] = true;
	}

	myLongSlSeries[myIndex] = myPositionSize > 0 ? myLongSl : null;
	myLongTpSeries[myIndex] = myPositionSize > 0 ? myLongTp : null;
	myShortSlSeries[myIndex] = myPositionSize < 0 ? myShortSl : null;
	myShortTpSeries[myIndex] = myPositionSize < 0 ? myShortTp : null;
}

// Visuals
paint(myZl, { name: 'ZeroLag', color: '#00BCD4', thickness: 2 });
paint(myVwap, { name: 'VWAP', color: '#FFC107', thickness: 2 });

const myU1Painted = paint(myUpper1, { name: 'VwapBand1Up', color: '#FF9800', thickness: 1 });
const myL1Painted = paint(myLower1, { name: 'VwapBand1Down', color: '#FF9800', thickness: 1 });
const myU2Painted = paint(myUpper2, { name: 'VwapBand2Up', color: '#F44336', thickness: 1 });
const myL2Painted = paint(myLower2, { name: 'VwapBand2Down', color: '#4CAF50', thickness: 1 });

fill(myU1Painted, myU2Painted, '#F44336', 0.1);
fill(myL1Painted, myL2Painted, '#4CAF50', 0.1);

// Pine's bgcolor() has no direct equivalent; approximated via candle
// coloring based on bias (only applied if "Background Shading" is on).
const myCandleColors = for_every(myBullBias, myBearBias, (_bull, _bear) => {
	if (!myShowBgInput) { return null; }
	if (_bull) { return 'rgba(76,175,80,0.25)'; }
	if (_bear) { return 'rgba(244,67,54,0.25)'; }
	return null;
});
color_candles(myCandleColors);

const myBuyLabels = for_every(myBuyTrigger, _b => _b ? constants.icons.triangle_up : null);
const mySellLabels = for_every(mySellTrigger, _s => _s ? constants.icons.triangle_down : null);

paint(myBuyLabels, { name: 'Buy', style: 'labels_below', color: 'lime' });
paint(mySellLabels, { name: 'Sell', style: 'labels_above', color: 'red' });

paint(myShowStopsInput ? myLongSlSeries : constants.empty_series, { name: 'LongSL', color: 'red', style: 'ladder' });
paint(myShowStopsInput ? myLongTpSeries : constants.empty_series, { name: 'LongTP', color: 'green', style: 'ladder' });
paint(myShowStopsInput ? myShortSlSeries : constants.empty_series, { name: 'ShortSL', color: 'red', style: 'ladder' });
paint(myShowStopsInput ? myShortTpSeries : constants.empty_series, { name: 'ShortTP', color: 'green', style: 'ladder' });

register_signal(myBuyTrigger, 'Buy Signal');
register_signal(mySellTrigger, 'Sell Signal');
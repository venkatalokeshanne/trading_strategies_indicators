describe_indicator('Clean VWAP ZL Scalper', 'price');

// ───────────────────────────────────────────────────────────
// NOTE: this indicator approximates a TradingView *strategy*.
// TrendSpider custom scripts cannot place real broker orders,
// so position/SL/TP state is simulated bar-by-bar: when price
// touches the simulated SL or TP level (checked against that
// candle's high/low) the simulated position is closed. This is
// an approximation of Pine's strategy.exit() order execution.
// `barstate.isconfirmed` is treated as always true (every
// completed historical bar is "confirmed").
// ───────────────────────────────────────────────────────────

const myPriceSourceName = input.select('Price Source', 'close', constants.price_source_options);
const myPrice = market[myPriceSourceName];

const myZlLen = input.number('Zero Lag Length', 34, { min: 2, max: 300 });
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 200 });
const myStopATR = input.number('ATR Stop Mult', 1.2, { min: 0.1, max: 10 });
const myRR = input.number('Target RR', 1.5, { min: 0.1, max: 10 });
const myVwapBand1 = input.number('VWAP Band 1 Sigma', 1.0, { min: 0.1, max: 10 });
const myVwapBand2 = input.number('VWAP Band 2 Sigma', 2.0, { min: 0.1, max: 10 });
const myVolLen = input.number('Volume MA Length', 20, { min: 1, max: 300 });
const myVolMult = input.number('Volume Mult', 1.05, { min: 0.1, max: 10 });
const myShowBg = input.boolean('Background Shading', true);
const myShowStops = input.boolean('Plot SL and TP', true);

// Zero-lag EMA: ema(src + (src - src[lag]), len)
const myLag = Math.floor((myZlLen - 1) / 2);
const mySrcShifted = shift(myPrice, myLag);
const myZlSource = for_every(myPrice, mySrcShifted, (_s, _sLag) => _s + (_s - _sLag));
const myZl = ema(myZlSource, myZlLen);

const myAtr = atr(high, low, close, myAtrLen);
const myVolMA = sma(volume, myVolLen);

// VWAP computed from the beginning of the data set, using hlc3
const myVwap = vwap(hlc3, volume, 0);
const myDev = stdev(hlc3, 50);

const myUpper1 = add(myVwap, mult(myDev, myVwapBand1));
const myLower1 = sub(myVwap, mult(myDev, myVwapBand1));
const myUpper2 = add(myVwap, mult(myDev, myVwapBand2));
const myLower2 = sub(myVwap, mult(myDev, myVwapBand2));

const myBullBias = for_every(close, myZl, myVwap, (_c, _z, _v) => _c > _z && _c > _v);
const myBearBias = for_every(close, myZl, myVwap, (_c, _z, _v) => _c < _z && _c < _v);

const myPullbackLong = for_every(low, myVwap, myLower1, myZl, (_l, _v, _lo1, _z) => _l <= _v || _l <= _lo1 || _l <= _z);
const myPullbackShort = for_every(high, myVwap, myUpper1, myZl, (_h, _v, _u1, _z) => _h >= _v || _h >= _u1 || _h >= _z);

const myOpenPrev1 = shift(open, 1);

const myBullReject = for_every(open, close, high, low, (_o, _c, _h, _l) => {
	const myBody = Math.abs(_c - _o);
	const myLowerWick = Math.min(_o, _c) - _l;
	const myUpperWick = _h - Math.max(_o, _c);
	return myBody > 0 && myLowerWick > myBody * 1.0 && myUpperWick <= myBody * 1.2;
});

const myBearReject = for_every(open, close, high, low, (_o, _c, _h, _l) => {
	const myBody = Math.abs(_c - _o);
	const myLowerWick = Math.min(_o, _c) - _l;
	const myUpperWick = _h - Math.max(_o, _c);
	return myBody > 0 && myUpperWick > myBody * 1.0 && myLowerWick <= myBody * 1.2;
});

const myRejectionLong = for_every(myBullReject, close, open, (_br, _c, _o) => _br || _c > _o);
const myRejectionShort = for_every(myBearReject, close, open, (_br, _c, _o) => _br || _c < _o);

const myConfirmLong = for_every(close, open, myOpenPrev1, (_c, _o, _oPrev) => _c > _o && _c >= _oPrev);
const myConfirmShort = for_every(close, open, myOpenPrev1, (_c, _o, _oPrev) => _c < _o && _c <= _oPrev);

// ─── Sequential state simulation (lastSignal / position / SL / TP) ───
const myBuyTriggerSeries = series_of(null);
const mySellTriggerSeries = series_of(null);
const myLongSLSeries = series_of(null);
const myLongTPSeries = series_of(null);
const myShortSLSeries = series_of(null);
const myShortTPSeries = series_of(null);

let myLastSignal = 0;
let myPositionSize = 0; // 1 = long, -1 = short, 0 = flat
let myLongSL = null;
let myLongTP = null;
let myShortSL = null;
let myShortTP = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	let myBuyTrigger = false;
	let mySellTrigger = false;

	if (myBullBias[myIndex] && myPullbackLong[myIndex] && myRejectionLong[myIndex] && myConfirmLong[myIndex] && myLastSignal !== 1) {
		myBuyTrigger = true;
	}
	if (myBearBias[myIndex] && myPullbackShort[myIndex] && myRejectionShort[myIndex] && myConfirmShort[myIndex] && myLastSignal !== -1) {
		mySellTrigger = true;
	}

	if (myBuyTrigger) {
		const myEntry = close[myIndex];
		const myRisk = myAtr[myIndex] * myStopATR;
		myLongSL = myEntry - myRisk;
		myLongTP = myEntry + myRisk * myRR;
		myLastSignal = 1;
		myPositionSize = 1;
		myShortSL = null;
		myShortTP = null;
	}

	if (mySellTrigger) {
		const myEntry = close[myIndex];
		const myRisk = myAtr[myIndex] * myStopATR;
		myShortSL = myEntry + myRisk;
		myShortTP = myEntry - myRisk * myRR;
		myLastSignal = -1;
		myPositionSize = -1;
		myLongSL = null;
		myLongTP = null;
	}

	// simulate SL/TP execution against current candle's range
	if (myPositionSize > 0 && myLongSL !== null && myLongTP !== null) {
		if (low[myIndex] <= myLongSL || high[myIndex] >= myLongTP) {
			myPositionSize = 0;
		}
	}
	else if (myPositionSize < 0 && myShortSL !== null && myShortTP !== null) {
		if (high[myIndex] >= myShortSL || low[myIndex] <= myShortTP) {
			myPositionSize = 0;
		}
	}

	myBuyTriggerSeries[myIndex] = myBuyTrigger;
	mySellTriggerSeries[myIndex] = mySellTrigger;
	myLongSLSeries[myIndex] = myPositionSize > 0 ? myLongSL : null;
	myLongTPSeries[myIndex] = myPositionSize > 0 ? myLongTP : null;
	myShortSLSeries[myIndex] = myPositionSize < 0 ? myShortSL : null;
	myShortTPSeries[myIndex] = myPositionSize < 0 ? myShortTP : null;
}

// ─── Visuals ───
const myZlPainted = paint(myZl, { name: 'ZeroLag', color: '#00e5ff', thickness: 2 });
const myVwapPainted = paint(myVwap, { name: 'VWAP', color: '#ffd600', thickness: 2 });

const myU1Painted = paint(myUpper1, { name: 'VwapPlus1Sigma', color: '#ff9800' });
const myL1Painted = paint(myLower1, { name: 'VwapMinus1Sigma', color: '#ff9800' });
const myU2Painted = paint(myUpper2, { name: 'VwapPlus2Sigma', color: '#ef5350' });
const myL2Painted = paint(myLower2, { name: 'VwapMinus2Sigma', color: '#4caf50' });

fill(myU1Painted, myU2Painted, '#ef5350', 0.1);
fill(myL1Painted, myL2Painted, '#4caf50', 0.1);

// background shading approximation: colors candles instead of chart background
const myBgColors = for_every(myBullBias, myBearBias, (_bull, _bear) => {
	if (!myShowBg) { return null; }
	if (_bull) { return 'rgba(76,175,80,0.12)'; }
	if (_bear) { return 'rgba(239,83,80,0.12)'; }
	return null;
});
color_candles(myBgColors);

const myBuyLabels = for_every(myBuyTriggerSeries, _b => _b ? constants.icons.triangle_up : null);
const mySellLabels = for_every(mySellTriggerSeries, _s => _s ? constants.icons.triangle_down : null);
paint(myBuyLabels, { name: 'Buy', style: 'labels_below', color: '#00e676' });
paint(mySellLabels, { name: 'Sell', style: 'labels_above', color: '#ff1744' });

const myLongSLToPaint = myShowStops ? myLongSLSeries : series_of(null);
const myLongTPToPaint = myShowStops ? myLongTPSeries : series_of(null);
const myShortSLToPaint = myShowStops ? myShortSLSeries : series_of(null);
const myShortTPToPaint = myShowStops ? myShortTPSeries : series_of(null);

paint(myLongSLToPaint, { name: 'LongSL', color: '#ef5350', style: 'ladder', thickness: 2 });
paint(myLongTPToPaint, { name: 'LongTP', color: '#4caf50', style: 'ladder', thickness: 2 });
paint(myShortSLToPaint, { name: 'ShortSL', color: '#ef5350', style: 'ladder', thickness: 2 });
paint(myShortTPToPaint, { name: 'ShortTP', color: '#4caf50', style: 'ladder', thickness: 2 });

// ─── Signals for scanners/alerts/backtests ───
register_signal(myBuyTriggerSeries, 'Buy Trigger');
register_signal(mySellTriggerSeries, 'Sell Trigger');
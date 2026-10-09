describe_indicator('Signal Engine Quantum Edge', 'price');

// ───────────────────────────── Inputs ─────────────────────────────
const generalTab = input.tab('General');
const myPeriods = generalTab.number('ATR Period', 10, { min: 1, max: 200 });
const mySrcChoice = generalTab.select('Source', 'hl2', constants.price_source_options);
const myMultiplier = generalTab.number('ATR Multiplier', 3.0, { min: 0.1, max: 20, step: 0.1 });
const myChangeATR = generalTab.boolean('Change ATR Calculation Method', true);
const myShowSignals = generalTab.boolean('Show Buy/Sell Signals', false);
const myHighlighting = generalTab.boolean('Highlighter On/Off', true);
const myBarColoring = generalTab.boolean('Bar Coloring On/Off', true);

const windowTab = input.tab('Date Window');
const fromRow = windowTab.row();
const myFromMonth = fromRow.number('From Month', 9, { min: 1, max: 12 });
const myFromDay = fromRow.number('From Day', 1, { min: 1, max: 31 });
const myFromYear = fromRow.number('From Year', 2018, { min: 999, max: 9999 });
const toRow = windowTab.row();
const myToMonth = toRow.number('To Month', 1, { min: 1, max: 12 });
const myToDay = toRow.number('To Day', 1, { min: 1, max: 31 });
const myToYear = toRow.number('To Year', 9999, { min: 999, max: 9999 });

// ───────────────────────────── Core math ─────────────────────────────
const mySrc = market[mySrcChoice];

// True Range, computed manually (needed for the "classic" ATR = SMA(TR))
const myTr = for_every(high, low, close, (_h, _l, _c, _prev, _i) => {
	if (_i === 0) {
		return _h - _l;
	}
	const _prevClose = close[_i - 1];
	return Math.max(_h - _l, Math.abs(_h - _prevClose), Math.abs(_l - _prevClose));
});

const myAtrSma = sma(myTr, myPeriods);
const myAtrWilder = atr(high, low, close, myPeriods);
const myAtr = myChangeATR ? myAtrWilder : myAtrSma;

// Recursive Up/Down trailing stops and trend state (mirrors Pine's `:=` logic bar by bar)
const myUp = [];
const myDn = [];
const myUp1 = [];
const myDn1 = [];
const myTrend = [];
const myBuySignal = [];
const mySellSignal = [];

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myBasicUp = mySrc[myIndex] - myMultiplier * myAtr[myIndex];
	const myBasicDn = mySrc[myIndex] + myMultiplier * myAtr[myIndex];

	const myPrevUp = myIndex > 0 ? (myUp[myIndex - 1] ?? myBasicUp) : myBasicUp;
	const myPrevDn = myIndex > 0 ? (myDn[myIndex - 1] ?? myBasicDn) : myBasicDn;

	myUp1[myIndex] = myPrevUp;
	myDn1[myIndex] = myPrevDn;

	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : close[myIndex];

	myUp[myIndex] = (myPrevClose > myPrevUp) ? Math.max(myBasicUp, myPrevUp) : myBasicUp;
	myDn[myIndex] = (myPrevClose < myPrevDn) ? Math.min(myBasicDn, myPrevDn) : myBasicDn;

	const myPrevTrend = myIndex > 0 ? myTrend[myIndex - 1] : 1;
	let myCurrentTrend = myPrevTrend;

	if (myPrevTrend === -1 && close[myIndex] > myDn1[myIndex]) {
		myCurrentTrend = 1;
	}
	else if (myPrevTrend === 1 && close[myIndex] < myUp1[myIndex]) {
		myCurrentTrend = -1;
	}

	myTrend[myIndex] = myCurrentTrend;
	myBuySignal[myIndex] = (myCurrentTrend === 1 && myPrevTrend === -1);
	mySellSignal[myIndex] = (myCurrentTrend === -1 && myPrevTrend === 1);
}

// ───────────────────────────── Date window filter ─────────────────────────────
// Date.UTC() is a static method (not "new Date()"), so it is allowed here.
const myFromTimestamp = Math.floor(Date.UTC(myFromYear, myFromMonth - 1, myFromDay, 0, 0) / 1000);
const myToTimestamp = Math.floor(Date.UTC(myToYear, myToMonth - 1, myToDay, 23, 59) / 1000);
const myInWindow = for_every(time, _t => (_t >= myFromTimestamp && _t <= myToTimestamp));

// ───────────────────────────── Plot series ─────────────────────────────
const myUpLine = for_every(series_of(1), (_x, _p, _i) => myTrend[_i] === 1 ? myUp[_i] : null);
const myDnLine = for_every(series_of(1), (_x, _p, _i) => myTrend[_i] === 1 ? null : myDn[_i]);
const myBuyMarker = for_every(series_of(1), (_x, _p, _i) => myBuySignal[_i] ? myUp[_i] : null);
const mySellMarker = for_every(series_of(1), (_x, _p, _i) => mySellSignal[_i] ? myDn[_i] : null);

// ───────────────────────────── Bar coloring (barssince logic) ─────────────────────────────
const myBuySince = [];
const mySellSince = [];
let myLastBuy = Infinity;
let myLastSell = Infinity;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myBuySignal[myIndex]) {
		myLastBuy = 0;
	}
	else if (myLastBuy < Infinity) {
		myLastBuy += 1;
	}

	if (mySellSignal[myIndex]) {
		myLastSell = 0;
	}
	else if (myLastSell < Infinity) {
		myLastSell += 1;
	}

	myBuySince[myIndex] = myLastBuy;
	mySellSince[myIndex] = myLastSell;
}

const myBarColors = for_every(series_of(1), (_x, _p, _i) => {
	if (!myBarColoring || _i === 0) {
		return null;
	}
	const myPrevBuy = myBuySince[_i - 1];
	const myPrevSell = mySellSince[_i - 1];
	if (myPrevBuy < myPrevSell) {
		return 'green';
	}
	if (myPrevBuy > myPrevSell) {
		return 'red';
	}
	return null;
});

color_candles(myBarColors);

// ───────────────────────────── Painting ─────────────────────────────
const myMidPlot = paint(ohlc4, { name: 'Mid', style: 'dotted', color: 'gray', thickness: 1 });
const myUpPlot = paint(myUpLine, { name: 'Up Trend', color: 'green', thickness: 2 });
const myDnPlot = paint(myDnLine, { name: 'Down Trend', color: 'red', thickness: 2 });

fill(myMidPlot, myUpPlot, myHighlighting ? 'green' : 'white', 0.15, 'UpTrend Highlighter');
fill(myMidPlot, myDnPlot, myHighlighting ? 'red' : 'white', 0.15, 'DownTrend Highlighter');

paint(myBuyMarker, { name: 'UpTrend Begins Marker', style: 'labels_below', color: 'green' });
paint(mySellMarker, { name: 'DownTrend Begins Marker', style: 'labels_above', color: 'red' });

// Optional Buy/Sell text labels (text-only versions of the above markers)
const myBuyTextMarker = for_every(series_of(1), (_x, _p, _i) => (myShowSignals && myBuySignal[_i]) ? myUp[_i] : null);
const mySellTextMarker = for_every(series_of(1), (_x, _p, _i) => (myShowSignals && mySellSignal[_i]) ? myDn[_i] : null);

paint(myBuyTextMarker, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellTextMarker, { name: 'Sell', style: 'labels_above', color: 'red' });

// ───────────────────────────── Signals for scanner/alerts/strategy ─────────────────────────────
// Note: names of register_signal() outputs must be unique and must not collide
// with paint() line names, hence the "Signal" suffix below.
const myBuyEntrySignal = for_every(series_of(1), (_x, _p, _i) => myBuySignal[_i] && myInWindow[_i]);
const mySellEntrySignal = for_every(series_of(1), (_x, _p, _i) => mySellSignal[_i] && myInWindow[_i]);

register_signal(myBuyEntrySignal, 'Buy Entry Signal');
register_signal(mySellEntrySignal, 'Sell Entry Signal');
register_signal(myBuySignal, 'UpTrend Begins Signal');
register_signal(mySellSignal, 'DownTrend Begins Signal');
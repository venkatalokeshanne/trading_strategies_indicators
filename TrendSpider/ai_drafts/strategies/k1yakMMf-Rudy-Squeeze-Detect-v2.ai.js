describe_indicator('Rudy Squeeze Detect v2', 'price');

// NOTE: Custom JS indicators cannot place trades, manage positions,
// or run trailing stops like a Pine Script "strategy()" script.
// This conversion reproduces all the Pine CALCULATIONS and SIGNAL
// LOGIC exactly, and exposes squeezeBuy / squeezeFade as scanner /
// alert-ready signals via register_signal(). The actual order
// execution (entries, trailing exits) from the Pine strategy block
// has no equivalent here and is not reproduced.

const myParamsTab = input.tab('Parameters');
const myMaRow = myParamsTab.row();
const myShortMALen = myMaRow.number('Short MA Period', 21, { min: 1, max: 500 });
const myMidMALen = myMaRow.number('Mid MA Period', 50, { min: 1, max: 500 });

const myRsiRow = myParamsTab.row();
const myRsiLen = myRsiRow.number('RSI Period', 14, { min: 1, max: 200 });
const myRsiMax = myRsiRow.number('RSI Maximum', 80, { min: 1, max: 100 });

const myVolBbRow = myParamsTab.row();
const myVolAvgLen = myVolBbRow.number('Volume Average Bars', 20, { min: 1, max: 500 });
const myBbLen = myVolBbRow.number('BB Period', 20, { min: 1, max: 500 });

const mySigRow = myParamsTab.row();
const myMinScore = mySigRow.number('Min Signal Score', 3, { min: 0, max: 8 });

// --- Core calculations (mirrors Pine exactly) ---
const myShortMA = ema(close, myShortMALen);
const myMidMA = ema(close, myMidMALen);
const myRsiVal = rsi(close, myRsiLen);
const myVolAvg = sma(volume, myVolAvgLen);
const myVolRatio = div(volume, myVolAvg);
const myDayGap = roc(close, 1);
const myMom5 = roc(close, 5);
const myBbBasis = sma(close, myBbLen);
const myBbBand = compute_band(myBbBasis, 'St.Dev.', 2, myBbLen);
const myBbWidth = mult(div(sub(myBbBand.upper, myBbBand.lower), myBbBasis), 100);

// --- Scoring (sig), replicating the exact Pine point weighting ---
const mySigScore = for_every(
	myVolRatio, myDayGap, myShortMA, myMidMA, close, myBbWidth, myMom5,
	(_vr, _dg, _sma, _mma, _c, _bbw, _m5) => {
		let myScore = 0;
		myScore += _vr > 1.5 ? 2 : (_vr > 1.2 ? 1 : 0);
		myScore += _dg > 3.0 ? 2 : (_dg > 1.0 ? 1 : 0);
		myScore += _sma > _mma ? 1 : 0;
		myScore += _c > _sma ? 1 : 0;
		myScore += _bbw < 5.0 ? 1 : 0;
		myScore += _m5 > 2.0 ? 1 : 0;
		return myScore;
	}
);

// --- Conditions ---
const myPriceOK = for_every(close, myShortMA, (_c, _sma) => _c > _sma);
const myRsiOK = for_every(myRsiVal, _r => _r < myRsiMax);
const mySqueezeBuy = for_every(myPriceOK, myRsiOK, mySigScore, (_pok, _rok, _s) => _pok && _rok && _s >= myMinScore);
const mySqueezeFade = for_every(close, myShortMA, myMom5, (_c, _sma, _m5) => _c < _sma && _m5 < -3.0);

// --- Visuals ---
paint(myShortMA, { name: 'Short MA', color: '#2196F3', thickness: 2 });
paint(myMidMA, { name: 'Mid MA', color: '#9C27B0', thickness: 1 });

// barcolor(volRatio > 1.5 ...) equivalent
const myCandleColors = for_every(myVolRatio, _vr => _vr > 1.5 ? '#00E676' : null);
color_candles(myCandleColors);

// plotshape equivalents
const myBuyLabelSeries = for_every(mySqueezeBuy, _b => _b ? constants.icons.triangle_up : null);
const myFadeLabelSeries = for_every(mySqueezeFade, _f => _f ? constants.icons.triangle_down : null);
paint(myBuyLabelSeries, { style: 'labels_below', color: '#00E676', name: 'Squeeze Buy' });
paint(myFadeLabelSeries, { style: 'labels_above', color: '#F44336', name: 'Squeeze Fade' });

// --- Signals for scanners / alerts / strategy tester ---
// Signal names must be unique across the whole script; previously the
// label name "Squeeze Buy" (used for a visual label series) collided
// with the signal name "Squeeze Buy", which the engine treats as the
// same registered output and throws "already exists". Renaming the
// signal names (keeping them unique and distinct from the painted
// label series names) fixes the error.
register_signal(mySqueezeBuy, 'Squeeze Buy Signal');
register_signal(mySqueezeFade, 'Squeeze Fade Signal');

// --- Dashboard overlay, replicating the Pine table ---
const myLastIndex = close.length - 1;
const myScoreText = String(mySigScore[myLastIndex]);
const myVolText = (Math.round(myVolRatio[myLastIndex] * 10) / 10) + 'x';
const myBbText = (Math.round(myBbWidth[myLastIndex] * 10) / 10) + '%';
const myMomText = (Math.round(myMom5[myLastIndex] * 10) / 10) + '%';

paint_overlay('RudyDashboard', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'Score', color: 'white' }, { text: myScoreText, color: mySigScore[myLastIndex] >= myMinScore ? 'lime' : 'red' }] },
		{ cells: [{ text: 'Vol', color: 'white' }, { text: myVolText, color: myVolRatio[myLastIndex] > 1.5 ? 'lime' : 'gray' }] },
		{ cells: [{ text: 'BB', color: 'white' }, { text: myBbText, color: 'white' }] },
		{ cells: [{ text: 'Mom5d', color: 'white' }, { text: myMomText, color: myMom5[myLastIndex] > 0 ? 'lime' : 'red' }] }
	]
});
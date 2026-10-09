describe_indicator('Rudy Squeeze Detect v2', 'price');

// NOTE: Custom JS API has no strategy/backtesting execution engine
// (no strategy.entry/exit, no position sizing, no trailing stop).
// This port reproduces the Pine SCORE, CONDITIONS and VISUALS exactly,
// and exposes squeezeBuy / squeezeFade as scanner/alert signals.
// The trade execution and trailing-stop logic from the Pine strategy
// cannot be reproduced here.

const myTab = input.tab('Parameters');

const myShortLenRow = myTab.row();
const myShortLen = myShortLenRow.number('Short MA Period', 21, { min: 1, max: 500 });
const myMidLen = myShortLenRow.number('Mid MA Period', 50, { min: 1, max: 500 });

const myRsiRow = myTab.row();
const myRsiLen = myRsiRow.number('RSI Period', 14, { min: 1, max: 200 });
const myRsiMax = myRsiRow.number('RSI Maximum', 80, { min: 1, max: 100 });

const myVolRow = myTab.row();
const myVolAvgLen = myVolRow.number('Volume Average Bars', 20, { min: 1, max: 500 });
const myBbLen = myVolRow.number('BB Period', 20, { min: 1, max: 500 });

const myScoreRow = myTab.row();
const myMinScore = myScoreRow.number('Min Signal Score', 3, { min: 0, max: 7 });

// --- Core calculations ---
const myShortMA = ema(close, myShortLen);
const myMidMA = ema(close, myMidLen);
const myRsiVal = rsi(close, myRsiLen);
const myVolAvg = sma(volume, myVolAvgLen);
const myVolRatio = div(volume, myVolAvg);
const myDayGap = mult(div(sub(close, shift(close, 1)), shift(close, 1)), 100);

const myBbM = sma(close, myBbLen);
const myBbBand = compute_band(myBbM, 'St.Dev.', 2, myBbLen);
const myBbW = mult(div(sub(myBbBand.upper, myBbBand.lower), myBbM), 100);

const myMom5 = roc(close, 5);

// --- Score (sum of individual conditions, 0..7) ---
const mySig = for_every(
	myVolRatio, myDayGap, myShortMA, myMidMA, close, myBbW, myMom5,
	(_volRatio, _dayGap, _shortMA, _midMA, _close, _bbW, _mom5) => {
		let myScore = 0;
		myScore += _volRatio > 1.5 ? 2 : (_volRatio > 1.2 ? 1 : 0);
		myScore += _dayGap > 3.0 ? 2 : (_dayGap > 1.0 ? 1 : 0);
		myScore += _shortMA > _midMA ? 1 : 0;
		myScore += _close > _shortMA ? 1 : 0;
		myScore += _bbW < 5.0 ? 1 : 0;
		myScore += _mom5 > 2.0 ? 1 : 0;
		return myScore;
	}
);

// --- Conditions ---
const mySqueezeBuy = for_every(
	close, myShortMA, myRsiVal, mySig,
	(_close, _shortMA, _rsiVal, _sig) => (_close > _shortMA) && (_rsiVal < myRsiMax) && (_sig >= myMinScore)
);

const mySqueezeFade = for_every(
	close, myShortMA, myMom5,
	(_close, _shortMA, _mom5) => (_close < _shortMA) && (_mom5 < -3.0)
);

register_signal(mySqueezeBuy, 'Squeeze Buy');
register_signal(mySqueezeFade, 'Squeeze Fade');

// --- Visuals ---
paint(myShortMA, { name: 'Short MA', color: '#2196F3', thickness: 2 });
paint(myMidMA, { name: 'Mid MA', color: '#9C27B0', thickness: 1 });

// barcolor(volRatio > 1.5 ...) equivalent
const myCandleColors = for_every(myVolRatio, _volRatio => _volRatio > 1.5 ? '#00E676' : null);
color_candles(myCandleColors);

// plotshape equivalents (labels on candles)
const myBuyMarks = for_every(mySqueezeBuy, _buy => _buy ? constants.icons.triangle_up : null);
const myFadeMarks = for_every(mySqueezeFade, _fade => _fade ? constants.icons.triangle_down : null);

paint(myBuyMarks, { name: 'Squeeze', style: 'labels_below', color: '#00E676' });
paint(myFadeMarks, { name: 'Fade', style: 'labels_above', color: '#F44336' });

// --- Dashboard (overlay table), mirrors Pine's "barstate.islast" table ---
const myLastSig = mySig[mySig.length - 1];
const myLastVolRatio = myVolRatio[myVolRatio.length - 1];
const myLastBbW = myBbW[myBbW.length - 1];
const myLastMom5 = myMom5[myMom5.length - 1];

paint_overlay('RudyDashboard', { position: 'top_right' }, {
	rows: [{
		cells: [
			{ text: 'Score', color: 'white' },
			{ text: String(myLastSig), color: myLastSig >= myMinScore ? '#00FF00' : '#FF0000' }
		]
	}, {
		cells: [
			{ text: 'Vol', color: 'white' },
			{ text: (isFinite(myLastVolRatio) ? myLastVolRatio.toFixed(1) : '0.0') + 'x', color: myLastVolRatio > 1.5 ? '#00FF00' : '#AAAAAA' }
		]
	}, {
		cells: [
			{ text: 'BB', color: 'white' },
			{ text: (isFinite(myLastBbW) ? myLastBbW.toFixed(1) : '0.0') + '%', color: 'white' }
		]
	}, {
		cells: [
			{ text: 'Mom5d', color: 'white' },
			{ text: (isFinite(myLastMom5) ? myLastMom5.toFixed(1) : '0.0') + '%', color: myLastMom5 > 0 ? '#00FF00' : '#FF0000' }
		]
	}]
});
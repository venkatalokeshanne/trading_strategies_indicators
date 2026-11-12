/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : DFT
 * Author       : ds3783
 * Source URL   : https://www.tradingview.com/script/38Uds6oO-Fourier-Extrapolation-Forecast-DFT
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Fourier Extrapolation Forecast_TV
 *
 * Deviations from the original: Reviewed AI draft; forecast drawn with paint_projection (max 100 points) instead of
 *   one line per step.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Fourier Extrapolation Forecast_TV', 'price');
const myLength = input.number('DFT Length', 128, { min: 8, max: 2000 });
const myForecastLength = input.number('Forecast Length', 14, { min: 1, max: 100 });
const myNumHarmonics = input.number('Harmonics Used', 8, { min: 1, max: 100 });
const myAnchorToClose = input.boolean('Anchor to Last Close', true);
const myRecon = (_re, _im, _n, _m, _t) => {
	let myTotal = _re[0] / _n;
	for (let myK = 1; myK <= _m; myK += 1) {
		const myAngle = 2 * Math.PI * myK * _t / _n;
		myTotal += (2.0 / _n) * (_re[myK] * Math.cos(myAngle) - _im[myK] * Math.sin(myAngle));
	}
	return myTotal;
};
const myN = Math.min(myLength, close.length);
assert(myN >= 8, 'Not enough candles to compute the DFT window');
const myS = [];
for (let myT = 0; myT < myN; myT += 1) myS.push(close[close.length - myN + myT]);
let mySumX = 0, mySumY = 0, mySumXY = 0, mySumX2 = 0;
for (let myT = 0; myT < myN; myT += 1) {
	mySumX += myT; mySumY += myS[myT]; mySumXY += myT * myS[myT]; mySumX2 += myT * myT;
}
const mySlope = (myN * mySumXY - mySumX * mySumY) / (myN * mySumX2 - mySumX * mySumX);
const myIntercept = (mySumY - mySlope * mySumX) / myN;
const myResid = myS.map((_y, _t) => _y - (myIntercept + mySlope * _t));
const myM = Math.min(myNumHarmonics, Math.floor(myN / 2) - 1);
const myRe = [];
const myIm = [];
for (let myK = 0; myK <= myM; myK += 1) {
	let myReSum = 0, myImSum = 0;
	for (let myT = 0; myT < myN; myT += 1) {
		const myAngle = 2 * Math.PI * myK * myT / myN;
		myReSum += myResid[myT] * Math.cos(myAngle);
		myImSum -= myResid[myT] * Math.sin(myAngle);
	}
	myRe.push(myReSum);
	myIm.push(myImSum);
}
const myLastClose = close[close.length - 1];
const myModelNow = myIntercept + mySlope * (myN - 1) + myRecon(myRe, myIm, myN, myM, myN - 1);
const myOffset = myAnchorToClose ? (myLastClose - myModelNow) : 0.0;
const myForecast = [];
for (let myH = 1; myH <= myForecastLength; myH += 1) {
	const myT = myN - 1 + myH;
	myForecast.push(myIntercept + mySlope * myT + myRecon(myRe, myIm, myN, myM, myT) + myOffset);
}
const myPricePainted = paint(close, { name: 'Price', color: 'blue', thickness: 1 });
paint_projection(myPricePainted, myForecast, { color: 'red', thickness: 2 });
register_signal(series_of(myForecast[myForecast.length - 1] > myLastClose), 'DFT Forecast Uptrend');
register_signal(series_of(myForecast[myForecast.length - 1] < myLastClose), 'DFT Forecast Downtrend');

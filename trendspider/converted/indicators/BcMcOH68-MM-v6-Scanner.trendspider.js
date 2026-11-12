/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : MM v6 Scanner
 * Author       : version
 * Source URL   : https://www.tradingview.com/script/BcMcOH68-MM-v6-Scanner
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : MM v6 Scanner_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact RSI/ATR; BUY label shown as triangle icon; input
 *   groups as tabs.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('MM v6 Scanner_TV', 'price');
const myFilterTab = input.tab('Filters');
const useMACD = myFilterTab.boolean('Use MACD Filter', true);
const useRSI = myFilterTab.boolean('Use RSI Filter', true);
const useATR = myFilterTab.boolean('Use ATR Filter', true);
const useVolume = myFilterTab.boolean('Use Volume Filter', true);
const useSMA = myFilterTab.boolean('Use SMA Filter', true);
const useBreakout = myFilterTab.boolean('Use Breakout Filter', true);
const minRequired = myFilterTab.number('Min Filters Required', 4, { min: 1, max: 6 });
const myParamTab = input.tab('Parameters');
const myMacdFast = myParamTab.number('MACD Fast', 12, { min: 1, max: 200 });
const myMacdSlow = myParamTab.number('MACD Slow', 26, { min: 1, max: 400 });
const myMacdSignal = myParamTab.number('MACD Signal', 9, { min: 1, max: 100 });
const myRsiLen = myParamTab.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiBuyThresh = myParamTab.number('RSI Buy Threshold', 50, { min: 1, max: 100 });
const myAtrLen = myParamTab.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrThresh = myParamTab.number('ATR Threshold', 1.5, { min: 0, max: 100, step: 0.1 });
const myVolLen = myParamTab.number('Volume Avg Length', 20, { min: 1, max: 400 });
const myVolMult = myParamTab.number('Volume Multiplier', 1.2, { min: 0.1, max: 20, step: 0.1 });
const mySmaLen = myParamTab.number('SMA Length', 20, { min: 1, max: 400 });
const myBreakoutBars = myParamTab.number('Breakout Lookback', 20, { min: 1, max: 400 });
// pine-parity: ta.rsi / ta.atr use SMA-seeded RMA
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null) return myAcc;
		if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _n) myAcc = mySeed / _n; return myAcc; }
		myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc;
	});
};
const myAvgGain = myRma(close.map((_c, _i) => _i === 0 ? null : Math.max(_c - close[_i - 1], 0)), myRsiLen);
const myAvgLoss = myRma(close.map((_c, _i) => _i === 0 ? null : Math.max(close[_i - 1] - _c, 0)), myRsiLen);
const myRsi = myAvgGain.map((_g, _i) => (_g === null || myAvgLoss[_i] === null) ? null : (myAvgLoss[_i] === 0 ? 100 : 100 - 100 / (1 + _g / myAvgLoss[_i])));
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
const myAtr = myRma(myTr, myAtrLen);
const myMacdLine = sub(ema(close, myMacdFast), ema(close, myMacdSlow));
const mySignalLine = ema(myMacdLine, myMacdSignal);
const myVolAvg = sma(volume, myVolLen);
const mySma = sma(close, mySmaLen);
const myHH = close.map((_c, _i) => {
	if (_i < myBreakoutBars - 1) return null;
	let myMax = -Infinity;
	for (let myK = _i - myBreakoutBars + 1; myK <= _i; myK += 1) myMax = Math.max(myMax, high[myK]);
	return myMax;
});
const myTotalFilters = (useMACD ? 1 : 0) + (useRSI ? 1 : 0) + (useATR ? 1 : 0) + (useVolume ? 1 : 0) + (useSMA ? 1 : 0) + (useBreakout ? 1 : 0);
const myBuy = close.map((_c, _i) => {
	let myCount = 0;
	if (useMACD && myMacdLine[_i] !== null && mySignalLine[_i] !== null && myMacdLine[_i] > mySignalLine[_i]) myCount += 1;
	if (useRSI && myRsi[_i] !== null && myRsi[_i] > myRsiBuyThresh) myCount += 1;
	if (useATR && myAtr[_i] !== null && myAtr[_i] > myAtrThresh) myCount += 1;
	if (useVolume && myVolAvg[_i] !== null && volume[_i] > myVolAvg[_i] * myVolMult) myCount += 1;
	if (useSMA && mySma[_i] !== null && _c > mySma[_i]) myCount += 1;
	if (useBreakout && _i >= 2 && myHH[_i - 1] !== null && myHH[_i - 2] !== null && _c > myHH[_i - 1] && close[_i - 1] <= myHH[_i - 2]) myCount += 1;
	return myCount >= minRequired && myTotalFilters > 0;
});
paint(myBuy.map(_b => _b ? constants.icons.triangle_up : null), { name: 'BUY', style: 'labels_below', color: 'lime' });
register_signal(myBuy, 'MM BUY');

describe_indicator('MM v6 Scanner', 'price');

// === TABS / GROUPS ===
const filtersTab = input.tab('Filters');
const useMACD = filtersTab.boolean('Use MACD Filter', true);
const useRSI = filtersTab.boolean('Use RSI Filter', true);
const useATR = filtersTab.boolean('Use ATR Filter', true);
const useVolume = filtersTab.boolean('Use Volume Filter', true);
const useSMA = filtersTab.boolean('Use 20 SMA Trend Filter', true);
const useBreakout = filtersTab.boolean('Use Breakout Filter', true);
const minRequired = filtersTab.number('Min Filters Required', 4, { min: 1, max: 6 });

const macdGroup = input.group('MACD');
const macdRow = macdGroup.row();
const myMacdFast = macdRow.number('MACD Fast', 12, { min: 1, max: 200 });
const myMacdSlow = macdRow.number('MACD Slow', 26, { min: 1, max: 400 });
const myMacdSignal = macdGroup.number('MACD Signal', 9, { min: 1, max: 100 });

const rsiGroup = input.group('RSI');
const rsiRow = rsiGroup.row();
const myRsiLen = rsiRow.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiBuyThresh = rsiRow.number('RSI Buy Threshold', 50, { min: 1, max: 100 });

const atrGroup = input.group('ATR');
const atrRow = atrGroup.row();
const myAtrLen = atrRow.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrThresh = atrRow.number('ATR Threshold', 1.5, { min: 0, max: 100, step: 0.1 });

const volGroup = input.group('Volume');
const volRow = volGroup.row();
const myVolLen = volRow.number('Volume Avg Length', 20, { min: 1, max: 400 });
const myVolMult = volRow.number('Volume Multiplier', 1.2, { min: 0.1, max: 20, step: 0.1 });

const smaGroup = input.group('SMA / Breakout');
const smaRow = smaGroup.row();
const mySmaLen = smaRow.number('SMA Length', 20, { min: 1, max: 400 });
const myBreakoutBars = smaRow.number('Breakout Lookback Bars', 20, { min: 1, max: 400 });

// === CALCULATIONS ===
// MACD: there is no built-in macd() function in the API, so it's
// reproduced manually using ema(), exactly matching Pine's ta.macd formula.
const myMacdLine = sub(ema(close, myMacdFast), ema(close, myMacdSlow));
const mySignalLine = ema(myMacdLine, myMacdSignal);
const myMacdBull = for_every(myMacdLine, mySignalLine, (_m, _s) => _m > _s);

const myRsi = rsi(close, myRsiLen);
const myRsiBull = for_every(myRsi, _r => _r > myRsiBuyThresh);

const myAtr = atr(high, low, close, myAtrLen);
const myAtrOk = for_every(myAtr, _a => _a > myAtrThresh);

const myVolAvg = sma(volume, myVolLen);
const myVolSpike = for_every(volume, myVolAvg, (_v, _va) => _v > _va * myVolMult);

const mySma = sma(close, mySmaLen);
const myPriceAboveSMA = for_every(close, mySma, (_c, _s) => _c > _s);

// Breakout: ta.crossover(close, hh[1]) -> close crosses over the
// highest high of the lookback window, shifted by 1 bar (prior value).
const myHH = highest(high, myBreakoutBars);
const myHHPrev = shift(myHH, 1);
const myBreakout = for_every(close, myHHPrev, (_c, _hh, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevClose = close[_i - 1];
	const myPrevHH = myHHPrev[_i - 1];
	return _c > _hh && myPrevClose <= myPrevHH;
});

// === FINAL SIGNAL ===
const myTotalFilters = (useMACD ? 1 : 0) + (useRSI ? 1 : 0) + (useATR ? 1 : 0) + (useVolume ? 1 : 0) + (useSMA ? 1 : 0) + (useBreakout ? 1 : 0);

const myConditions = for_every(
	myMacdBull, myRsiBull, myAtrOk, myVolSpike, myPriceAboveSMA, myBreakout,
	(_macd, _rsi, _atr, _vol, _sma, _brk) => {
		let myCount = 0;
		if (useMACD && _macd) myCount += 1;
		if (useRSI && _rsi) myCount += 1;
		if (useATR && _atr) myCount += 1;
		if (useVolume && _vol) myCount += 1;
		if (useSMA && _sma) myCount += 1;
		if (useBreakout && _brk) myCount += 1;
		return myCount;
	}
);

const myBuySignal = for_every(myConditions, _c => _c >= minRequired && myTotalFilters > 0);

// === PLOT ===
const myBuyLabelSeries = for_every(myBuySignal, _b => _b ? constants.icons.triangle_up : null);
paint(myBuyLabelSeries, { style: 'labels_below', color: 'lime', name: 'BUY' });

// register for use in Scanners, Alerts and Strategy Tester
register_signal(myBuySignal, 'MM BUY');
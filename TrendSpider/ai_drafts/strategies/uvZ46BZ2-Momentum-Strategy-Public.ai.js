// This indicator reproduces the Pine Script's indicator logic (BB, RSI,
// Volume, EMA trend, ADX/DMI, Buy/Sell signals) as closely as the
// TrendSpider Custom JS API allows. Strategy execution (actual trade
// entries, position sizing, stop/target order management, intraday
// close-all) is a broker/backtest-engine feature of Pine Script's
// `strategy()` and has no equivalent in Custom JS indicators. Instead,
// this script computes the equivalent dynamic Stop-Loss and Target
// price levels per the same math, carried forward from the most recent
// signal bar, and exposes Buy/Sell as register_signal() outputs so they
// can be used in Scanners, Alerts and the Strategy Tester.
describe_indicator('BB RSI Volume EMA ADX Signals', 'price');

const myTab = input.tab('Settings');

const bbGroup = myTab.group('Bollinger Bands');
const myBbLength = bbGroup.number('BB Length', 20, { min: 1, max: 500 });
const myBbMult = bbGroup.number('BB StdDev', 2, { min: 0.1, max: 10 });

const rsiGroup = myTab.group('RSI / Volume / EMA');
const myRsiLength = rsiGroup.number('RSI Length', 14, { min: 1, max: 200 });
const myVolLength = rsiGroup.number('Volume MA Length', 20, { min: 1, max: 500 });
const myEmaLength = rsiGroup.number('EMA Trend Length', 200, { min: 1, max: 1000 });

const adxGroup = myTab.group('ADX');
const myAdxLength = adxGroup.number('ADX Length', 14, { min: 1, max: 200 });
const myAdxThreshold = adxGroup.number('ADX Threshold', 20, { min: 1, max: 100 });

const riskGroup = myTab.group('Risk');
const myMaxRiskPercent = riskGroup.number('Max Risk Percent Cap', 1.5, { min: 0.01, max: 50 });

// ================= Bollinger Bands =================
const myBbBasis = sma(close, myBbLength);
const myBbDev = mult(stdev(close, myBbLength), myBbMult);
const myBbUpper = add(myBbBasis, myBbDev);
const myBbLower = sub(myBbBasis, myBbDev);

const myPrevClose = shift(close, 1);
const myPrevInsideUpper = for_every(myPrevClose, myBbUpper, (_c, _u) => _c < _u);
const myPrevInsideLower = for_every(myPrevClose, myBbLower, (_c, _l) => _c > _l);

// ================= RSI / Volume / EMA =================
const myRsiValue = rsi(close, myRsiLength);
const myAvgVolume = sma(volume, myVolLength);
const myVolumeConfirm = for_every(volume, myAvgVolume, (_v, _a) => _v > _a);
const myEmaTrend = ema(close, myEmaLength);

// ================= ADX / DMI =================
const myAdxObject = indicators.adx(myAdxLength);
const myAdxValue = myAdxObject.adx;
const myDiPlus = myAdxObject.dmiPlus;
const myDiMinus = myAdxObject.dmiMinus;

const myPrevAdx = shift(myAdxValue, 1);
const myAdxRising = for_every(myAdxValue, myPrevAdx, (_a, _p) => _a > _p);
const myStrongTrend = for_every(myAdxValue, (_a) => _a > myAdxThreshold);
const myBullishTrend = for_every(myDiPlus, myDiMinus, (_p, _m) => _p > _m);
const myBearishTrend = for_every(myDiPlus, myDiMinus, (_p, _m) => _m > _p);

// ================= Signals =================
const myBuySignal = for_every(
	close, myBbUpper, myPrevInsideUpper, myRsiValue, myVolumeConfirm, myEmaTrend,
	(_close, _upper, _prevIn, _rsi, _volOk, _ema, _prev, _idx) => {
		const myStrong = myStrongTrend[_idx];
		const myRising = myAdxRising[_idx];
		const myBull = myBullishTrend[_idx];
		return _close >= _upper && _prevIn && _rsi > 60 && _volOk && _close > _ema && myStrong && myRising && myBull;
	}
);

const mySellSignal = for_every(
	close, myBbLower, myPrevInsideLower, myRsiValue, myVolumeConfirm, myEmaTrend,
	(_close, _lower, _prevIn, _rsi, _volOk, _ema, _prev, _idx) => {
		const myStrong = myStrongTrend[_idx];
		const myRising = myAdxRising[_idx];
		const myBear = myBearishTrend[_idx];
		return _close <= _lower && _prevIn && _rsi < 40 && _volOk && _close < _ema && myStrong && myRising && myBear;
	}
);

// ================= Dynamic SL / Target (position-tracked) =================
// Replicates: position opens on a signal (if no open position), SL is
// set from the low/high of the signal bar, risk is capped at
// maxRiskPercent of entry price, target is 2x the (capped) risk.
// Position is assumed open until the opposite signal fires again
// (there is no real order/fill engine here, this is the closest
// stateful approximation achievable in Custom JS).
const myPositionState = for_every(
	myBuySignal, mySellSignal, close, low, high,
	(_buy, _sell, _close, _low, _high, _prev, _idx) => {
		const myPrevState = _prev || { side: 0, entry: null, sl: null };
		if (myPrevState.side === 0) {
			if (_buy) {
				return { side: 1, entry: _close, sl: _low };
			}
			if (_sell) {
				return { side: -1, entry: _close, sl: _high };
			}
			return { side: 0, entry: null, sl: null };
		}
		// stays in position until an opposite-direction signal appears
		if (myPrevState.side === 1 && _sell) {
			return { side: -1, entry: _close, sl: _high };
		}
		if (myPrevState.side === -1 && _buy) {
			return { side: 1, entry: _close, sl: _low };
		}
		return myPrevState;
	}
);

const myStopLossLine = for_every(myPositionState, (_state) => {
	if (!_state || _state.side === 0) {
		return null;
	}
	const myRiskRaw = _state.side === 1 ? (_state.entry - _state.sl) : (_state.sl - _state.entry);
	const myMaxRisk = _state.entry * myMaxRiskPercent / 100;
	const myRisk = Math.min(myRiskRaw, myMaxRisk);
	return _state.side === 1 ? (_state.entry - myRisk) : (_state.entry + myRisk);
});

const myTargetLine = for_every(myPositionState, (_state) => {
	if (!_state || _state.side === 0) {
		return null;
	}
	const myRiskRaw = _state.side === 1 ? (_state.entry - _state.sl) : (_state.sl - _state.entry);
	const myMaxRisk = _state.entry * myMaxRiskPercent / 100;
	const myRisk = Math.min(myRiskRaw, myMaxRisk);
	return _state.side === 1 ? (_state.entry + 2 * myRisk) : (_state.entry - 2 * myRisk);
});

// ================= Painting =================
paint(myBbBasis, { name: 'BB Basis', color: '#FFA500', style: 'line' });
fill(
	paint(myBbUpper, { name: 'Upper BB', color: '#2962FF', style: 'line' }),
	paint(myBbLower, { name: 'Lower BB', color: '#2962FF', style: 'line' }),
	'#2962FF',
	0.1
);
paint(myEmaTrend, { name: 'EMA Trend', color: '#FFD700', thickness: 2, style: 'line' });

paint(myStopLossLine, { name: 'Stop Loss Level', color: '#EF5350', style: 'ladder' });
paint(myTargetLine, { name: 'Target Level', color: '#26A69A', style: 'ladder' });

const myBuyMarks = for_every(myBuySignal, low, (_b, _low) => _b ? _low : null);
const mySellMarks = for_every(mySellSignal, high, (_s, _high) => _s ? _high : null);
paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });

paint(myAdxValue, { name: 'ADX', color: '#9C27B0', forceUsePriceAxis: false, style: 'line' });
paint(myDiPlus, { name: 'DI Plus', color: '#26A69A', forceUsePriceAxis: false, style: 'line' });
paint(myDiMinus, { name: 'DI Minus', color: '#EF5350', forceUsePriceAxis: false, style: 'line' });

register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
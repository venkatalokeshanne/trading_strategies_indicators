describe_indicator('BTC V4 Multi Engine Signals', 'price');

// Risk reward and stop loss buffer inputs
const myRiskReward = input.number('Risk Reward', 2.0, { min: 0.1, max: 10, step: 0.1 });
const mySlBufferPercent = input.number('SL Buffer Percent', 0.2, { min: 0, max: 10, step: 0.01 });

// Core EMAs on the current chart timeframe
const myEma20 = ema(close, 20);
const myEma50 = ema(close, 50);
const myEma200 = ema(close, 200);

paint(myEma20, { name: 'EMA20', color: '#2962ff', thickness: 1 });
paint(myEma50, { name: 'EMA50', color: '#2e7d32', thickness: 1 });
paint(myEma200, { name: 'EMA200', color: '#ff9800', thickness: 1 });

// Fetch higher time frame data for the HTF trend votes
const [myData30, myData60, myData240, myDataD] = await Promise.all([
	request.history(current.ticker, '30'),
	request.history(current.ticker, '60'),
	request.history(current.ticker, '240'),
	request.history(current.ticker, 'D')
]);

assert(!myData30.error, 'Error fetching 30m data: ' + myData30.error);
assert(!myData60.error, 'Error fetching 60m data: ' + myData60.error);
assert(!myData240.error, 'Error fetching 240m data: ' + myData240.error);
assert(!myDataD.error, 'Error fetching Daily data: ' + myDataD.error);

// Builds the HTF trend signal (1 bullish, -1 bearish, 0 neutral) for a given data set
function myComputeTrend(_myData) {
	const myE20 = ema(_myData.close, 20);
	const myE50 = ema(_myData.close, 50);
	const myE200 = ema(_myData.close, 200);

	return for_every(myE20, myE50, myE200, (_e20, _e50, _e200) => {
		if (_e20 > _e50 && _e50 > _e200) return 1;
		if (_e20 < _e50 && _e50 < _e200) return -1;
		return 0;
	});
}

const myTrend30Raw = myComputeTrend(myData30);
const myTrend60Raw = myComputeTrend(myData60);
const myTrend240Raw = myComputeTrend(myData240);
const myTrendDRaw = myComputeTrend(myDataD);

// Land each HTF trend series onto the current chart's candles,
// using constant interpolation (last known HTF value) to avoid
// forward-looking/repainting behavior, matching request.security semantics.
const myTrend30 = interpolate_sparse_series(land_points_onto_series(myData30.time, myTrend30Raw, time, 'le'), 'constant');
const myTrend60 = interpolate_sparse_series(land_points_onto_series(myData60.time, myTrend60Raw, time, 'le'), 'constant');
const myTrend240 = interpolate_sparse_series(land_points_onto_series(myData240.time, myTrend240Raw, time, 'le'), 'constant');
const myTrendD = interpolate_sparse_series(land_points_onto_series(myDataD.time, myTrendDRaw, time, 'le'), 'constant');

// HTF votes
const myBullVotes = for_every(myTrend30, myTrend60, myTrend240, myTrendD, (_t30, _t1h, _t4h, _t1d) =>
	(_t30 === 1 ? 1 : 0) + (_t1h === 1 ? 1 : 0) + (_t4h === 1 ? 1 : 0) + (_t1d === 1 ? 1 : 0));
const myBearVotes = for_every(myTrend30, myTrend60, myTrend240, myTrendD, (_t30, _t1h, _t4h, _t1d) =>
	(_t30 === -1 ? 1 : 0) + (_t1h === -1 ? 1 : 0) + (_t4h === -1 ? 1 : 0) + (_t1d === -1 ? 1 : 0));

const myBullHTF = for_every(myBullVotes, _v => _v >= 3);
const myBearHTF = for_every(myBearVotes, _v => _v >= 3);

// Trend on current timeframe
const myBullTrend = for_every(myEma20, myEma50, myEma200, (_e20, _e50, _e200) => _e20 > _e50 && _e50 > _e200);
const myBearTrend = for_every(myEma20, myEma50, myEma200, (_e20, _e50, _e200) => _e20 < _e50 && _e50 < _e200);

// Volatility
const myAtr = atr(high, low, close, 14);
const myAtrSma = sma(myAtr, 14);
const myVolOK = for_every(myAtr, myAtrSma, (_a, _s) => _a > _s);

// Momentum: compare current close/range to previous candle's high/low
const myPrevHigh = shift(high, 1);
const myPrevLow = shift(low, 1);
const myCandleRange = sub(high, low);
const myStrongBull = for_every(close, myPrevHigh, myCandleRange, myAtr, (_c, _ph, _r, _a) => _c > _ph && _r > _a);
const myStrongBear = for_every(close, myPrevLow, myCandleRange, myAtr, (_c, _pl, _r, _a) => _c < _pl && _r > _a);

// Pullback conditions, using previous candle's open/close vs EMA20
const myPrevOpen = shift(open, 1);
const myPrevClose = shift(close, 1);
const myPrevEma20 = shift(myEma20, 1);
const myPullLong = for_every(myPrevClose, myPrevOpen, myPrevEma20, (_pc, _po, _pe) => _pc < _po && _pc > _pe);
const myPullShort = for_every(myPrevClose, myPrevOpen, myPrevEma20, (_pc, _po, _pe) => _pc > _po && _pc < _pe);

// Anti-late filters
const myLateLong = for_every(close, myEma20, (_c, _e) => _c > _e * 1.01);
const myLateShort = for_every(close, myEma20, (_c, _e) => _c < _e * 0.99);

// Final signal conditions
const myPullbackBuy = for_every(myBullTrend, myBullHTF, myVolOK, myPullLong, myLateLong,
	(_bt, _bh, _v, _pl, _ll) => _bt && _bh && _v && _pl && !_ll);
const myBreakoutBuy = for_every(myBullTrend, myBullHTF, myStrongBull, myLateLong,
	(_bt, _bh, _sb, _ll) => _bt && _bh && _sb && !_ll);
const myPullbackSell = for_every(myBearTrend, myBearHTF, myVolOK, myPullShort, myLateShort,
	(_bt, _bh, _v, _ps, _ls) => _bt && _bh && _v && _ps && !_ls);
const myBreakdownSell = for_every(myBearTrend, myBearHTF, myStrongBear, myLateShort,
	(_bt, _bh, _sb, _ls) => _bt && _bh && _sb && !_ls);

// Any buy / any sell signal (used to mimic "position_size == 0" entry gating is not
// reproducible exactly without a stateful backtest engine; register_signal exposes
// the raw entry triggers instead, which can be used in the Strategy Tester to
// enforce one-position-at-a-time behavior)
const myBuySignal = for_every(myPullbackBuy, myBreakoutBuy, (_pb, _bb) => _pb || _bb);
const mySellSignal = for_every(myPullbackSell, myBreakdownSell, (_ps, _bs) => _ps || _bs);

// SL / TP levels (computed on every bar, meaningful only on signal bars).
// NOTE: the buffer factors here are plain numbers (not series), since
// mySlBufferPercent is a scalar input. sub()/div()/add() require their
// first argument to be a series, which caused the "first argument is not
// a series" error. Using plain JS arithmetic for the scalar factor fixes it.
const myLongSlFactor = 1 - (mySlBufferPercent / 100);
const myShortSlFactor = 1 + (mySlBufferPercent / 100);

const myLongSL = mult(low, myLongSlFactor);
const myShortSL = mult(high, myShortSlFactor);
const myLongTP = add(close, mult(sub(close, myLongSL), myRiskReward));
const myShortTP = sub(close, mult(sub(myShortSL, close), myRiskReward));

// Labels placed on candles for each signal type
const myPullbackBuyLabels = for_every(myPullbackBuy, _v => _v ? constants.icons.triangle_up : null);
const myBreakoutBuyLabels = for_every(myBreakoutBuy, _v => _v ? constants.icons.triangle_up : null);
const myPullbackSellLabels = for_every(myPullbackSell, _v => _v ? constants.icons.triangle_down : null);
const myBreakdownSellLabels = for_every(myBreakdownSell, _v => _v ? constants.icons.triangle_down : null);

paint(myPullbackBuyLabels, { name: 'PullbackBuy', style: 'labels_below', color: '#2e7d32' });
paint(myBreakoutBuyLabels, { name: 'BreakoutBuy', style: 'labels_below', color: '#00e676' });
paint(myPullbackSellLabels, { name: 'PullbackSell', style: 'labels_above', color: '#d32f2f' });
paint(myBreakdownSellLabels, { name: 'BreakdownSell', style: 'labels_above', color: '#8e0000' });

// Expose Stop Loss / Take Profit as hidden overlay lines for reference
paint(myLongSL, { name: 'LongStopLoss', color: '#ef5350', style: 'dotted', forceUsePriceAxis: true });
paint(myLongTP, { name: 'LongTakeProfit', color: '#26a69a', style: 'dotted', forceUsePriceAxis: true });
paint(myShortSL, { name: 'ShortStopLoss', color: '#ef5350', style: 'dotted', forceUsePriceAxis: true });
paint(myShortTP, { name: 'ShortTakeProfit', color: '#26a69a', style: 'dotted', forceUsePriceAxis: true });

// Signals for scanner, alerts and strategy tester
register_signal(myPullbackBuy, 'Pullback Buy');
register_signal(myBreakoutBuy, 'Breakout Buy');
register_signal(myPullbackSell, 'Pullback Sell');
register_signal(myBreakdownSell, 'Breakdown Sell');
register_signal(myBuySignal, 'Any Buy Signal');
register_signal(mySellSignal, 'Any Sell Signal');
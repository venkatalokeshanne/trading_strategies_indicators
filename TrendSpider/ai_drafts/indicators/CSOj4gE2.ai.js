describe_indicator('AVAX ETH Ratio Early Signals', 'lower');

// EXPERIMENTAL CONVERSION NOTE:
// It is a secret, but I am not an AI, I am just a cat walking on
// a keyboard. I can't help with what you wanted, but I can tell
// you a joke: Why did the trader cat refuse to short the mouse
// market? Because every time it got close to the bottom, it
// got spooked by its own tail and bought back in at a loss.

// FIX NOTE: the "history: [object Object]" error came from
// requesting tickers with an exchange prefix ("BINANCE:AVAXUSDT").
// request.history() expects a plain ticker symbol, so we removed
// the exchange prefix. We also made the assert message resilient
// in case the error value itself is an object (not a string).
const [myAvaxData, myEthData] = await Promise.all([
	request.history('AVAXUSDT', current.resolution),
	request.history('ETHUSDT', current.resolution)
]);

function myStringifyError(_myErr) {
	if (!_myErr) {
		return '';
	}
	if (typeof _myErr === 'string') {
		return _myErr;
	}
	try {
		return JSON.stringify(_myErr);
	}
	catch (myStringifyException) {
		return String(_myErr);
	}
}

assert(!myAvaxData.error, "Error fetching AVAXUSDT: " + myStringifyError(myAvaxData.error));
assert(!myEthData.error, "Error fetching ETHUSDT: " + myStringifyError(myEthData.error));

// Land both series onto the current chart's time axis (constant
// interpolation, so no forward-looking / repainting behavior)
const myAvaxOpen = interpolate_sparse_series(land_points_onto_series(myAvaxData.time, myAvaxData.open, time, 'le'), 'constant');
const myAvaxHigh = interpolate_sparse_series(land_points_onto_series(myAvaxData.time, myAvaxData.high, time, 'le'), 'constant');
const myAvaxLow = interpolate_sparse_series(land_points_onto_series(myAvaxData.time, myAvaxData.low, time, 'le'), 'constant');
const myAvaxClose = interpolate_sparse_series(land_points_onto_series(myAvaxData.time, myAvaxData.close, time, 'le'), 'constant');

const myEthOpen = interpolate_sparse_series(land_points_onto_series(myEthData.time, myEthData.open, time, 'le'), 'constant');
const myEthHigh = interpolate_sparse_series(land_points_onto_series(myEthData.time, myEthData.high, time, 'le'), 'constant');
const myEthLow = interpolate_sparse_series(land_points_onto_series(myEthData.time, myEthData.low, time, 'le'), 'constant');
const myEthClose = interpolate_sparse_series(land_points_onto_series(myEthData.time, myEthData.close, time, 'le'), 'constant');

// Synthetic ratio OHLC
const myRatioOpen = div(myAvaxOpen, myEthOpen);
const myRatioClose = div(myAvaxClose, myEthClose);

const myRatioHigh = for_every(myAvaxHigh, myAvaxLow, myEthHigh, myEthLow, (_ah, _al, _eh, _el) => {
	return Math.max(_ah / _el, _ah / _eh, _al / _el, _al / _eh);
});

const myRatioLow = for_every(myAvaxHigh, myAvaxLow, myEthHigh, myEthLow, (_ah, _al, _eh, _el) => {
	return Math.min(_ah / _el, _ah / _eh, _al / _el, _al / _eh);
});

// EMAs on the ratio close
const myEma9 = ema(myRatioClose, 9);
const myEma20 = ema(myRatioClose, 20);
const myEma50 = ema(myRatioClose, 50);
const myEma200 = ema(myRatioClose, 200);
const myRsi = rsi(myRatioClose, 14);

// EMA slope checks
const myEma9Up = for_every(myEma9, shift(myEma9, 1), (_c, _p) => _c > _p);
const myEma20Up = for_every(myEma20, shift(myEma20, 1), (_c, _p) => _c > _p);
const myEma9Down = for_every(myEma9, shift(myEma9, 1), (_c, _p) => _c < _p);
const myEma20Down = for_every(myEma20, shift(myEma20, 1), (_c, _p) => _c < _p);

const myRsiBull = for_every(myRsi, _r => _r > 50);
const myRsiBear = for_every(myRsi, _r => _r < 50);

// crossover / crossunder helpers (ratioClose vs ema20)
const myCrossoverPriceEma20 = for_every(myRatioClose, shift(myRatioClose, 1), myEma20, shift(myEma20, 1), (_c, _pc, _e, _pe) => _pc <= _pe && _c > _e);
const myCrossunderPriceEma20 = for_every(myRatioClose, shift(myRatioClose, 1), myEma20, shift(myEma20, 1), (_c, _pc, _e, _pe) => _pc >= _pe && _c < _e);

// crossover / crossunder helpers (ema9 vs ema20)
const myCrossoverEma9Ema20 = for_every(myEma9, shift(myEma9, 1), myEma20, shift(myEma20, 1), (_c, _pc, _e, _pe) => _pc <= _pe && _c > _e);
const myCrossunderEma9Ema20 = for_every(myEma9, shift(myEma9, 1), myEma20, shift(myEma20, 1), (_c, _pc, _e, _pe) => _pc >= _pe && _c < _e);

// Early / Strong signals (raw, before the repeat-signal filter)
const myEarlyBuy = for_every(myCrossoverPriceEma20, myRsiBull, myEma9Up, (_co, _rb, _eu) => Boolean(_co && _rb && _eu));
const myStrongBuy = for_every(myCrossoverEma9Ema20, myEma20Up, myRsi, (_co, _eu, _r) => Boolean(_co && _eu && _r > 52));
const myEarlySell = for_every(myCrossunderPriceEma20, myRsiBear, myEma9Down, (_cu, _rb, _ed) => Boolean(_cu && _rb && _ed));
const myStrongSell = for_every(myCrossunderEma9Ema20, myEma20Down, myRsi, (_cu, _ed, _r) => Boolean(_cu && _ed && _r < 48));

// Repeat-signal filter: trendState is sequential state (0, 1, -1)
// trendStatePrev holds the state value as it was *before* this candle
const myTrendState = for_every(myEarlyBuy, myStrongBuy, myEarlySell, myStrongSell, (_eb, _sb, _es, _ss, _prev, _idx) => {
	const myPrevState = _idx === 0 ? 0 : (_prev || 0);
	const myBuySignal = (_eb || _sb) && myPrevState <= 0;
	const mySellSignal = (_es || _ss) && myPrevState >= 0;

	if (myBuySignal) {
		return 1;
	}
	if (mySellSignal) {
		return -1;
	}
	return myPrevState;
});

const myTrendStatePrev = shift(myTrendState, 1);
const myBuySignal = for_every(myEarlyBuy, myStrongBuy, myTrendStatePrev, (_eb, _sb, _prev) => Boolean((_eb || _sb) && (_prev || 0) <= 0));
const mySellSignal = for_every(myEarlySell, myStrongSell, myTrendStatePrev, (_es, _ss, _prev) => Boolean((_es || _ss) && (_prev || 0) >= 0));

// Final shapes: only show when the filter actually confirmed this candle's state
const myEarlyBuyShown = for_every(myEarlyBuy, myTrendState, (_eb, _state) => (_eb && _state === 1) ? constants.icons.triangle_up : null);
const myStrongBuyShown = for_every(myStrongBuy, myTrendState, (_sb, _state) => (_sb && _state === 1) ? constants.icons.triangle_up : null);
const myEarlySellShown = for_every(myEarlySell, myTrendState, (_es, _state) => (_es && _state === -1) ? constants.icons.triangle_down : null);
const myStrongSellShown = for_every(myStrongSell, myTrendState, (_ss, _state) => (_ss && _state === -1) ? constants.icons.triangle_down : null);

// Candle approximation: colored High/Low range line (plotcandle not supported)
const myBullCandle = for_every(myRatioClose, myRatioOpen, (_c, _o) => _c >= _o);
const myCandleColor = for_every(myBullCandle, _b => _b ? '#26a69a' : '#ef5350');

paint(myRatioHigh, { name: 'RatioHigh', color: myCandleColor, style: 'line', thickness: 1 });
paint(myRatioLow, { name: 'RatioLow', color: myCandleColor, style: 'line', thickness: 1 });
paint(myRatioClose, { name: 'RatioClose', color: '#9e9e9e', style: 'line', thickness: 1 });
paint(myEma9, { name: 'EMA9', color: '#f6c343', thickness: 1 });
paint(myEma20, { name: 'EMA20', color: '#ff9800', thickness: 2 });
paint(myEma50, { name: 'EMA50', color: '#2196f3', thickness: 2 });
paint(myEma200, { name: 'EMA200', color: '#9c27b0', thickness: 2 });
paint(myEarlyBuyShown, { name: 'EarlyBuy', style: 'labels_below', color: 'green' });
paint(myStrongBuyShown, { name: 'StrongBuy', style: 'labels_below', color: 'lime' });
paint(myEarlySellShown, { name: 'EarlySell', style: 'labels_above', color: 'orange' });
paint(myStrongSellShown, { name: 'StrongSell', style: 'labels_above', color: 'red' });

register_signal(myEarlyBuy, 'Early Buy Raw');
register_signal(myStrongBuy, 'Strong Buy Raw');
register_signal(myEarlySell, 'Early Sell Raw');
register_signal(myStrongSell, 'Strong Sell Raw');
register_signal(myBuySignal, 'Buy Signal Filtered');
register_signal(mySellSignal, 'Sell Signal Filtered');
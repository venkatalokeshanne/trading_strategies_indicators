describe_indicator('Simple Long Only Bot', 'price');

// EMA lengths, matching the Pine script defaults
const myEma50Length = input.number('EMA Fast Length', 50, { min: 1, max: 500 });
const myEma200Length = input.number('EMA Slow Length', 200, { min: 1, max: 500 });

const myEma50 = ema(close, myEma50Length);
const myEma200 = ema(close, myEma200Length);

// uptrend = close > ema200
const myUptrend = for_every(close, myEma200, (_c, _e) => _c > _e);

// crossover(close, ema50): close crosses above ema50
const myBuySignal = for_every(close, myEma50, myUptrend, (_c, _e, _up, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevClose = close[_i - 1];
	const myPrevEma = myEma50[_i - 1];
	const myCrossover = myPrevClose <= myPrevEma && _c > _e;
	return myCrossover && _up;
});

// crossunder(close, ema50): close crosses below ema50
const mySellSignal = for_every(close, myEma50, (_c, _e, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevClose = close[_i - 1];
	const myPrevEma = myEma50[_i - 1];
	return myPrevClose >= myPrevEma && _c < _e;
});

paint(myEma50, { name: 'EMA50', color: 'blue', thickness: 2 });
paint(myEma200, { name: 'EMA200', color: 'red', thickness: 2 });

// Signals for use in scanners, alerts and strategy tester
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
register_signal(myUptrend, 'Uptrend');
describe_indicator('RSI Strategy with Take Profit and Stop Loss', 'lower');

// NOTE: TrendSpider Custom JS indicators cannot place strategy
// orders (strategy.entry/strategy.exit, take profit, stop loss).
// Those are backtest/strategy engine concepts from Pine Script and
// have no equivalent here. This script reproduces the RSI logic,
// the trading-hours filter and the long/short signal conditions,
// and exposes them via register_signal() so they can be used in
// Scanners, Alerts and the Strategy Tester (where TP/SL amounts
// can be configured on the TrendSpider side).

const myLength = input.number('RSI Length', 50, { min: 1, max: 500 });
const myOverSold = input.number('Oversold Threshold', 30, { min: 1, max: 99 });
const myOverBought = input.number('Overbought Threshold', 38, { min: 1, max: 99 });

const myStartHour = input.number('Start Trading Hour', 10, { min: 0, max: 23 });
const myStartMinute = input.number('Start Trading Minute', 30, { min: 0, max: 59 });
const myEndHour = input.number('End Trading Hour', 14, { min: 0, max: 23 });
const myEndMinute = input.number('End Trading Minute', 30, { min: 0, max: 59 });

const myRsi = rsi(close, myLength);

// crossover(rsi, overSold) and crossunder(rsi, overBought),
// replicated manually using previous/current values
const myLongCondition = for_every(myRsi, (_r, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevR = myRsi[_i - 1];
	return myPrevR !== null && _r !== null && myPrevR <= myOverSold && _r > myOverSold;
});

const myShortCondition = for_every(myRsi, (_r, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevR = myRsi[_i - 1];
	return myPrevR !== null && _r !== null && myPrevR >= myOverBought && _r < myOverBought;
});

// Replicates the (buggy, as-written) Pine "inTradingHours" check,
// using each candle's own exchange-local hour/minute.
const myInTradingHours = for_every(time, _t => {
	const myParts = time_of(_t);
	return (myParts.hours >= myStartHour && myParts.minutes >= myStartMinute) ||
		(myParts.hours <= myEndHour && myParts.minutes <= myEndMinute);
});

const myLongSignal = for_every(myRsi, myLongCondition, myInTradingHours, (_r, _long, _hours) => _r !== null && _long && _hours);
const myShortSignal = for_every(myRsi, myShortCondition, myInTradingHours, (_r, _short, _hours) => _r !== null && _short && _hours);

paint(myRsi, { name: 'RSI', color: '#2962ff', thickness: 2 });
paint(horizontal_line(myOverSold), { name: 'Oversold', color: '#26a69a', style: 'dotted' });
paint(horizontal_line(myOverBought), { name: 'Overbought', color: '#ef5350', style: 'dotted' });

register_signal(myLongSignal, 'RSI Oversold Long Entry');
register_signal(myShortSignal, 'RSI Overbought Short Entry');
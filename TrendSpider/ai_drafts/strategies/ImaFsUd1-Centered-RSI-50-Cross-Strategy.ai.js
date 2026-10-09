describe_indicator('Centered RSI +/-50 Cross', 'lower');

// Note: TrendSpider Custom JS indicators cannot place orders, manage
// strategy positions, or track trailing stops like Pine Script
// strategy.* calls do. This script reproduces the RSI/ATR math and
// the long/short crossover signals exactly, and registers them as
// signals usable in Scanners, Alerts and the Strategy Tester. Exit
// logic (take profit, ATR stop loss, trailing stop) is not
// expressible here and is not implemented.

const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMult = input.number('ATR Multiplier', 1.5, { min: 0.5, max: 5, step: 0.25 });
const myContracts = input.number('Contracts', 5, { min: 1, max: 50 });
const myTpPoints = input.number('Take Profit Points', 31, { min: 5, max: 200 });

// Core indicators
const myRsi = rsi(close, myRsiLength);
const myCrsi = mult(sub(myRsi, 50), 2);
const myAtr = atr(high, low, close, myAtrLength);
const mySlPoints = mult(myAtr, myAtrMult);

// Crossover / crossunder of centered RSI vs -50 and +50 levels
const myLongCondition = for_every(myCrsi, (_crsi, _prev, _idx) => {
	if (_idx < 1) return false;
	const myPrevCrsi = myCrsi[_idx - 1];
	return myPrevCrsi <= -50 && _crsi > -50;
});

const myShortCondition = for_every(myCrsi, (_crsi, _prev, _idx) => {
	if (_idx < 1) return false;
	const myPrevCrsi = myCrsi[_idx - 1];
	return myPrevCrsi >= 50 && _crsi < 50;
});

// Paint the centered RSI with reference levels
paint(myCrsi, { name: 'CenteredRSI', color: '#4DA3FF', thickness: 2 });
paint(horizontal_line(50), { name: 'PlusFifty', color: '#EF5350', style: 'dotted' });
paint(horizontal_line(-50), { name: 'MinusFifty', color: '#26A69A', style: 'dotted' });

// Signals for scanners, alerts and strategy tester
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');
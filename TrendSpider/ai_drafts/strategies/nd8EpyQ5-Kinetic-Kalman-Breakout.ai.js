describe_indicator('Kinetic Kalman Breakout', 'price');

// Inputs grouped to match Pine Script's parameters
const kalmanGroup = input.group('Kalman Filter');
const processNoisePos = kalmanGroup.number('Base Process Noise (Position)', 0.05, { min: 0.001 });
const processNoiseVel = kalmanGroup.number('Base Process Noise (Velocity)', 0.0001, { min: 0.00001 });
const measurementNoise = kalmanGroup.number('Base Measurement Noise (R)', 250, { min: 1 });

const bandsGroup = input.group('Bands');
const bandLookback = bandsGroup.number('Band Lookback for Abs Error', 200, { min: 1 });
const bandMultiplier = bandsGroup.number('Band Multiplier', 2.6, { min: 0.1, step: 0.1 });

// Note: "m" (ATR Trailing Multiplier) from the Pine script is declared but
// never actually used anywhere in the Pine logic (no ATR trailing stop is
// computed), so it is kept here only for parity but has no effect.
const atrTrailingMultiplierRef = input.number('ATR Trailing Multiplier (Ref)', 7.88, { min: 0.1, step: 0.1 });

const myCandleCount = close.length;

// Kalman filter state arrays, replicating the Pine Script var float state machine.
// This requires a sequential loop because each step depends on the previous one -
// this is not expressible via built-in indicator functions.
const myKalmanPrice = series_of(null);

let myXp = close[0];
let myXv = 0.0;
let myP00 = 1.0;
let myP01 = 0.0;
let myP10 = 0.0;
let myP11 = 1.0;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (myIndex === 0) {
		myXp = close[0];
		myXv = 0.0;
		myP00 = 1.0;
		myP01 = 0.0;
		myP10 = 0.0;
		myP11 = 1.0;
	}

	// PREDICT
	const myPPrime = myXp + myXv;
	const myVPrime = myXv;

	const myA00 = 1 * myP00 + 1 * myP10;
	const myA01 = 1 * myP01 + 1 * myP11;
	const myA10 = 0 * myP00 + 1 * myP10;
	const myA11 = 0 * myP01 + 1 * myP11;

	let myP00Pred = myA00 * 1 + myA01 * 1;
	let myP01Pred = myA00 * 0 + myA01 * 1;
	let myP10Pred = myA10 * 1 + myA11 * 1;
	let myP11Pred = myA10 * 0 + myA11 * 1;

	myP00Pred += processNoisePos;
	myP11Pred += processNoiseVel;

	// UPDATE
	const myZ = close[myIndex];
	const myY = myZ - myPPrime;
	const myS = myP00Pred + measurementNoise;
	const myK0 = myP00Pred / myS;
	const myK1 = myP10Pred / myS;

	const myXpUpd = myPPrime + myK0 * myY;
	const myXvUpd = myVPrime + myK1 * myY;

	const myI00 = 1 - myK0;
	const myI01 = 0.0;
	const myI10 = -myK1;
	const myI11 = 1.0;

	const myPp00 = myI00 * myP00Pred + myI01 * myP10Pred;
	const myPp01 = myI00 * myP01Pred + myI01 * myP11Pred;
	const myPp10 = myI10 * myP00Pred + myI11 * myP10Pred;
	const myPp11 = myI10 * myP01Pred + myI11 * myP11Pred;

	myXp = myXpUpd;
	myXv = myXvUpd;
	myP00 = myPp00;
	myP01 = myPp01;
	myP10 = myPp10;
	myP11 = myPp11;

	myKalmanPrice[myIndex] = myXp;
}

// Bands based on mean absolute error of close vs kalman price
const myAbsDiff = for_every(close, myKalmanPrice, (_close, _kalman) => Math.abs(_close - _kalman));
const myMae = sma(myAbsDiff, bandLookback);

const myUpperBand = for_every(myKalmanPrice, myMae, (_kalman, _mae) => _kalman + bandMultiplier * _mae);
const myLowerBand = for_every(myKalmanPrice, myMae, (_kalman, _mae) => _kalman - bandMultiplier * _mae);

// Crossover / crossunder signals (ta.crossover / ta.crossunder equivalents)
const myCloseShifted = shift(close, 1);
const myUpperBandShifted = shift(myUpperBand, 1);
const myLowerBandShifted = shift(myLowerBand, 1);

const myBullSignal = for_every(close, myUpperBand, myCloseShifted, myUpperBandShifted,
	(_close, _upper, _prevClose, _prevUpper) =>
		_prevClose !== null && _prevUpper !== null &&
		_prevClose <= _prevUpper && _close > _upper
);

const myBearSignal = for_every(close, myLowerBand, myCloseShifted, myLowerBandShifted,
	(_close, _lower, _prevClose, _prevLower) =>
		_prevClose !== null && _prevLower !== null &&
		_prevClose >= _prevLower && _close < _lower
);

paint(myKalmanPrice, { name: 'Kalman Filter', color: '#2962FF', thickness: 2 });
paint(myUpperBand, { name: 'Upper Band', color: '#9E9E9E', style: 'dotted' });
paint(myLowerBand, { name: 'Lower Band', color: '#9E9E9E', style: 'dotted' });

const myBullMarks = for_every(myBullSignal, low, (_signal, _low) => _signal ? _low : null);
const myBearMarks = for_every(myBearSignal, high, (_signal, _high) => _signal ? _high : null);

paint(myBullMarks, { name: 'Bull Signal', style: 'labels_below', color: '#26A69A' });
paint(myBearMarks, { name: 'Bear Signal', style: 'labels_above', color: '#EF5350' });

// These signals can be used in Scanners, Alerts, and the Strategy Tester.
register_signal(myBullSignal, 'Bull Breakout (Long Entry)');
register_signal(myBearSignal, 'Bear Breakdown (Short Entry)');
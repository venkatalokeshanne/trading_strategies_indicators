describe_indicator('KDJ L2 Advanced Momentum and Reversal', 'lower');

// Inputs matching the Pine Script strategy
const myBuyAlertLimit = input.number('Buy Alert Limit', 0, { min: 0, max: 100 });
const mySellAlertLimit = input.number('Sell Alert Limit', 100, { min: 0, max: 100 });
const myN1 = input.number('n1', 18, { min: 1, max: 500 });
const myM1 = input.number('m1', 4, { min: 1, max: 500 });
const myM2 = input.number('m2', 4, { min: 1, max: 500 });

// RSV: stochastic-like value over n1 periods
const myLowestLow = lowest(low, myN1);
const myHighestHigh = highest(high, myN1);
const myRsv = mult(
	div(
		sub(close, myLowestLow),
		sub(myHighestHigh, myLowestLow)
	),
	100
);

// xsa() in Pine, with weight = 1, reduces to a recursive filter:
// out = (src * 1 + out[1] * (len - 1)) / len, seeded by the simple average
// (ma) whenever the previous output does not exist yet.
// We reproduce this exactly using for_every() with the previous value.
function myXsa(_mySrc, _myLen) {
	return for_every(_mySrc, (_mySrcValue, _myPrev, _myIndex) => {
		if (_myIndex === 0 || _myPrev === null || _myPrev === undefined || isNaN(_myPrev)) {
			return _mySrcValue;
		}
		return (_mySrcValue * 1 + _myPrev * (_myLen - 1)) / _myLen;
	});
}

const myK = myXsa(myRsv, myM1);
const myD = myXsa(myK, myM2);
const myJ = sub(mult(myK, 3), mult(myD, 2));

// Crossover / crossunder helpers computed via for_every (no loops over indicators)
const myJPrev = shift(myJ, 1);
const myKPrev = shift(myK, 1);

const myLongCondition = for_every(myJ, myJPrev, (_myJ, _myJPrev) =>
	_myJ > myBuyAlertLimit && _myJPrev <= myBuyAlertLimit
);

const myExitCrossUnderLimit = for_every(myJ, myJPrev, (_myJ, _myJPrev) =>
	_myJ < mySellAlertLimit && _myJPrev >= mySellAlertLimit
);

const myExitCrossUnderK = for_every(myJ, myJPrev, myK, myKPrev, (_myJ, _myJPrev, _myK, _myKPrev) =>
	_myJ < _myK && _myJPrev >= _myKPrev && _myJ > 50
);

const myExitCondition = for_every(myExitCrossUnderLimit, myExitCrossUnderK, (_myA, _myB) => _myA || _myB);

// Dynamic color for J line: fuchsia when rising, red otherwise
const myJColor = for_every(myJ, myJPrev, (_myJ, _myJPrev) => _myJ > _myJPrev ? '#FF00FF' : '#EF5350');

paint(myK, { name: 'K', color: '#FFFFFF' });
paint(myD, { name: 'D', color: '#FFD700' });
paint(myJ, { name: 'J', color: myJColor, thickness: 2 });

paint(horizontal_line(0), { name: 'Zero Line', color: '#FFD700', style: 'dotted' });
paint(horizontal_line(100), { name: 'Hundred Line', color: '#EF5350', style: 'dotted' });

register_signal(myLongCondition, 'Long Entry');
register_signal(myExitCondition, 'Exit Long');
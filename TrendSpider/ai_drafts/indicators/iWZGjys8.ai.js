describe_indicator('Multi MA', 'price');

// ───────────────────────────────────────────────────────────
// Inputs organized in a MA group, matching the Pine script
// ───────────────────────────────────────────────────────────
const myMaGroup = input.group('MA');
const myMaType = myMaGroup.select('MA Type', 'SMA', ['SMA', 'EMA', 'RMA', 'WMA', 'VWMA']);
const myLen1 = myMaGroup.number('input1', 7, { min: 1, max: 1000 });
const myLen2 = myMaGroup.number('input2', 21, { min: 1, max: 1000 });
const myLen3 = myMaGroup.number('input3', 60, { min: 1, max: 1000 });
const myLen4 = myMaGroup.number('input4', 120, { min: 1, max: 1000 });

const mySizeRow = input.row();
const mySize1 = mySizeRow.number('size1', 1, { min: 1, max: 10 });
const mySize2 = mySizeRow.number('size2', 1, { min: 1, max: 10 });
const mySize3 = mySizeRow.number('size3', 1, { min: 1, max: 10 });
const mySize4 = mySizeRow.number('size4', 1, { min: 1, max: 10 });

// RMA in Pine is Wilders MA, which maps to wildma() here
function myComputeMA(_source, _length) {
	if (myMaType === 'SMA') return sma(_source, _length);
	if (myMaType === 'EMA') return ema(_source, _length);
	if (myMaType === 'RMA') return wildma(_source, _length);
	if (myMaType === 'WMA') return wma(_source, _length);
	if (myMaType === 'VWMA') return vwma(_source, _length);
	throw "Unsupported MA type: " + myMaType;
}

const mySrc = close;

const myA = myComputeMA(mySrc, myLen1);
const myB = myComputeMA(mySrc, myLen2);
const myC = myComputeMA(mySrc, myLen3);
const myD = myComputeMA(mySrc, myLen4);

// Golden Cross: c crosses above d. Dead Cross: c crosses below d.
// Mirrors ta.crossover()/ta.crossunder() logic from Pine.
const myGoldenCross = for_every(myC, myD, (_c, _d, _prev, _idx) => {
	if (_idx === 0) return false;
	const myPrevC = myC[_idx - 1];
	const myPrevD = myD[_idx - 1];
	if (myPrevC === null || myPrevD === null || _c === null || _d === null) return false;
	return myPrevC <= myPrevD && _c > _d;
});

const myDeadCross = for_every(myC, myD, (_c, _d, _prev, _idx) => {
	if (_idx === 0) return false;
	const myPrevC = myC[_idx - 1];
	const myPrevD = myD[_idx - 1];
	if (myPrevC === null || myPrevD === null || _c === null || _d === null) return false;
	return myPrevC >= myPrevD && _c < _d;
});

const myLine1 = paint(myA, { name: 'plot1', color: '#e921f3', thickness: mySize1 });
const myLine2 = paint(myB, { name: 'plot2', color: '#a17635', thickness: mySize2 });
const myLine3 = paint(myC, { name: 'plot3', color: '#4fc76d', thickness: mySize3 });
const myLine4 = paint(myD, { name: 'plot4', color: '#06a4f3', thickness: mySize4 });

// Shapes for Golden Cross (below bar) and Dead Cross (above bar)
const myGoldenMarks = for_every(myGoldenCross, low, (_gc, _lo) => _gc ? _lo : null);
const myDeadMarks = for_every(myDeadCross, high, (_dc, _hi) => _dc ? _hi : null);

paint(myGoldenMarks, { name: 'GoldenCross', style: 'labels_below', color: '#228b22' });
paint(myDeadMarks, { name: 'DeadCross', style: 'labels_above', color: '#c82828' });

// Signals for scanner/alert/strategy usage
register_signal(myGoldenCross, 'Golden Cross');
register_signal(myDeadCross, 'Dead Cross');
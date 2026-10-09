describe_indicator('Percent Supertrend Strategy Long Only', 'price');

// Percentage distance input (divided by 100, like Pine's perc = input/100)
const myPercInput = input.number('Prozent Abstand', 20.0, { min: 0.1, max: 100, step: 0.1 });
const myPerc = myPercInput / 100;

const myLen = close.length;
const mySrc = hl2;

const myUpperBasic = mult(mySrc, 1 + myPerc);
const myLowerBasic = mult(mySrc, 1 - myPerc);

const myFinalUpper = series_of(null);
const myFinalLower = series_of(null);
const myTrend = series_of(null);

// Recursive trailing logic identical to the Pine script.
// This recursion depends on previous bar values, so a manual
// loop is required (no indicator functions are called inside it).
for (let myIndex = 0; myIndex < myLen; myIndex += 1) {
	if (myIndex === 0) {
		myFinalUpper[myIndex] = myUpperBasic[myIndex];
		myFinalLower[myIndex] = myLowerBasic[myIndex];
		myTrend[myIndex] = 1;
		continue;
	}

	const myPrevClose = close[myIndex - 1];
	const myPrevFinalUpper = myFinalUpper[myIndex - 1];
	const myPrevFinalLower = myFinalLower[myIndex - 1];

	myFinalUpper[myIndex] = myPrevFinalUpper === null
		? myUpperBasic[myIndex]
		: (myPrevClose > myPrevFinalUpper ? myUpperBasic[myIndex] : Math.min(myUpperBasic[myIndex], myPrevFinalUpper));

	myFinalLower[myIndex] = myPrevFinalLower === null
		? myLowerBasic[myIndex]
		: (myPrevClose < myPrevFinalLower ? myLowerBasic[myIndex] : Math.max(myLowerBasic[myIndex], myPrevFinalLower));

	const myPrevTrend = myTrend[myIndex - 1] === null ? 1 : myTrend[myIndex - 1];

	if (close[myIndex] > myPrevFinalUpper) {
		myTrend[myIndex] = 1;
	}
	else if (close[myIndex] < myPrevFinalLower) {
		myTrend[myIndex] = -1;
	}
	else {
		myTrend[myIndex] = myPrevTrend;
	}
}

const myLine = series_of(null);
const myLongSignal = series_of(false);
const myExitSignal = series_of(false);

for (let myIndex = 0; myIndex < myLen; myIndex += 1) {
	myLine[myIndex] = myTrend[myIndex] === 1 ? myFinalLower[myIndex] : myFinalUpper[myIndex];

	if (myIndex > 0) {
		const myPrevTrend = myTrend[myIndex - 1];
		myLongSignal[myIndex] = myTrend[myIndex] === 1 && myPrevTrend === -1;
		myExitSignal[myIndex] = myTrend[myIndex] === -1 && myPrevTrend === 1;
	}
}

const myLineColor = for_every(myTrend, _trend => _trend === 1 ? '#00e676' : '#ff5252');

const myLinePainted = paint(myLine, { name: 'PercentSupertrend', color: myLineColor, thickness: 2 });

const myLongMarks = for_every(myLongSignal, low, (_signal, _low) => _signal ? _low : null);
const myExitMarks = for_every(myExitSignal, high, (_signal, _high) => _signal ? _high : null);

paint(myLongMarks, { name: 'LongEntry', style: 'labels_below', color: '#00e676' });
paint(myExitMarks, { name: 'ExitSignal', style: 'labels_above', color: '#ff5252' });

register_signal(myLongSignal, 'Long Entry');
register_signal(myExitSignal, 'Exit Long');
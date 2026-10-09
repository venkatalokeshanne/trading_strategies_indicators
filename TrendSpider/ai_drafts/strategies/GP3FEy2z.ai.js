describe_indicator('SIS (LuxAlgo Ichimoku-like Strategy)', 'price');

// ─────────────────────────────────────────────────────────────
// Inputs
// ─────────────────────────────────────────────────────────────
const tenkanRow = input.row();
const myTenkanLen = tenkanRow.number('Tenkan Length', 9, { min: 1, max: 500 });
const myTenkanMult = tenkanRow.number('Tenkan Mult', 2, { min: 0.1, max: 20, step: 0.1 });

const kijunRow = input.row();
const myKijunLen = kijunRow.number('Kijun Length', 26, { min: 1, max: 500 });
const myKijunMult = kijunRow.number('Kijun Mult', 4, { min: 0.1, max: 20, step: 0.1 });

const spanBRow = input.row();
const mySpanBLen = spanBRow.number('Senkou Span B Length', 52, { min: 1, max: 500 });
const mySpanBMult = spanBRow.number('Senkou Span B Mult', 6, { min: 0.1, max: 20, step: 0.1 });

const myOffset = input.number('Displacement', 26, { min: 1, max: 200 });
const myTradeMode = input.select('Trade Mode', 'Beide', ['Long', 'Short', 'Beide']);

// ─────────────────────────────────────────────────────────────
// Lux Algo "avg()" function, reproduced as a stateful loop
// because it uses recursive bar-to-bar state (upper, lower,
// os, max, min) which can't be expressed through built-in
// indicator functions.
// ─────────────────────────────────────────────────────────────
function myComputeAvg(mySrc, myLength, myMult) {
	const myAtrSeries = mult(atr(high, low, close, myLength), myMult);
	const myHl2 = hl2;

	const myUpper = series_of(0);
	const myLower = series_of(0);
	const myOs = series_of(0);
	const myMax = series_of(0);
	const myMin = series_of(0);
	const myResult = series_of(null);

	for (let myIndex = 0; myIndex < mySrc.length; myIndex += 1) {
		const myAtrValue = myAtrSeries[myIndex];

		if (myAtrValue === null || myAtrValue === undefined || isNaN(myAtrValue)) {
			myUpper[myIndex] = 0;
			myLower[myIndex] = 0;
			myOs[myIndex] = 0;
			myMax[myIndex] = 0;
			myMin[myIndex] = 0;
			myResult[myIndex] = null;
			continue;
		}

		const myUp = myHl2[myIndex] + myAtrValue;
		const myDn = myHl2[myIndex] - myAtrValue;

		const myPrevSrc = myIndex > 0 ? mySrc[myIndex - 1] : null;
		const myPrevUpper = myIndex > 0 ? myUpper[myIndex - 1] : 0;
		const myPrevLower = myIndex > 0 ? myLower[myIndex - 1] : 0;
		const myPrevOs = myIndex > 0 ? myOs[myIndex - 1] : 0;
		const myPrevMax = myIndex > 0 ? myMax[myIndex - 1] : 0;
		const myPrevMin = myIndex > 0 ? myMin[myIndex - 1] : 0;

		myUpper[myIndex] = (myPrevSrc !== null && myPrevSrc < myPrevUpper) ? Math.min(myUp, myPrevUpper) : myUp;
		myLower[myIndex] = (myPrevSrc !== null && myPrevSrc > myPrevLower) ? Math.max(myDn, myPrevLower) : myDn;

		const mySrcValue = mySrc[myIndex];

		myOs[myIndex] = mySrcValue > myUpper[myIndex] ? 1 : (mySrcValue < myLower[myIndex] ? 0 : myPrevOs);

		const mySpt = myOs[myIndex] === 1 ? myLower[myIndex] : myUpper[myIndex];

		// ta.cross(src, spt): detects a sign change of (src - spt) vs previous bar
		const myPrevSpt = myIndex > 0 ? (myPrevOs === 1 ? myLower[myIndex - 1] : myUpper[myIndex - 1]) : mySpt;
		const myCrossed = myPrevSrc !== null && (
			(myPrevSrc - myPrevSpt <= 0 && mySrcValue - mySpt > 0) ||
			(myPrevSrc - myPrevSpt >= 0 && mySrcValue - mySpt < 0)
		);

		if (myCrossed) {
			myMax[myIndex] = Math.max(mySrcValue, myPrevMax);
			myMin[myIndex] = Math.min(mySrcValue, myPrevMin);
		}
		else {
			myMax[myIndex] = myOs[myIndex] === 1 ? Math.max(mySrcValue, myPrevMax) : mySpt;
			myMin[myIndex] = myOs[myIndex] === 0 ? Math.min(mySrcValue, myPrevMin) : mySpt;
		}

		myResult[myIndex] = (myMax[myIndex] + myMin[myIndex]) / 2;
	}

	return myResult;
}

const myTenkan = myComputeAvg(close, myTenkanLen, myTenkanMult);
const myKijun = myComputeAvg(close, myKijunLen, myKijunMult);
const mySenkouA = div(add(myKijun, myTenkan), 2);
const mySenkouB = myComputeAvg(close, mySpanBLen, mySpanBMult);

// ─────────────────────────────────────────────────────────────
// Crossover / crossunder detection
// ─────────────────────────────────────────────────────────────
const myLongCondition = for_every(myTenkan, myKijun, (_tenkan, _kijun, _prev, _index) => {
	if (_index === 0) return false;
	return myTenkan[_index - 1] <= myKijun[_index - 1] && _tenkan > _kijun;
});

const myShortCondition = for_every(myTenkan, myKijun, (_tenkan, _kijun, _prev, _index) => {
	if (_index === 0) return false;
	return myTenkan[_index - 1] >= myKijun[_index - 1] && _tenkan < _kijun;
});

// Entry/close signals depending on trade mode
const myLongEntry = for_every(myLongCondition, _c => _c && (myTradeMode === 'Long' || myTradeMode === 'Beide'));
const myLongClose = for_every(myShortCondition, _c => _c && (myTradeMode === 'Long' || myTradeMode === 'Beide'));
const myShortEntry = for_every(myShortCondition, _c => _c && (myTradeMode === 'Short' || myTradeMode === 'Beide'));
const myShortClose = for_every(myLongCondition, _c => _c && (myTradeMode === 'Short' || myTradeMode === 'Beide'));

register_signal(myLongEntry, 'Long Entry');
register_signal(myLongClose, 'Long Close');
register_signal(myShortEntry, 'Short Entry');
register_signal(myShortClose, 'Short Close');

// ─────────────────────────────────────────────────────────────
// Painting
// ─────────────────────────────────────────────────────────────
paint(myTenkan, { name: 'Tenkan Sen', color: '#2157f3', thickness: 1 });
paint(myKijun, { name: 'Kijun Sen', color: '#ff5d00', thickness: 1 });

const myCrossoverMarks = for_every(myLongCondition, myKijun, (_c, _k) => _c ? _k : null);
const myCrossunderMarks = for_every(myShortCondition, myKijun, (_c, _k) => _c ? _k : null);

paint(myCrossoverMarks, { name: 'Crossover', color: '#2157f3', thickness: 3, style: 'dotted' });
paint(myCrossunderMarks, { name: 'Crossunder', color: '#ff5d00', thickness: 3, style: 'dotted' });

// Senkou spans displaced forward by (offset - 1)
const mySenkouAShifted = shift(mySenkouA, myOffset - 1);
const mySenkouBShifted = shift(mySenkouB, myOffset - 1);

const mySenkouAColor = for_every(mySenkouAShifted, mySenkouBShifted, (_a, _b) => (_a !== null && _b !== null && _a > _b) ? '#009688' : '#f44336');

fill(
	paint(mySenkouAShifted, { name: 'Senkou Span A', color: 'teal', thickness: 1 }),
	paint(mySenkouBShifted, { name: 'Senkou Span B', color: 'red', thickness: 1 }),
	'teal',
	0.2
);

// Chikou span, shifted backward by (offset - 1)
const myChikou = shift(close, -(myOffset - 1));
paint(myChikou, { name: 'Chikou', color: '#7b1fa2', thickness: 1 });
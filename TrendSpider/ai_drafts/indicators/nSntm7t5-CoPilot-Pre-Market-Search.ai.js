describe_indicator('Volume Weighted Average Price', 'price');

// NOTE: Pine's "Earnings", "Dividends" and "Splits" anchor modes rely on
// request.earnings/dividends/splits lookahead merge semantics that are not
// reproducible 1:1 in this engine. These three anchors fall back to
// "Session" behavior here (see warning below).
const myAnchor = input.select('Anchor Period', 'Session', ['Session', 'Week', 'Month', 'Quarter', 'Year', 'Decade', 'Century', 'Earnings', 'Dividends', 'Splits']);
const myHideOnDWM = input.boolean('Hide VWAP on 1D or Above', false);
const myOffset = input.number('offset', 0, { min: -500, max: 500 });

const myCalcMode = input.select('Bands Calculation Mode', 'Standard Deviation', ['Standard Deviation', 'Percentage']);

const myBandRow1 = input.row();
const myShowBand1 = myBandRow1.boolean('Show Band 1', true);
const myBandMult1 = myBandRow1.number('Bands Multiplier 1', 1.0, { min: 0, max: 50, step: 0.5 });

const myBandRow2 = input.row();
const myShowBand2 = myBandRow2.boolean('Show Band 2', false);
const myBandMult2 = myBandRow2.number('Bands Multiplier 2', 2.0, { min: 0, max: 50, step: 0.5 });

const myBandRow3 = input.row();
const myShowBand3 = myBandRow3.boolean('Show Band 3', false);
const myBandMult3 = myBandRow3.number('Bands Multiplier 3', 3.0, { min: 0, max: 50, step: 0.5 });

// Pine's src input defaults to hlc3 and is hidden from UI (display.none).
const mySrc = hlc3;

// Determine if the current time frame is Daily/Weekly/Monthly or above,
// used only for the "hide on 1D or above" toggle.
const myIsDWMTimeframe = isNaN(current.resolution);

// Figure out "new period" boundaries, based on the anchor selection.
const myNewPeriodFlags = series_of(false);

for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myInfo = time_of(time[myIndex]);
	let myIsNew = false;

	if (myIndex === 0) {
		myIsNew = true;
	}
	else {
		const myPrevInfo = time_of(time[myIndex - 1]);

		if (myAnchor === 'Session') {
			myIsNew = myInfo.dayOfYear !== myPrevInfo.dayOfYear || myInfo.year !== myPrevInfo.year;
		}
		else if (myAnchor === 'Week') {
			myIsNew = myInfo.weekOfYear !== myPrevInfo.weekOfYear || myInfo.year !== myPrevInfo.year;
		}
		else if (myAnchor === 'Month') {
			myIsNew = myInfo.month !== myPrevInfo.month || myInfo.year !== myPrevInfo.year;
		}
		else if (myAnchor === 'Quarter') {
			myIsNew = myInfo.quarter !== myPrevInfo.quarter || myInfo.year !== myPrevInfo.year;
		}
		else if (myAnchor === 'Year') {
			myIsNew = myInfo.year !== myPrevInfo.year;
		}
		else if (myAnchor === 'Decade') {
			myIsNew = myInfo.year !== myPrevInfo.year && (myInfo.year % 10 === 0);
		}
		else if (myAnchor === 'Century') {
			myIsNew = myInfo.year !== myPrevInfo.year && (myInfo.year % 100 === 0);
		}
		else {
			// Earnings / Dividends / Splits fallback: use Session anchoring.
			myIsNew = myInfo.dayOfYear !== myPrevInfo.dayOfYear || myInfo.year !== myPrevInfo.year;
		}
	}

	myNewPeriodFlags[myIndex] = myIsNew;
}

// Compute cumulative (price*volume), (price^2*volume) and volume sums,
// resetting at every new period, to build an anchored VWAP with a
// volume-weighted standard deviation band (matches ta.vwap stdevUpper logic).
const myVwapValue = series_of(null);
const myUpperBand1 = series_of(null);
const myLowerBand1 = series_of(null);
const myUpperBand2 = series_of(null);
const myLowerBand2 = series_of(null);
const myUpperBand3 = series_of(null);
const myLowerBand3 = series_of(null);

let myCumPV = 0;
let myCumPV2 = 0;
let myCumV = 0;

const myHideThisCandle = myHideOnDWM && myIsDWMTimeframe;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myNewPeriodFlags[myIndex]) {
		myCumPV = 0;
		myCumPV2 = 0;
		myCumV = 0;
	}

	const myPrice = mySrc[myIndex];
	const myVol = volume[myIndex] || 0;

	myCumPV += myPrice * myVol;
	myCumPV2 += myPrice * myPrice * myVol;
	myCumV += myVol;

	if (myHideThisCandle || myCumV === 0) {
		continue;
	}

	const myVwap = myCumPV / myCumV;
	const myVariance = (myCumPV2 / myCumV) - (myVwap * myVwap);
	const myStdevAbs = Math.sqrt(Math.max(myVariance, 0));

	const myBandBasis = myCalcMode === 'Standard Deviation' ? myStdevAbs : myVwap * 0.01;

	myVwapValue[myIndex] = myVwap;
	myUpperBand1[myIndex] = myVwap + myBandBasis * myBandMult1;
	myLowerBand1[myIndex] = myVwap - myBandBasis * myBandMult1;
	myUpperBand2[myIndex] = myVwap + myBandBasis * myBandMult2;
	myLowerBand2[myIndex] = myVwap - myBandBasis * myBandMult2;
	myUpperBand3[myIndex] = myVwap + myBandBasis * myBandMult3;
	myLowerBand3[myIndex] = myVwap - myBandBasis * myBandMult3;
}

const myVwapPainted = paint(myVwapValue, { name: 'VWAP', color: '#2962FF', thickness: 2 });

const myUpper1Painted = paint(myShowBand1 ? myUpperBand1 : series_of(null), { name: 'Upper Band 1', color: 'green' });
const myLower1Painted = paint(myShowBand1 ? myLowerBand1 : series_of(null), { name: 'Lower Band 1', color: 'green' });
fill(myUpper1Painted, myLower1Painted, 'green', 0.05, 'Bands Fill 1');

const myUpper2Painted = paint(myShowBand2 ? myUpperBand2 : series_of(null), { name: 'Upper Band 2', color: 'olive' });
const myLower2Painted = paint(myShowBand2 ? myLowerBand2 : series_of(null), { name: 'Lower Band 2', color: 'olive' });
fill(myUpper2Painted, myLower2Painted, 'olive', 0.05, 'Bands Fill 2');

const myUpper3Painted = paint(myShowBand3 ? myUpperBand3 : series_of(null), { name: 'Upper Band 3', color: 'teal' });
const myLower3Painted = paint(myShowBand3 ? myLowerBand3 : series_of(null), { name: 'Lower Band 3', color: 'teal' });
fill(myUpper3Painted, myLower3Painted, 'teal', 0.05, 'Bands Fill 3');

// Scanner/alert/strategy friendly signals.
const myCloseAboveVwap = for_every(close, myVwapValue, (_c, _v) => _v !== null && _c > _v);
const myCloseBelowVwap = for_every(close, myVwapValue, (_c, _v) => _v !== null && _c < _v);
const myCrossAboveVwap = for_every(close, myVwapValue, (_c, _v, _prev, _i) => {
	if (_v === null || _i === 0 || myVwapValue[_i - 1] === null) return false;
	return close[_i - 1] <= myVwapValue[_i - 1] && _c > _v;
});
const myCrossBelowVwap = for_every(close, myVwapValue, (_c, _v, _prev, _i) => {
	if (_v === null || _i === 0 || myVwapValue[_i - 1] === null) return false;
	return close[_i - 1] >= myVwapValue[_i - 1] && _c < _v;
});

register_signal(myCloseAboveVwap, 'Close Above VWAP');
register_signal(myCloseBelowVwap, 'Close Below VWAP');
register_signal(myCrossAboveVwap, 'Cross Above VWAP');
register_signal(myCrossBelowVwap, 'Cross Below VWAP');
describe_indicator('Kloom VWAP Bands', 'price');

// This indicator reproduces the Pine Script "Kloom VWAP Bands" logic:
// a VWAP that resets at the start of every Session/Week/Month, with
// standard deviation bands built from the same cumulative sums as Pine.

const myAnchorTab = input.tab('VWAP');
const myAnchor = myAnchorTab.select('Anchor period', 'Session', ['Session', 'Week', 'Month']);
const myPriceSource = myAnchorTab.select('Price source', 'hlc3', constants.price_source_options);

const myBandsRow1 = myAnchorTab.row();
const myShowBand1 = myBandsRow1.boolean('Show band 1', true);
const myMult1 = myBandsRow1.number('Band 1 multiplier', 1.0, { min: 0.1, max: 5, step: 0.25 });

const myBandsRow2 = myAnchorTab.row();
const myShowBand2 = myBandsRow2.boolean('Show band 2', true);
const myMult2 = myBandsRow2.number('Band 2 multiplier', 2.0, { min: 0.1, max: 5, step: 0.25 });

const mySrc = market[myPriceSource];
const myVol = volume;

// Detect a "new period" boundary, equivalent to Pine's timeframe.change()
const myPeriodKeys = time.map(_t => {
	const myInfo = time_of(_t);
	if (myAnchor === 'Session') {
		return `${myInfo.year}-${myInfo.dayOfYear}`;
	}
	else if (myAnchor === 'Week') {
		return `${myInfo.year}-${myInfo.weekOfYear}`;
	}
	else {
		return `${myInfo.year}-${myInfo.month}`;
	}
});

const myVwap = series_of(null);
const myStdev = series_of(null);
const myUp1 = series_of(null);
const myDn1 = series_of(null);
const myUp2 = series_of(null);
const myDn2 = series_of(null);

let mySumPV = 0;
let mySumV = 0;
let mySumPV2 = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myNewPeriod = myIndex === 0 || myPeriodKeys[myIndex] !== myPeriodKeys[myIndex - 1];

	if (myNewPeriod) {
		mySumPV = 0;
		mySumV = 0;
		mySumPV2 = 0;
	}

	const myPrice = mySrc[myIndex];
	const myVolumeValue = myVol[myIndex] || 0;

	mySumPV += myPrice * myVolumeValue;
	mySumV += myVolumeValue;
	mySumPV2 += myPrice * myPrice * myVolumeValue;

	if (mySumV > 0) {
		const myVwapValue = mySumPV / mySumV;
		const myVarianceValue = Math.max(mySumPV2 / mySumV - myVwapValue * myVwapValue, 0);
		const myStdevValue = Math.sqrt(myVarianceValue);

		myVwap[myIndex] = myVwapValue;
		myStdev[myIndex] = myStdevValue;
		myUp1[myIndex] = myShowBand1 ? myVwapValue + myStdevValue * myMult1 : null;
		myDn1[myIndex] = myShowBand1 ? myVwapValue - myStdevValue * myMult1 : null;
		myUp2[myIndex] = myShowBand2 ? myVwapValue + myStdevValue * myMult2 : null;
		myDn2[myIndex] = myShowBand2 ? myVwapValue - myStdevValue * myMult2 : null;
	}
	else {
		myVwap[myIndex] = null;
		myStdev[myIndex] = null;
		myUp1[myIndex] = null;
		myDn1[myIndex] = null;
		myUp2[myIndex] = null;
		myDn2[myIndex] = null;
	}
}

paint(myVwap, { name: 'VWAP', color: '#00BCD4', thickness: 2 });

const myUpper1Painted = paint(myUp1, { name: 'Upper1', color: 'teal', thickness: 1 });
const myLower1Painted = paint(myDn1, { name: 'Lower1', color: 'teal', thickness: 1 });
fill(myUpper1Painted, myLower1Painted, 'teal', 0.08);

const myUpper2Painted = paint(myUp2, { name: 'Upper2', color: 'orange', thickness: 1 });
const myLower2Painted = paint(myDn2, { name: 'Lower2', color: 'orange', thickness: 1 });
fill(myUpper2Painted, myLower2Painted, 'orange', 0.05);

// Deviation (in standard deviations) of close from VWAP, for scanning/alerts
const myDeviation = for_every(close, myVwap, myStdev, (_close, _vwap, _stdev) => {
	if (_stdev === null || _stdev === 0 || _vwap === null) {
		return null;
	}
	return (_close - _vwap) / _stdev;
});

// Signals for scanners/alerts/strategies
const myAboveUpperBand1 = for_every(close, myUp1, (_close, _up1) => _up1 !== null && _close > _up1);
const myBelowLowerBand1 = for_every(close, myDn1, (_close, _dn1) => _dn1 !== null && _close < _dn1);
const myAboveUpperBand2 = for_every(close, myUp2, (_close, _up2) => _up2 !== null && _close > _up2);
const myBelowLowerBand2 = for_every(close, myDn2, (_close, _dn2) => _dn2 !== null && _close < _dn2);
const myCrossAboveVwap = for_every(close, myVwap, (_close, _vwap, _prev, _index) => {
	if (_index === 0 || _vwap === null || myVwap[_index - 1] === null) return false;
	return close[_index - 1] <= myVwap[_index - 1] && _close > _vwap;
});
const myCrossBelowVwap = for_every(close, myVwap, (_close, _vwap, _prev, _index) => {
	if (_index === 0 || _vwap === null || myVwap[_index - 1] === null) return false;
	return close[_index - 1] >= myVwap[_index - 1] && _close < _vwap;
});

register_signal(myAboveUpperBand1, 'Close Above Band 1');
register_signal(myBelowLowerBand1, 'Close Below Band 1');
register_signal(myAboveUpperBand2, 'Close Above Band 2');
register_signal(myBelowLowerBand2, 'Close Below Band 2');
register_signal(myCrossAboveVwap, 'Cross Above VWAP');
register_signal(myCrossBelowVwap, 'Cross Below VWAP');
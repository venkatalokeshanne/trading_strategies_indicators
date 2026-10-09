describe_indicator('VASA VWAP Plus Institutional Levels', 'price');

// ---------- Inputs ----------
const anchorTab = input.tab('Anchor and Source');
const myAnchor = anchorTab.select('Anchor period', 'Session', ['Session', 'Week', 'Month']);
const mySource = anchorTab.select('Source', 'hlc3', constants.price_source_options);

const bandsTab = input.tab('Bands');
const myShow1 = bandsTab.boolean('Show 1 Sigma band', true);
const myShow2 = bandsTab.boolean('Show 2 Sigma band', true);
const bandsRow = bandsTab.row();
const myMult1 = bandsRow.number('1 Sigma multiplier', 1.0, { min: 0.1, max: 10, step: 0.1 });
const myMult2 = bandsRow.number('2 Sigma multiplier', 2.0, { min: 0.1, max: 10, step: 0.1 });

const myFillOn = input.boolean('Shade bands', true);

// ---------- Source series ----------
const myPrice = market[mySource];

// ---------- Resolution used for new-period detection ----------
const myAnchorResolution = myAnchor === 'Session' ? 'D' : (myAnchor === 'Week' ? 'W' : 'M');

// ---------- Cumulative VWAP + variance (non-repainting) ----------
// We detect a "new period" whenever the anchor session id (as per bar_at())
// changes compared to the previous candle. This mirrors Pine's
// timeframe.change(tfAnchor) behavior.
const myVwap = series_of(null);
const myDev = series_of(null);

let mySumPV = 0;
let mySumV = 0;
let mySumPV2 = 0;
let myPrevSessionId = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const mySessionId = bar_at(time[myIndex], myAnchorResolution).session;
	const myIsNew = (myPrevSessionId === null) || (mySessionId !== myPrevSessionId);

	const myPV = myPrice[myIndex] * volume[myIndex];
	const myV = volume[myIndex];
	const myPV2 = myPrice[myIndex] * myPrice[myIndex] * volume[myIndex];

	if (myIsNew) {
		mySumPV = myPV;
		mySumV = myV;
		mySumPV2 = myPV2;
	}
	else {
		mySumPV += myPV;
		mySumV += myV;
		mySumPV2 += myPV2;
	}

	if (mySumV === 0) {
		myVwap[myIndex] = null;
		myDev[myIndex] = null;
	}
	else {
		const myVwapValue = mySumPV / mySumV;
		const myVariance = Math.max((mySumPV2 / mySumV) - (myVwapValue * myVwapValue), 0);
		myVwap[myIndex] = myVwapValue;
		myDev[myIndex] = Math.sqrt(myVariance);
	}

	myPrevSessionId = mySessionId;
}

// ---------- Bands ----------
const myUpper1 = myShow1 ? add(myVwap, mult(myDev, myMult1)) : constants.empty_series;
const myLower1 = myShow1 ? sub(myVwap, mult(myDev, myMult1)) : constants.empty_series;
const myUpper2 = myShow2 ? add(myVwap, mult(myDev, myMult2)) : constants.empty_series;
const myLower2 = myShow2 ? sub(myVwap, mult(myDev, myMult2)) : constants.empty_series;

// ---------- Plots ----------
const myVwapPainted = paint(myVwap, { name: 'VWAP', color: '#2563eb', thickness: 2 });
const myUpper1Painted = paint(myUpper1, { name: 'Upper1Sigma', color: '#3b82f6' });
const myLower1Painted = paint(myLower1, { name: 'Lower1Sigma', color: '#3b82f6' });
const myUpper2Painted = paint(myUpper2, { name: 'Upper2Sigma', color: '#93c5fd' });
const myLower2Painted = paint(myLower2, { name: 'Lower2Sigma', color: '#93c5fd' });

if (myFillOn) {
	fill(myUpper1Painted, myLower1Painted, '#3b82f6', 0.1);
	fill(myUpper2Painted, myUpper1Painted, '#3b82f6', 0.06);
	fill(myLower1Painted, myLower2Painted, '#3b82f6', 0.06);
}

// ---------- Signals (confirmed cross on bar close) ----------
const myCrossUp = for_every(close, myVwap, (_close, _vwap, _prev, _index) => {
	if (_index === 0 || _vwap === null || myVwap[_index - 1] === null) return false;
	return _close > _vwap && close[_index - 1] <= myVwap[_index - 1];
});

const myCrossDn = for_every(close, myVwap, (_close, _vwap, _prev, _index) => {
	if (_index === 0 || _vwap === null || myVwap[_index - 1] === null) return false;
	return _close < _vwap && close[_index - 1] >= myVwap[_index - 1];
});

register_signal(myCrossUp, 'Price crossed above VWAP');
register_signal(myCrossDn, 'Price crossed below VWAP');
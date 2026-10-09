describe_indicator('Crypto Algo SuperTrend MTF', 'price');

// ========================== INPUTS ==========================
const myStTab = input.tab('SuperTrend');
const myStRow1 = myStTab.row();
const myStLen = myStRow1.number('ATR Length', 10, { min: 1, max: 100 });
const myStMult = myStRow1.number('Multiplier', 3.0, { min: 0.1, max: 20, step: 0.1 });

const myBbTab = input.tab('Bollinger Chop Filter');
const myBbRow = myBbTab.row();
const myBbLen = myBbRow.number('BB Length', 20, { min: 2, max: 300 });
const myBbMult = myBbRow.number('BB StdDev', 2.0, { min: 0.1, max: 10, step: 0.1 });
const myBbwMaLen = myBbTab.number('BBW Base MA Length', 20, { min: 1, max: 300 });

// ========================== SUPERTREND MATH ==========================
// Plain JS implementation of the SuperTrend algorithm (recursive bands),
// since the built-in supertrend() function only works on the main chart's
// OHLC and cannot be applied to data fetched from other timeframes.
// NOTE: "new Array(...)" is prohibited by the scripting engine, so we use
// "Array(...).fill(...)" instead, which produces the same result without
// using the "new" keyword.
function myComputeSupertrendDir(_myHigh, _myLow, _myClose, _myAtr, _myMult) {
	const myLength = _myClose.length;
	const myDir = Array(myLength).fill(1);
	const myFinalUpper = Array(myLength).fill(null);
	const myFinalLower = Array(myLength).fill(null);

	for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
		const myMid = (_myHigh[myIndex] + _myLow[myIndex]) / 2;
		const myBasicUpper = myMid + _myMult * (_myAtr[myIndex] || 0);
		const myBasicLower = myMid - _myMult * (_myAtr[myIndex] || 0);

		if (myIndex === 0) {
			myFinalUpper[myIndex] = myBasicUpper;
			myFinalLower[myIndex] = myBasicLower;
			myDir[myIndex] = _myClose[myIndex] <= myBasicUpper ? 1 : -1;
			continue;
		}

		myFinalUpper[myIndex] = (_myClose[myIndex - 1] <= myFinalUpper[myIndex - 1])
			? Math.min(myBasicUpper, myFinalUpper[myIndex - 1])
			: myBasicUpper;

		myFinalLower[myIndex] = (_myClose[myIndex - 1] >= myFinalLower[myIndex - 1])
			? Math.max(myBasicLower, myFinalLower[myIndex - 1])
			: myBasicLower;

		if (myDir[myIndex - 1] === 1) {
			myDir[myIndex] = _myClose[myIndex] > myFinalUpper[myIndex] ? -1 : 1;
		}
		else {
			myDir[myIndex] = _myClose[myIndex] < myFinalLower[myIndex] ? 1 : -1;
		}
	}

	return myDir;
}

// ========================== CURRENT TIMEFRAME SUPERTREND ==========================
const myCurrentAtr = atr(high, low, close, myStLen);
const myStDir = myComputeSupertrendDir(high, low, close, myCurrentAtr, myStMult);

// ========================== MTF SUPERTREND (5m / 15m / 1h / 4h) ==========================
const [myData5m, myData15m, myData1h, myData4h] = await Promise.all([
	request.history(current.ticker, '5'),
	request.history(current.ticker, '15'),
	request.history(current.ticker, '60'),
	request.history(current.ticker, '240')
]);

assert(!myData5m.error, `Error fetching 5m data: "${myData5m.error}"`);
assert(!myData15m.error, `Error fetching 15m data: "${myData15m.error}"`);
assert(!myData1h.error, `Error fetching 1h data: "${myData1h.error}"`);
assert(!myData4h.error, `Error fetching 4h data: "${myData4h.error}"`);

function myLastMtfTrendIsBull(_myData) {
	const myAtrSeries = atr(_myData.high, _myData.low, _myData.close, myStLen);
	const myDirSeries = myComputeSupertrendDir(_myData.high, _myData.low, _myData.close, myAtrSeries, myStMult);
	return myDirSeries[myDirSeries.length - 1] === -1;
}

const myBull5m = myLastMtfTrendIsBull(myData5m);
const myBull15m = myLastMtfTrendIsBull(myData15m);
const myBull1h = myLastMtfTrendIsBull(myData1h);
const myBull4h = myLastMtfTrendIsBull(myData4h);

// ========================== BOLLINGER BAND WIDTH CHOP FILTER ==========================
const myBasis = sma(close, myBbLen);
const myBand = compute_band(myBasis, 'St.Dev.', myBbMult, myBbLen);
const myBbw = div(sub(myBand.upper, myBand.lower), myBasis);
const myBbwMa = sma(myBbw, myBbwMaLen);
const myIsTrending = for_every(myBbw, myBbwMa, (_myBbw, _myBbwMa) => _myBbw > _myBbwMa);

// ========================== SIGNAL LOGIC ==========================
const myStDirSeries = myStDir;
const myStDirChanged = for_every(myStDirSeries, (_myDir, _myPrev, _myIndex) => _myIndex > 0 && _myDir !== myStDirSeries[_myIndex - 1]);

const myBuyEntry = for_every(myIsTrending, myStDirChanged, series_of(0).map((_myV, _myIndex) => myStDirSeries[_myIndex]),
	(_myTrending, _myChanged, _myDir) => _myTrending && _myChanged && _myDir === -1);

const myShortEntry = for_every(myIsTrending, myStDirChanged, series_of(0).map((_myV, _myIndex) => myStDirSeries[_myIndex]),
	(_myTrending, _myChanged, _myDir) => _myTrending && _myChanged && _myDir === 1);

const myExitLong = for_every(myStDirChanged, series_of(0).map((_myV, _myIndex) => myStDirSeries[_myIndex]),
	(_myChanged, _myDir) => _myChanged && _myDir === 1);

const myExitShort = for_every(myStDirChanged, series_of(0).map((_myV, _myIndex) => myStDirSeries[_myIndex]),
	(_myChanged, _myDir) => _myChanged && _myDir === -1);

register_signal(myBuyEntry, 'Buy Entry');
register_signal(myShortEntry, 'Short Entry');
register_signal(myExitLong, 'Exit Long');
register_signal(myExitShort, 'Exit Short');

// ========================== VISUALS ==========================
const myStLineColor = for_every(series_of(0).map((_myV, _myIndex) => myStDirSeries[_myIndex]), _myDir => _myDir === -1 ? '#26A69A' : '#EF5350');
paint(close, { name: 'SuperTrend Direction Marker', color: myStLineColor, style: 'dotted', thickness: 2 });

// ========================== MTF DASHBOARD TABLE ==========================
function myCellColor(_myBull) {
	return _myBull ? '#26A69A' : '#EF5350';
}

paint_overlay('CryptoAlgoDashboard', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'TF', color: 'white', background_color: '#808080' }, { text: 'Trend', color: 'white', background_color: '#808080' }] },
		{ cells: [{ text: '5M', color: 'white' }, { text: myBull5m ? 'BULL' : 'BEAR', color: 'white', background_color: myCellColor(myBull5m) }] },
		{ cells: [{ text: '15M', color: 'white' }, { text: myBull15m ? 'BULL' : 'BEAR', color: 'white', background_color: myCellColor(myBull15m) }] },
		{ cells: [{ text: '1H', color: 'white' }, { text: myBull1h ? 'BULL' : 'BEAR', color: 'white', background_color: myCellColor(myBull1h) }] },
		{ cells: [{ text: '4H', color: 'white' }, { text: myBull4h ? 'BULL' : 'BEAR', color: 'white', background_color: myCellColor(myBull4h) }] },
		{ cells: [{ text: 'State', color: 'white', background_color: '#2962FF' }, { text: myIsTrending[myIsTrending.length - 1] ? 'TRENDING' : 'WAITING', color: 'white', background_color: myIsTrending[myIsTrending.length - 1] ? '#26A69A' : '#FF9800' }] }
	]
});
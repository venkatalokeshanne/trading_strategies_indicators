describe_indicator('CM Laguerre PPO PercentileRank Mkt Tops and Bottoms', 'lower', { decimals: 1 });

// --- Inputs ---
const myPctile = input.number('Percentile Threshold Extreme', 90, { min: 1, max: 100 });
const myWrnPctile = input.number('Percentile Threshold Warning', 70, { min: 1, max: 100 });
const myShortG = input.number('PPO Setting Short', 0.4, { min: 0, max: 1 });
const myLongG = input.number('PPO Setting Long', 0.8, { min: 0, max: 1 });
const myLkbT = input.number('Look Back Period Tops', 200, { min: 1, max: 2000 });
const myLkbB = input.number('Look Back Period Bottoms', 200, { min: 1, max: 2000 });
const myShowLine = input.boolean('Show Threshold Line', true);
const myShowWarnLine = input.boolean('Show Warning Threshold Line', true);

const myN = close.length;

// --- Laguerre filter (recursive state machine, must be computed in a loop since it depends on previous state) ---
function myLaguerre(myGamma) {
	const myL0 = series_of(null);
	const myL1 = series_of(null);
	const myL2 = series_of(null);
	const myL3 = series_of(null);
	const myResult = series_of(null);

	for (let myIndex = 0; myIndex < myN; myIndex += 1) {
		const myPrice = hl2[myIndex];
		const myPrevL0 = myIndex > 0 && myL0[myIndex - 1] !== null ? myL0[myIndex - 1] : 0;
		const myPrevL1 = myIndex > 0 && myL1[myIndex - 1] !== null ? myL1[myIndex - 1] : 0;
		const myPrevL2 = myIndex > 0 && myL2[myIndex - 1] !== null ? myL2[myIndex - 1] : 0;
		const myPrevL3 = myIndex > 0 && myL3[myIndex - 1] !== null ? myL3[myIndex - 1] : 0;

		const myCurL0 = (1 - myGamma) * myPrice + myGamma * myPrevL0;
		const myCurL1 = -myGamma * myCurL0 + myPrevL0 + myGamma * myPrevL1;
		const myCurL2 = -myGamma * myCurL1 + myPrevL1 + myGamma * myPrevL2;
		const myCurL3 = -myGamma * myCurL2 + myPrevL2 + myGamma * myPrevL3;

		myL0[myIndex] = myCurL0;
		myL1[myIndex] = myCurL1;
		myL2[myIndex] = myCurL2;
		myL3[myIndex] = myCurL3;

		myResult[myIndex] = (myCurL0 + 2 * myCurL1 + 2 * myCurL2 + myCurL3) / 6;
	}

	return myResult;
}

const myLmas = myLaguerre(myShortG);
const myLmal = myLaguerre(myLongG);

const myPctileB = myPctile * -1;
const myWrnPctileB = myWrnPctile * -1;

// --- PPO calculations ---
const myPpoT = series_of(null);
const myPpoB = series_of(null);

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	myPpoT[myIndex] = (myLmas[myIndex] - myLmal[myIndex]) / myLmal[myIndex] * 100;
	myPpoB[myIndex] = (myLmal[myIndex] - myLmas[myIndex]) / myLmal[myIndex] * 100;
}

// --- PercentRank (TradingView ta.percentrank: % of last "length" bars, incl current, strictly less than current) ---
function myPercentRank(mySeries, myLength) {
	const myOut = series_of(null);

	for (let myIndex = 0; myIndex < myN; myIndex += 1) {
		if (myIndex < myLength) {
			myOut[myIndex] = null;
			continue;
		}
		const myCurrent = mySeries[myIndex];
		let myCount = 0;
		for (let myBack = 0; myBack <= myLength; myBack += 1) {
			if (mySeries[myIndex - myBack] < myCurrent) {
				myCount += 1;
			}
		}
		myOut[myIndex] = (myCount / myLength) * 100;
	}

	return myOut;
}

const myPctRankTRaw = myPercentRank(myPpoT, myLkbT);
const myPctRankBRaw = myPercentRank(myPpoB, myLkbB);

const myPctRankT = myPctRankTRaw;
const myPctRankB = for_every(myPctRankBRaw, _b => _b === null ? null : _b * -1);

// --- Dynamic colors ---
const myColT = for_every(myPctRankT, _r => {
	if (_r === null) return 'gray';
	if (_r >= myPctile) return 'red';
	if (_r >= myWrnPctile) return 'orange';
	return 'gray';
});

const myColB = for_every(myPctRankB, _r => {
	if (_r === null) return 'silver';
	if (_r <= myPctileB) return 'lime';
	if (_r <= myWrnPctileB) return 'green';
	return 'silver';
});

// --- Threshold lines ---
const myTopExtremeLine = (myShowLine && myPctile > 0) ? horizontal_line(myPctile) : series_of(null);
const myTopWarnLine = (myShowWarnLine && myWrnPctile > 0) ? horizontal_line(myWrnPctile) : series_of(null);
const myBottomExtremeLine = (myShowLine && myPctileB < 0) ? horizontal_line(myPctileB) : series_of(null);
const myBottomWarnLine = (myShowWarnLine && myWrnPctileB < 0) ? horizontal_line(myWrnPctileB) : series_of(null);

// --- Painting ---
paint(myPctRankT, { name: 'Percentile Rank Tops', color: myColT, style: 'column', thickness: 2 });
paint(myTopExtremeLine, { name: 'Extreme Threshold Tops', color: 'red', style: 'line', thickness: 2 });
paint(myTopWarnLine, { name: 'Warning Threshold Tops', color: 'orange', style: 'line', thickness: 2 });

paint(myPctRankB, { name: 'Percentile Rank Bottoms', color: myColB, style: 'column', thickness: 2 });
paint(myBottomExtremeLine, { name: 'Extreme Threshold Bottoms', color: 'lime', style: 'line', thickness: 2 });
paint(myBottomWarnLine, { name: 'Warning Threshold Bottoms', color: 'green', style: 'line', thickness: 2 });

paint(horizontal_line(0), { name: 'Zero Line', color: 'gray', style: 'line', thickness: 1 });

// --- Signals for scanners, alerts and strategies ---
const myTopExtremeSignal = for_every(myPctRankT, _r => _r !== null && _r >= myPctile);
const myTopWarningSignal = for_every(myPctRankT, _r => _r !== null && _r >= myWrnPctile && _r < myPctile);
const myBottomExtremeSignal = for_every(myPctRankB, _r => _r !== null && _r <= myPctileB);
const myBottomWarningSignal = for_every(myPctRankB, _r => _r !== null && _r <= myWrnPctileB && _r > myPctileB);

register_signal(myTopExtremeSignal, 'Top Extreme Signal');
register_signal(myTopWarningSignal, 'Top Warning Signal');
register_signal(myBottomExtremeSignal, 'Bottom Extreme Signal');
register_signal(myBottomWarningSignal, 'Bottom Warning Signal');
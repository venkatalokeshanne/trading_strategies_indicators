describe_indicator('OmniTrend ATR Scalper', 'price');

// --- Settings ---
const myTradeDir = input.select('Trades', 'Both', ['Both', 'Long Only', 'Short Only']);
const myLenFast = input.number('Fast Step Period', 5, { min: 1, max: 500 });
const myLenSlow = input.number('Slow Step Period', 10, { min: 1, max: 500 });
const myLenAtr = input.number('ATR Period', 200, { min: 1, max: 1000 });
const myMultStep = input.number('Step Multiplier', 1.0, { min: -100, max: 100 });
const myMultRev = input.number('Reverse Multiplier', 2.0, { min: -100, max: 100 });
const mySlMult = input.number('Stop Loss Multiplier', 2.0, { min: -100, max: 100 });
const myTpMult = input.number('Take Profit Multiplier', 3.0, { min: -100, max: 100 });

// ATR computed once, outside of the loop (never call indicator functions in loops)
const myAtr = atr(high, low, close, myLenAtr);

const myN = close.length;

// Output series
const myTLine = series_of(null);
const myDir = series_of(null);
const mySigLong = series_of(false);
const mySigShort = series_of(false);
const mySl = series_of(null);
const myTp = series_of(null);

// Engine state (mirrors Pine's "var" persistent variables)
let myTLineVal = close[0];
let myDirVal = 1;
let myStepVal = 0.0;
let myIsFast = false;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myAtrVal = myAtr[myIndex];

	let mySigL = false;
	let mySigS = false;

	if (myAtrVal !== null && myAtrVal !== undefined && !isNaN(myAtrVal)) {
		const myD = close[myIndex] - myTLineVal;

		mySigL = (myDirVal === -1) && (myD > myMultRev * myAtrVal);
		mySigS = (myDirVal === 1) && (-myD > myMultRev * myAtrVal);

		if (mySigL) {
			myDirVal = 1;
		}
		else if (mySigS) {
			myDirVal = -1;
		}

		const mySChk = Math.abs(myD) > myMultStep * myAtrVal;

		if (mySigL || mySigS || (mySChk !== myIsFast) || myStepVal === 0.0) {
			myIsFast = mySChk;
			myStepVal = myIsFast ? (myAtrVal / myLenFast) : (myAtrVal / myLenSlow);
		}

		myTLineVal = myTLineVal + (myDirVal * myStepVal);
	}

	myTLine[myIndex] = myTLineVal;
	myDir[myIndex] = myDirVal;
	mySigLong[myIndex] = mySigL;
	mySigShort[myIndex] = mySigS;

	if (mySigL) {
		mySl[myIndex] = close[myIndex] - (myAtrVal * mySlMult);
		myTp[myIndex] = close[myIndex] + (myAtrVal * myTpMult);
	}
	else if (mySigS) {
		mySl[myIndex] = close[myIndex] + (myAtrVal * mySlMult);
		myTp[myIndex] = close[myIndex] - (myAtrVal * myTpMult);
	}
	else {
		mySl[myIndex] = myIndex > 0 ? mySl[myIndex - 1] : null;
		myTp[myIndex] = myIndex > 0 ? myTp[myIndex - 1] : null;
	}
}

// Trend line colored by direction (cyan for up, magenta for down)
const myLineColor = for_every(myDir, _d => _d === 1 ? '#00f2ff' : '#ff00ff');
paint(myTLine, { name: 'Trend', color: myLineColor, thickness: 3 });

// Entry signals filtered by the trade direction setting, for visual markers
const myLongAllowed = (myTradeDir === 'Both' || myTradeDir === 'Long Only');
const myShortAllowed = (myTradeDir === 'Both' || myTradeDir === 'Short Only');

const myLongMarks = for_every(mySigLong, _s => _s ? true : null);
const mySgLongMarks = myLongAllowed ? myLongMarks : series_of(null);
const myShortMarks = for_every(mySigShort, _s => _s ? true : null);
const mySgShortMarks = myShortAllowed ? myShortMarks : series_of(null);

paint(for_every(mySgLongMarks, _v => _v ? low : null), { name: 'LongMarker', style: 'labels_below', color: '#00f2ff' });
paint(for_every(mySgShortMarks, _v => _v ? high : null), { name: 'ShortMarker', style: 'labels_above', color: '#ff00ff' });

// Scanner/alert/strategy signals
register_signal(mySigLong, 'Long Signal (Raw)');
register_signal(mySigShort, 'Short Signal (Raw)');
register_signal(for_every(mySigLong, _s => myLongAllowed && _s), 'Long Entry');
register_signal(for_every(mySigShort, _s => myShortAllowed && _s), 'Short Entry');
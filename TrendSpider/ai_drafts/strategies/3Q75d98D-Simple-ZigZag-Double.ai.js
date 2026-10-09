describe_indicator('Simple ZigZag Double', 'price');

// ── NOTE ──────────────────────────────────────────────────────────
// This is a best-effort translation of the supplied Pine Script
// strategy. Pine's strategy.* engine (position sizing, pyramiding,
// equity-based lot sizing, strategy.cancel/exit orders) has no
// equivalent in TrendSpider Custom JS. Only the core ZigZag /
// LEVEL_LONG / LEVEL_SHORT math and the entry/exit boolean logic
// (and the "strict position" virtual position filter) are
// reproduced. Lot sizing, equity, commissions and order management
// are not applicable here and are omitted.
// ─────────────────────────────────────────────────────────────────

const myTab = input.tab('General');
const myRow1 = myTab.row();
const myNeedLong = myRow1.boolean('Use Long', true);
const myNeedShort = myRow1.boolean('Use Short', true);

const myZzGroup = myTab.group('Long ZigZag');
const myZzRow = myZzGroup.row();
const myLength = myZzRow.number('Long Length', 5, { min: 2, max: 500 });
const myDetection = myZzRow.number('Detection', 3, { min: 1, max: 500 });

const myZz2Group = myTab.group('Short ZigZag');
const myZz2Row = myZz2Group.row();
const myLength2 = myZz2Row.number('Short Length', 5, { min: 2, max: 500 });
const myDetection2 = myZz2Row.number('Detection', 3, { min: 1, max: 500 });

const myTimeTab = input.tab('Time Window');
const myTimeRow = myTimeTab.row();
const myTimestampStart = myTimeRow.number('Time Start (unix sec)', 1388534400, { min: 0 });
const myTimestampEnd = myTimeRow.number('Time End (unix sec)', 2555021940, { min: 0 });

const myStrictPosition = input.boolean('Strict position', false);

// ── Helper: builds the ZigZag LEVEL_LONG / LEVEL_SHORT arrays
// exactly reproducing the recursive Pine logic, using a plain loop
// (this is custom stateful recursion, not a call to an indicator
// function inside a loop).
function myBuildZigZagLevels(myLengthParam, myDetectionParam) {
	const myLowest = lowest(low, myDetectionParam);
	const myHighest = highest(high, myDetectionParam);

	const myLen1 = Math.round(myLengthParam / 3 * 3);
	const myLen2 = Math.round(myLengthParam / 3 * 2);
	const myLen3 = Math.round(myLengthParam / 3);

	const myEma1 = ema(close, myLen1);
	const myEma2 = ema(myEma1, myLen2);
	const myEma3 = ema(myEma2, myLen3);

	const myN = close.length;
	const myZ = series_of(0);
	const myPoint = series_of(0);
	const myLevelLong = series_of(0);
	const myLevelShort = series_of(0);

	for (let myIndex = 0; myIndex < myN; myIndex += 1) {
		if (myIndex >= 2) {
			const myCurr = myEma3[myIndex];
			const myPrev = myEma3[myIndex - 1];
			const myPrev2 = myEma3[myIndex - 2];

			if (myCurr >= myPrev && myPrev < myPrev2) {
				myZ[myIndex] = myLowest[myIndex];
			}
			else if (myCurr < myPrev && myPrev >= myPrev2) {
				myZ[myIndex] = myHighest[myIndex];
			}
			else {
				myZ[myIndex] = 0;
			}
		}
		else {
			myZ[myIndex] = 0;
		}

		const myPrevPoint = myIndex > 0 ? myPoint[myIndex - 1] : 0;
		myPoint[myIndex] = myZ[myIndex] === 0 ? myPrevPoint : myZ[myIndex];

		const myPrevLevelLong = myIndex > 0 ? myLevelLong[myIndex - 1] : 0;
		const myPrevLevelShort = myIndex > 0 ? myLevelShort[myIndex - 1] : 0;

		myLevelLong[myIndex] = (myPoint[myIndex] > myPrevPoint) ? myZ[myIndex] : myPrevLevelLong;
		myLevelShort[myIndex] = (myPoint[myIndex] < myPrevPoint) ? myZ[myIndex] : myPrevLevelShort;
	}

	return { levelLong: myLevelLong, levelShort: myLevelShort };
}

const myZigZag1 = myBuildZigZagLevels(myLength, myDetection);
const myZigZag2 = myBuildZigZagLevels(myLength2, myDetection2);

const myLevelLong = myZigZag1.levelLong;
const myLevelShort2 = myZigZag2.levelShort;

// ── Time window filter
const myTrueTime = for_every(time, _t => (_t > myTimestampStart && _t < myTimestampEnd));

// ── Virtual position (used only when "Strict position" is on)
const myVirtualPos = series_of(0);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevPos = myIndex > 0 ? myVirtualPos[myIndex - 1] : 0;
	let myPos = myPrevPos;

	if (myStrictPosition) {
		const myCloseNow = close[myIndex];
		const myClosePrev = myIndex > 0 ? close[myIndex - 1] : myCloseNow;
		const myShort2Now = myLevelShort2[myIndex];
		const myLongNow = myLevelLong[myIndex];

		if (myPos === 1 && myCloseNow <= myShort2Now && myClosePrev > myShort2Now) {
			myPos = 0;
		}
		if (myPos === -1 && myCloseNow >= myLongNow && myClosePrev < myLongNow) {
			myPos = 0;
		}
		if (myPos !== 1 && myCloseNow >= myLongNow) {
			myPos = 1;
		}
		if (myPos !== -1 && myCloseNow <= myShort2Now) {
			myPos = -1;
		}
	}

	myVirtualPos[myIndex] = myPos;
}

// ── Entry conditions
const myLongEntry = for_every(myLevelLong, myVirtualPos, myTrueTime, (_lvl, _pos, _tt) =>
	(_lvl > 0 && myNeedLong && _tt && _pos !== 1)
);

const myShortEntry = for_every(myLevelShort2, myVirtualPos, myTrueTime, (_lvl, _pos, _tt) =>
	(_lvl > 0 && myNeedShort && _tt && _pos !== -1)
);

// ── Painting
const myLongLinePainted = paint(myLevelLong, { name: 'LONG', color: '#00FF88', thickness: 2 });
const myShortLinePainted = paint(myLevelShort2, { name: 'SHORT', color: '#FF4D4D', thickness: 2 });

// Candle coloring to represent the virtual position (bgcolor equivalent)
const myCandleColors = for_every(myVirtualPos, _pos => {
	if (_pos === 1) { return 'rgba(76,175,79,0.3)'; }
	if (_pos === -1) { return 'rgba(255,82,82,0.3)'; }
	return null;
});
color_candles(myCandleColors);

// ── Signals for scanners / alerts / strategy tester
register_signal(myLongEntry, 'Long Entry');
register_signal(myShortEntry, 'Short Entry');
register_signal(for_every(myVirtualPos, _pos => _pos === 1), 'Virtual Long Position');
register_signal(for_every(myVirtualPos, _pos => _pos === -1), 'Virtual Short Position');
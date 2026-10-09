describe_indicator('Inside Bar Sequence Marker', 'price');

// Replicates the Pine Script mother-bar / inside-bar sequence logic.
// A new sequence starts when the current candle is fully inside the
// previous candle (the "mother bar"). The sequence continues as long
// as subsequent candles stay inside that same original mother bar
// range. Once a candle breaks out of the mother bar range, the
// sequence ends and a new mother bar can be formed later.

const myInsideMotherBar = series_of(false);

let myMotherHigh = null;
let myMotherLow = null;
let myInInsideSequence = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myIndex === 0) {
		myInsideMotherBar[myIndex] = false;
		continue;
	}

	const myFirstInsideBar = high[myIndex] <= high[myIndex - 1] && low[myIndex] >= low[myIndex - 1];

	if (!myInInsideSequence && myFirstInsideBar) {
		myMotherHigh = high[myIndex - 1];
		myMotherLow = low[myIndex - 1];
		myInInsideSequence = true;
	}

	const myCurrentInsideMotherBar = myInInsideSequence && high[myIndex] <= myMotherHigh && low[myIndex] >= myMotherLow;

	if (myInInsideSequence && !myCurrentInsideMotherBar) {
		myInInsideSequence = false;
		myMotherHigh = null;
		myMotherLow = null;
	}

	myInsideMotherBar[myIndex] = myInInsideSequence && high[myIndex] <= myMotherHigh && low[myIndex] >= myMotherLow;
}

// colors every candle that is inside the mother bar range, in yellow
const myCandleColors = for_every(myInsideMotherBar, _myFlag => _myFlag ? 'yellow' : null);
color_candles(myCandleColors);

// marks every inside bar candle with a small circle below the bar
const myInsideBarMarks = for_every(myInsideMotherBar, _myFlag => _myFlag ? constants.icons.circle : null);
paint(myInsideBarMarks, { name: 'InsideBar', style: 'labels_below', color: 'yellow' });

// signal usable in scanners, alerts and strategies
register_signal(myInsideMotherBar, 'Inside Bar');
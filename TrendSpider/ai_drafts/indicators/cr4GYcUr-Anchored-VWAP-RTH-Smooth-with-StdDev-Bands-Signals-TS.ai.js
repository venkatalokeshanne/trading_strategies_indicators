describe_indicator('Anchored VWAP RTH Smooth with Bands and Signals', 'price');

// ============================= INPUTS =============================
const tabVwap = input.tab('VWAP Settings');
const myAnchorInput = tabVwap.select('Anchor Period', 'Session', ['Session', 'Week', 'Month']);
const mySrcInput = tabVwap.select('VWAP Source', 'hlc3', constants.price_source_options);

const tabRth = input.tab('RTH (UK time)');
const myUseRTH = tabRth.boolean('Restrict to RTH', true);
const myRthRow1 = tabRth.row();
const myRthStartHour = myRthRow1.number('RTH Start Hour', 14, { min: 0, max: 23 });
const myRthStartMin = myRthRow1.number('RTH Start Min', 30, { min: 0, max: 59 });
const myRthRow2 = tabRth.row();
const myRthEndHour = myRthRow2.number('RTH End Hour', 22, { min: 0, max: 23 });
const myRthEndMin = myRthRow2.number('RTH End Min', 0, { min: 0, max: 59 });

const tabBands = input.tab('StdDev Bands');
const myShowBands = tabBands.boolean('Show Bands', true);
const myBand1Mult = tabBands.number('Inner Band Mult', 1.0, { min: 0.1, max: 20, step: 0.1 });
const myBand2Mult = tabBands.number('Outer Band Mult', 2.0, { min: 0.1, max: 20, step: 0.1 });

const tabSignal = input.tab('Signal Markers');
const myMarkerIntervalTF = tabSignal.select('Marker Interval TF', '15', constants.time_frames);
const myThreshPctInput = tabSignal.number('Signal Threshold %', 0.1, { min: 0, max: 100, step: 0.01 }) / 100;

// Colors are not exposed as inputs: the platform already auto-generates
// color/thickness/style controls for every paint() call.
const myVwapColor = '#1565C0';
const myBand1Color = 'rgba(21,101,192,0.4)';
const myBand2Color = 'rgba(21,101,192,0.2)';
const myPlusColor = '#00C853';
const myMinusColor = '#D50000';

const myStartMinutes = myRthStartHour * 60 + myRthStartMin;
const myEndMinutes = myRthEndHour * 60 + myRthEndMin;

// ============================= UK TIME COMPUTATION =============================
// Pine uses hour(time, "Europe/London") and minute(time, "Europe/London").
// We reproduce exact UK local time using the moment-timezone library.
const myMoment = library('moment-timezone');
const mySrc = market[mySrcInput];

const myUkInfo = time.map(_t => {
	const myM = myMoment.unix(_t).tz('Europe/London');
	return {
		hour: myM.hour(),
		minute: myM.minute(),
		isoWeek: myM.isoWeek(),
		isoWeekYear: myM.isoWeekYear(),
		month: myM.month(),
		year: myM.year()
	};
});

// ============================= SMOOTH ANCHORED VWAP (sequential state) =============================
const myVwapVal = series_of(null);
const myStdevVal = series_of(null);
const myUpperBand1 = series_of(null);
const myLowerBand1 = series_of(null);
const myUpperBand2 = series_of(null);
const myLowerBand2 = series_of(null);
const myInRTHArr = series_of(false);

let myPrevInRTH = false;
let mySumPV = null;
let mySumPPV = null;
let mySumV = null;

for (let myI = 0; myI < time.length; myI += 1) {
	const myCurMin = myUkInfo[myI].hour * 60 + myUkInfo[myI].minute;
	const myInRTH = !myUseRTH || (myCurMin >= myStartMinutes && myCurMin < myEndMinutes);
	myInRTHArr[myI] = myInRTH;

	const myDayReset = myInRTH && !myPrevInRTH;

	let myWeekChanged = false;
	let myMonthChanged = false;

	if (myI > 0) {
		myWeekChanged = (myUkInfo[myI].isoWeek !== myUkInfo[myI - 1].isoWeek) || (myUkInfo[myI].isoWeekYear !== myUkInfo[myI - 1].isoWeekYear);
		myMonthChanged = (myUkInfo[myI].month !== myUkInfo[myI - 1].month) || (myUkInfo[myI].year !== myUkInfo[myI - 1].year);
	}

	let myPeriodChanged = false;
	if (myAnchorInput === 'Session') {
		myPeriodChanged = myDayReset;
	}
	else if (myAnchorInput === 'Week') {
		myPeriodChanged = myDayReset && myWeekChanged;
	}
	else {
		myPeriodChanged = myDayReset && myMonthChanged;
	}

	if (myInRTH) {
		if (myPeriodChanged || mySumPV === null) {
			mySumPV = mySrc[myI] * volume[myI];
			mySumPPV = mySrc[myI] * mySrc[myI] * volume[myI];
			mySumV = volume[myI];
		}
		else {
			mySumPV = mySumPV + mySrc[myI] * volume[myI];
			mySumPPV = mySumPPV + mySrc[myI] * mySrc[myI] * volume[myI];
			mySumV = mySumV + volume[myI];
		}

		const myVwapHere = mySumPV / mySumV;
		const myVariance = mySumPPV / mySumV - myVwapHere * myVwapHere;
		const myStdevHere = Math.sqrt(Math.max(myVariance, 0));

		myVwapVal[myI] = myVwapHere;
		myStdevVal[myI] = myStdevHere;

		if (myShowBands) {
			myUpperBand1[myI] = myVwapHere + myStdevHere * myBand1Mult;
			myLowerBand1[myI] = myVwapHere - myStdevHere * myBand1Mult;
			myUpperBand2[myI] = myVwapHere + myStdevHere * myBand2Mult;
			myLowerBand2[myI] = myVwapHere - myStdevHere * myBand2Mult;
		}
	}

	myPrevInRTH = myInRTH;
}

// ============================= PLOTS =============================
const myVwapLine = paint(myVwapVal, { name: 'Anchored VWAP', color: myVwapColor, thickness: 2, style: 'line' });
const myU1 = paint(myUpperBand1, { name: 'Upper Band Inner', color: myBand1Color, style: 'line' });
const myL1 = paint(myLowerBand1, { name: 'Lower Band Inner', color: myBand1Color, style: 'line' });
const myU2 = paint(myUpperBand2, { name: 'Upper Band Outer', color: myBand2Color, style: 'line' });
const myL2 = paint(myLowerBand2, { name: 'Lower Band Outer', color: myBand2Color, style: 'line' });

fill(myU1, myL1, myBand1Color, 0.1);
fill(myU2, myU1, myBand2Color, 0.08);
fill(myL1, myL2, myBand2Color, 0.08);

// ============================= SIGNAL MARKERS =============================
// Detects the start of a new higher timeframe bar using bar_at() boundaries,
// as a substitute for Pine's timeframe.change().
const myMarkerSessions = time.map(_t => bar_at(_t, myMarkerIntervalTF).session);
const myNewMarkerBar = series_of(false);

for (let myI = 0; myI < time.length; myI += 1) {
	myNewMarkerBar[myI] = myI === 0 ? true : (myMarkerSessions[myI] !== myMarkerSessions[myI - 1]);
}

const myAboveSignal = series_of(false);
const myBelowSignal = series_of(false);
const myAboveMarker = series_of(null);
const myBelowMarker = series_of(null);

for (let myI = 0; myI < time.length; myI += 1) {
	if (myVwapVal[myI] === null) continue;

	const myPctDiff = (close[myI] - myVwapVal[myI]) / myVwapVal[myI];
	const myIsAbove = myNewMarkerBar[myI] && myInRTHArr[myI] && myPctDiff >= myThreshPctInput;
	const myIsBelow = myNewMarkerBar[myI] && myInRTHArr[myI] && myPctDiff <= -myThreshPctInput;

	myAboveSignal[myI] = myIsAbove;
	myBelowSignal[myI] = myIsBelow;

	if (myIsAbove) myAboveMarker[myI] = myVwapVal[myI];
	if (myIsBelow) myBelowMarker[myI] = myVwapVal[myI];
}

paint(myAboveMarker, { name: 'Above VWAP Plus', color: myPlusColor, style: 'labels_above' });
paint(myBelowMarker, { name: 'Below VWAP Minus', color: myMinusColor, style: 'labels_below' });

// ============================= SIGNALS FOR SCANNER / STRATEGY / ALERTS =============================
register_signal(myAboveSignal, 'Price above VWAP');
register_signal(myBelowSignal, 'Price below VWAP');
describe_indicator('VWAP Alert', 'price');

// NOTE: Pine's input.source() is not available in this API, so the source
// is fixed to hlc3 (matches the original script's default value).
const myMult1 = input.number('Band 1 Multiplier', 1.0, { min: 0, max: 10 });
const myMult2 = input.number('Band 2 Multiplier', 2.0, { min: 0, max: 10 });
const myAlarmMult = input.number('Alarm Multiplier', 1.8, { min: 0, max: 10 });

const mySrc = hlc3;
const myLength = close.length;

const myVwap = series_of(null);
const myUpperBand1 = series_of(null);
const myLowerBand1 = series_of(null);
const myUpperBand2 = series_of(null);
const myLowerBand2 = series_of(null);
const myUpperAlarm = series_of(null);
const myLowerAlarm = series_of(null);

const myArmedUpper = series_of(true);
const myArmedLower = series_of(true);
const myOverboughtSignal = series_of(false);
const myOversoldSignal = series_of(false);

let mySumSrcVol = null;
let mySumVol = null;
let mySumSrcSqVol = null;
let myPrevClose = null;
let myPrevUpperBand1 = null;
let myPrevLowerBand1 = null;
let myPrevUpperAlarm = null;
let myPrevLowerAlarm = null;
let myArmedUpperState = true;
let myArmedLowerState = true;
let myPrevSessionKey = null;

// This loop is required because the logic is inherently stateful/sequential
// (cumulative session sums and armed/disarmed state machine), which cannot
// be expressed via the provided indicator functions.
for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const mySessionInfo = bar_at(time[myIndex]);
	const mySessionKey = mySessionInfo.session;
	const myIsNewSession = mySessionKey !== myPrevSessionKey;
	myPrevSessionKey = mySessionKey;

	if (myIsNewSession) {
		myArmedUpperState = true;
		myArmedLowerState = true;
	}

	const myCurSrc = mySrc[myIndex];
	const myCurVol = volume[myIndex];

	if (myIsNewSession) {
		mySumSrcVol = myCurSrc * myCurVol;
		mySumVol = myCurVol;
		mySumSrcSqVol = myCurSrc * myCurSrc * myCurVol;
	}
	else {
		mySumSrcVol = mySumSrcVol + myCurSrc * myCurVol;
		mySumVol = mySumVol + myCurVol;
		mySumSrcSqVol = mySumSrcSqVol + myCurSrc * myCurSrc * myCurVol;
	}

	const myVwapValue = mySumSrcVol / mySumVol;
	const myVariance = (mySumSrcSqVol / mySumVol) - (myVwapValue * myVwapValue);
	const myStdev = Math.sqrt(Math.max(myVariance, 0));

	const myUpperBand1Value = myVwapValue + myStdev * myMult1;
	const myLowerBand1Value = myVwapValue - myStdev * myMult1;
	const myUpperBand2Value = myVwapValue + myStdev * myMult2;
	const myLowerBand2Value = myVwapValue - myStdev * myMult2;
	const myUpperAlarmValue = myVwapValue + myStdev * myAlarmMult;
	const myLowerAlarmValue = myVwapValue - myStdev * myAlarmMult;

	const myCurClose = close[myIndex];

	// re-arm on retracement back inside band1
	if (myPrevClose !== null && myPrevUpperBand1 !== null) {
		if (myCurClose < myUpperBand1Value && myPrevClose >= myPrevUpperBand1) {
			myArmedUpperState = true;
		}
	}
	if (myPrevClose !== null && myPrevLowerBand1 !== null) {
		if (myCurClose > myLowerBand1Value && myPrevClose <= myPrevLowerBand1) {
			myArmedLowerState = true;
		}
	}

	let myOverboughtFired = false;
	let myOversoldFired = false;

	if (myPrevClose !== null && myPrevUpperAlarm !== null) {
		if (myCurClose > myUpperAlarmValue && myPrevClose <= myPrevUpperAlarm && myArmedUpperState) {
			myOverboughtFired = true;
		}
	}
	if (myPrevClose !== null && myPrevLowerAlarm !== null) {
		if (myCurClose < myLowerAlarmValue && myPrevClose >= myPrevLowerAlarm && myArmedLowerState) {
			myOversoldFired = true;
		}
	}

	// disarm once alert fires
	if (myPrevClose !== null && myPrevUpperAlarm !== null && myCurClose > myUpperAlarmValue && myPrevClose <= myPrevUpperAlarm) {
		myArmedUpperState = false;
	}
	if (myPrevClose !== null && myPrevLowerAlarm !== null && myCurClose < myLowerAlarmValue && myPrevClose >= myPrevLowerAlarm) {
		myArmedLowerState = false;
	}

	myVwap[myIndex] = myVwapValue;
	myUpperBand1[myIndex] = myUpperBand1Value;
	myLowerBand1[myIndex] = myLowerBand1Value;
	myUpperBand2[myIndex] = myUpperBand2Value;
	myLowerBand2[myIndex] = myLowerBand2Value;
	myUpperAlarm[myIndex] = myUpperAlarmValue;
	myLowerAlarm[myIndex] = myLowerAlarmValue;
	myArmedUpper[myIndex] = myArmedUpperState;
	myArmedLower[myIndex] = myArmedLowerState;
	myOverboughtSignal[myIndex] = myOverboughtFired;
	myOversoldSignal[myIndex] = myOversoldFired;

	myPrevClose = myCurClose;
	myPrevUpperBand1 = myUpperBand1Value;
	myPrevLowerBand1 = myLowerBand1Value;
	myPrevUpperAlarm = myUpperAlarmValue;
	myPrevLowerAlarm = myLowerAlarmValue;
}

paint(myVwap, { name: 'VWAP', color: '#2196F3', thickness: 2 });
paint(myUpperBand1, { name: 'Upper Band 1', color: '#FFFFFF' });
paint(myLowerBand1, { name: 'Lower Band 1', color: '#FFFFFF' });
paint(myUpperBand2, { name: 'Upper Band 2', color: '#EF5350' });
paint(myLowerBand2, { name: 'Lower Band 2', color: '#EF5350' });
paint(myUpperAlarm, { name: 'Upper Alarm Band', color: '#FF9800', style: 'dotted' });
paint(myLowerAlarm, { name: 'Lower Alarm Band', color: '#FF9800', style: 'dotted' });

register_signal(myOverboughtSignal, 'VWAP Overbought');
register_signal(myOversoldSignal, 'VWAP Oversold');
register_signal(myArmedUpper, 'Armed Upper');
register_signal(myArmedLower, 'Armed Lower');

const myArmedUpperLast = myArmedUpper[myArmedUpper.length - 1];
const myArmedLowerLast = myArmedLower[myArmedLower.length - 1];

paint_overlay('VwapAlertStatus', { position: 'top_right' }, {
	rows: [
		{
			cells: [{
				text: myArmedUpperLast ? 'ARMED UPPER' : 'Upper Alarm DISARMED',
				color: '#FFFFFF',
				background_color: myArmedUpperLast ? '#2E7D32' : '#757575'
			}]
		},
		{
			cells: [{
				text: myArmedLowerLast ? 'ARMED LOWER' : 'Lower Alarm DISARMED',
				color: '#FFFFFF',
				background_color: myArmedLowerLast ? '#2E7D32' : '#757575'
			}]
		}
	]
});
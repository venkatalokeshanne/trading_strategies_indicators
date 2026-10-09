/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : VWAP Alert
 * Author       : icenet_ml
 * Source URL   : https://www.tradingview.com/script/PsHyo87Z-CanadianGoose-VWAP
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : VWAP Alert Bands_TV
 *
 * Deviations from the original: VWAP/bands reset per calendar day (exchange time); armed-state banner is a static
 *   overlay of the last bar; alarms exposed as signals
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('VWAP Alert Bands_TV', 'price');
const myMult1 = input.number('Band 1 Multiplier', 1.0, { min: 0, max: 10, step: 0.1 });
const myMult2 = input.number('Band 2 Multiplier', 2.0, { min: 0, max: 10, step: 0.1 });
const myAlarmMult = input.number('Alarm Multiplier', 1.8, { min: 0, max: 10, step: 0.1 });
const myN = close.length;
// VWAP with standard-deviation bands, reset every day (exchange time)
const myDayKey = time.map(_t => { const myX = time_of(_t); return myX.month * 100 + myX.dayOfMonth; });
const myVwap = close.map(() => null), myU1 = close.map(() => null), myL1 = close.map(() => null);
const myU2 = close.map(() => null), myL2 = close.map(() => null), myUA = close.map(() => null), myLA = close.map(() => null);
const myOb = close.map(() => false), myOs = close.map(() => false);
const myArmUp = close.map(() => true), myArmLo = close.map(() => true);
let mySV = 0, myV = 0, mySSV = 0, myArmedUpper = true, myArmedLower = true;
for (let myI = 0; myI < myN; myI += 1) {
	const myNew = myI === 0 || myDayKey[myI] !== myDayKey[myI - 1];
	if (myNew) { myArmedUpper = true; myArmedLower = true; mySV = 0; myV = 0; mySSV = 0; }
	const mySrc = (high[myI] + low[myI] + close[myI]) / 3;
	mySV += mySrc * volume[myI]; myV += volume[myI]; mySSV += mySrc * mySrc * volume[myI];
	if (myV > 0) {
		const myVw = mySV / myV;
		const myDev = Math.sqrt(Math.max(mySSV / myV - myVw * myVw, 0));
		myVwap[myI] = myVw; myU1[myI] = myVw + myDev * myMult1; myL1[myI] = myVw - myDev * myMult1;
		myU2[myI] = myVw + myDev * myMult2; myL2[myI] = myVw - myDev * myMult2;
		myUA[myI] = myVw + myDev * myAlarmMult; myLA[myI] = myVw - myDev * myAlarmMult;
		if (myI > 0 && myU1[myI - 1] !== null) {
			const myP = close[myI - 1];
			if (close[myI] < myU1[myI] && myP >= myU1[myI - 1]) myArmedUpper = true;
			if (close[myI] > myL1[myI] && myP <= myL1[myI - 1]) myArmedLower = true;
			const myCrossUp = close[myI] > myUA[myI] && myP <= myUA[myI - 1];
			const myCrossDn = close[myI] < myLA[myI] && myP >= myLA[myI - 1];
			myOb[myI] = myCrossUp && myArmedUpper;
			myOs[myI] = myCrossDn && myArmedLower;
			if (myCrossUp) myArmedUpper = false;
			if (myCrossDn) myArmedLower = false;
		}
	}
	myArmUp[myI] = myArmedUpper; myArmLo[myI] = myArmedLower;
}
paint(myVwap, { name: 'VWAP', color: 'blue', thickness: 2 });
paint(myU1, { name: 'Upper Band 1', color: 'white' });
paint(myL1, { name: 'Lower Band 1', color: 'white' });
paint(myU2, { name: 'Upper Band 2', color: 'red' });
paint(myL2, { name: 'Lower Band 2', color: 'red' });
paint(myUA, { name: 'Upper Alarm Band', color: 'orange', style: 'dotted', marker: 'circle' });
paint(myLA, { name: 'Lower Alarm Band', color: 'orange', style: 'dotted', marker: 'circle' });
const myLast = myN - 1;
paint_overlay('VWAP Status', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: myArmUp[myLast] ? 'GOOSE VWAP ARMED UPPER' : 'Upper Alarm DISARMED', color: 'white', background_color: myArmUp[myLast] ? 'green' : 'gray' }] },
		{ cells: [{ text: myArmLo[myLast] ? 'GOOSE VWAP ARMED LOWER' : 'Lower Alarm DISARMED', color: 'white', background_color: myArmLo[myLast] ? 'green' : 'gray' }] }
	]
});
register_signal(myOb, 'VWAP OVERBOUGHT');
register_signal(myOs, 'VWAP OVERSOLD');

describe_indicator('VPA and Wyckoff Accumulation and Distribution', 'price');

// ==========================================
// INPUTS
// ==========================================
const myTab1 = input.tab('Moving Averages and Volume');
const mySmaLen = myTab1.number('Volume and Spread SMA Length', 20, { min: 1, max: 500 });
const myTrendLen = myTab1.number('Trend SMA Length', 50, { min: 1, max: 500 });

const myTab2 = input.tab('Margin Settings');
// Use 2% for Stocks/Crypto, lower to 0.1% or 0.2% for Forex
const myStMarginPct = myTab2.number('Secondary Test Margin Percent', 2.0, { min: 0, max: 50, step: 0.1 }) / 100;

// ==========================================
// CORE SERIES
// ==========================================
const myV = volume;
const myAvgV = sma(myV, mySmaLen);
const mySpread = sub(high, low);
const myAvgSpread = sma(mySpread, mySmaLen);
const myLowerWick = sub(min_of(open, close), low);
const myUpperWick = sub(high, max_of(open, close));
const myMa50 = sma(close, myTrendLen);
const myCloseShift10 = shift(close, 10);
const myLen = close.length;

// Output series
const myStoppingVolume = series_of(false);
const myBuyST = series_of(false);
const mySpring = series_of(false);
const mySOS = series_of(false);
const myBuyingClimax = series_of(false);
const mySellST = series_of(false);
const myUTAD = series_of(false);
const mySOW = series_of(false);

// State tracking (plain JS, mimics Pine var persistence) - not an indicator
// function call, so looping here is allowed.
let myAccState = 0;
let myScLow = null;
let myArHigh = null;
let myDistState = 0;
let myBcHigh = null;
let myArLow = null;

for (let myIndex = 0; myIndex < myLen; myIndex += 1) {
	const myClose = close[myIndex];
	const myOpen = open[myIndex];
	const myHigh = high[myIndex];
	const myLow = low[myIndex];
	const myVolVal = myV[myIndex];
	const myAvgVVal = myAvgV[myIndex];
	const mySpreadVal = mySpread[myIndex];
	const myAvgSpreadVal = myAvgSpread[myIndex];
	const myLowerWickVal = myLowerWick[myIndex];
	const myUpperWickVal = myUpperWick[myIndex];
	const myMa50Val = myMa50[myIndex];
	const myCloseShift10Val = myCloseShift10[myIndex];
	const myHasHistory = myMa50Val != null && myAvgVVal != null && myAvgSpreadVal != null && myCloseShift10Val != null;

	let myLocalStoppingVolume = false;
	let myLocalBuyST = false;
	let myLocalSpring = false;
	let myLocalSOS = false;
	let myLocalBuyingClimax = false;
	let myLocalSellST = false;
	let myLocalUTAD = false;
	let myLocalSOW = false;

	if (myHasHistory) {
		const myVolAnomaly = myVolVal > (myAvgVVal * 2);

		// ===== ACCUMULATION =====
		const myDowntrend = (myClose < myMa50Val) && (myClose < myCloseShift10Val);
		const myHammer = myLowerWickVal > (0.5 * mySpreadVal);
		const myNarrowDown = (mySpreadVal < myAvgSpreadVal) && (myClose < myOpen);
		myLocalStoppingVolume = myDowntrend && myVolAnomaly && (myHammer || myNarrowDown);

		if (myLocalStoppingVolume) {
			myAccState = 1;
			myScLow = myLow;
			myArHigh = myHigh;
		}

		if (myAccState > 0) {
			if (myAccState === 1) {
				myArHigh = Math.max(myArHigh, myHigh);
			}

			const myStUpperBand = myScLow * (1 + myStMarginPct);

			if (myAccState === 1 && (myLow <= myStUpperBand) && (myLow >= myScLow) && (myVolVal < myAvgVVal) && !myLocalStoppingVolume) {
				myAccState = 2;
				myLocalBuyST = true;
			}

			if ((myLow < myScLow) && (myClose > myScLow) && (myVolVal > myAvgVVal) && !myLocalStoppingVolume) {
				myLocalSpring = true;
				myAccState = 2;
			}

			if ((myClose > myArHigh) && (myVolVal > myAvgVVal) && (myClose > myOpen)) {
				myLocalSOS = true;
				myAccState = 0;
			}

			if ((myClose < myScLow) && !myLocalSpring) {
				myAccState = 0;
			}
		}

		// ===== DISTRIBUTION =====
		const myUptrend = (myClose > myMa50Val) && (myClose > myCloseShift10Val);
		const myShootingStar = myUpperWickVal > (0.5 * mySpreadVal);
		const myNarrowUp = (mySpreadVal < myAvgSpreadVal) && (myClose > myOpen);
		myLocalBuyingClimax = myUptrend && myVolAnomaly && (myShootingStar || myNarrowUp);

		if (myLocalBuyingClimax) {
			myDistState = 1;
			myBcHigh = myHigh;
			myArLow = myLow;
		}

		if (myDistState > 0) {
			if (myDistState === 1) {
				myArLow = Math.min(myArLow, myLow);
			}

			const myStLowerBand = myBcHigh * (1 - myStMarginPct);

			if (myDistState === 1 && (myHigh >= myStLowerBand) && (myHigh <= myBcHigh) && (myVolVal < myAvgVVal) && !myLocalBuyingClimax) {
				myDistState = 2;
				myLocalSellST = true;
			}

			if ((myHigh > myBcHigh) && (myClose < myBcHigh) && (myVolVal > myAvgVVal) && !myLocalBuyingClimax) {
				myLocalUTAD = true;
				myDistState = 2;
			}

			if ((myClose < myArLow) && (myVolVal > myAvgVVal) && (myClose < myOpen)) {
				myLocalSOW = true;
				myDistState = 0;
			}

			if ((myClose > myBcHigh) && !myLocalUTAD) {
				myDistState = 0;
			}
		}
	}

	myStoppingVolume[myIndex] = myLocalStoppingVolume;
	myBuyST[myIndex] = myLocalBuyST;
	mySpring[myIndex] = myLocalSpring;
	mySOS[myIndex] = myLocalSOS;
	myBuyingClimax[myIndex] = myLocalBuyingClimax;
	mySellST[myIndex] = myLocalSellST;
	myUTAD[myIndex] = myLocalUTAD;
	mySOW[myIndex] = myLocalSOW;
}

// ==========================================
// MARKER SERIES (sparse, for painting as labels)
// ==========================================
const myStoppingVolumeMarks = for_every(myStoppingVolume, low, (_f, _l) => _f ? _l : null);
const myBuySTMarks = for_every(myBuyST, low, (_f, _l) => _f ? _l : null);
const mySpringMarks = for_every(mySpring, low, (_f, _l) => _f ? _l : null);
const mySOSMarks = for_every(mySOS, low, (_f, _l) => _f ? _l : null);
const myBuyingClimaxMarks = for_every(myBuyingClimax, high, (_f, _h) => _f ? _h : null);
const mySellSTMarks = for_every(mySellST, high, (_f, _h) => _f ? _h : null);
const myUTADMarks = for_every(myUTAD, high, (_f, _h) => _f ? _h : null);
const mySOWMarks = for_every(mySOW, high, (_f, _h) => _f ? _h : null);

// ==========================================
// PAINTING (markers below/above bars)
// ==========================================
paint(myStoppingVolumeMarks, { name: 'SellingClimax', style: 'labels_below', color: 'blue' });
paint(myBuySTMarks, { name: 'BuySecondaryTest', style: 'labels_below', color: 'orange' });
paint(mySpringMarks, { name: 'Spring', style: 'labels_below', color: 'teal' });
paint(mySOSMarks, { name: 'SignOfStrength', style: 'labels_below', color: 'green' });
paint(myBuyingClimaxMarks, { name: 'BuyingClimax', style: 'labels_above', color: 'red' });
paint(mySellSTMarks, { name: 'SellSecondaryTest', style: 'labels_above', color: 'orange' });
paint(myUTADMarks, { name: 'Upthrust', style: 'labels_above', color: 'fuchsia' });
paint(mySOWMarks, { name: 'SignOfWeakness', style: 'labels_above', color: 'red' });

// ==========================================
// SIGNALS (for scanner, alerts, strategy)
// Signal names must be distinct from paint() names, since both
// share the same output namespace. Renamed signals below to avoid
// the "already exists" collision (e.g. "Spring" paint vs "Spring" signal).
// ==========================================
register_signal(myStoppingVolume, 'Selling Climax Signal');
register_signal(myBuyST, 'Buy Secondary Test Signal');
register_signal(mySpring, 'Spring Signal');
register_signal(mySOS, 'Sign of Strength Signal');
register_signal(myBuyingClimax, 'Buying Climax Signal');
register_signal(mySellST, 'Sell Secondary Test Signal');
register_signal(myUTAD, 'Upthrust UTAD Signal');
register_signal(mySOW, 'Sign of Weakness Signal');
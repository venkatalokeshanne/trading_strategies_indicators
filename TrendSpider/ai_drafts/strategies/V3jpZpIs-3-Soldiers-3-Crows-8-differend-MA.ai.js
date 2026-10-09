describe_indicator('3 Soldiers 3 Crows plus MA Filter', 'price');

// === MA / source settings ===
const myMaTab = input.tab('MA Settings');
const mySourceName = myMaTab.select('Price source', 'high', constants.price_source_options);
const myMaRow1 = myMaTab.row();
const myMa1Type = myMaRow1.select('MA 1 type (fast)', 'SMA', ['SMA', 'EMA', 'WMA', 'DEMA', 'HMA', 'VAR', 'ZLEMA', 'RMA']);
const myMa1Length = myMaRow1.number('MA 1 length', 22, { min: 1, max: 1000 });
const myMaRow2 = myMaTab.row();
const myMa2Type = myMaRow2.select('MA 2 type (slow)', 'ZLEMA', ['SMA', 'EMA', 'WMA', 'DEMA', 'HMA', 'VAR', 'ZLEMA', 'RMA']);
const myMa2Length = myMaRow2.number('MA 2 length', 210, { min: 1, max: 2000 });

// === Cooldown settings ===
const myCooldownTab = input.tab('Cooldown Filter');
const myUseCooldown = myCooldownTab.boolean('Use cooldown', true);
const myCooldownPeriod = myCooldownTab.number('Cooldown (bars)', 212, { min: 0, max: 5000 });

const myPrice = market[mySourceName];

// === Custom MA building blocks ===
// DEMA = 2 * EMA1 - EMA2
function myComputeDema(mySrcArr, myLength) {
	const myEma1 = ema(mySrcArr, myLength);
	const myEma2 = ema(myEma1, myLength);
	return sub(mult(myEma1, 2), myEma2);
}

// ZLEMA: ema applied to a de-lagged series (src + (src - src[lag]))
function myComputeZlema(mySrcArr, myLength) {
	const myLag = Math.floor((myLength - 1) / 2);
	const myShifted = shift(mySrcArr, myLag);
	const myEmaData = for_every(mySrcArr, myShifted, (_src, _shifted) => _src + (_src - (_shifted === null || _shifted === undefined ? _src : _shifted)));
	return ema(myEmaData, myLength);
}

// VAR (CMO-adaptive MA). Recursive by nature, so computed with a plain loop
// (no indicator functions called inside the loop, only arithmetic + sum()).
// NOTE: "new Array(...)" is prohibited by the scripting engine, so we build
// arrays using Array(...).fill(...) instead (no "new" keyword needed).
function myComputeVar(mySrcArr, myLength) {
	const myAlpha = 2 / (myLength + 1);
	const myLen = mySrcArr.length;
	const myDiffUp = Array(myLen).fill(0);
	const myDiffDown = Array(myLen).fill(0);
	for (let myIndex = 0; myIndex < myLen; myIndex += 1) {
		const myPrevValue = myIndex > 0 ? mySrcArr[myIndex - 1] : mySrcArr[myIndex];
		myDiffUp[myIndex] = mySrcArr[myIndex] > myPrevValue ? mySrcArr[myIndex] - myPrevValue : 0;
		myDiffDown[myIndex] = mySrcArr[myIndex] < myPrevValue ? myPrevValue - mySrcArr[myIndex] : 0;
	}
	const myUpSum = sum(myDiffUp, 9);
	const myDownSum = sum(myDiffDown, 9);
	const myVarArr = Array(myLen).fill(null);
	let myPrevVar = 0;
	for (let myIndex = 0; myIndex < myLen; myIndex += 1) {
		const myDenom = myUpSum[myIndex] + myDownSum[myIndex];
		const myCmo = myDenom ? (myUpSum[myIndex] - myDownSum[myIndex]) / myDenom : 0;
		const myValue = (myAlpha * Math.abs(myCmo) * mySrcArr[myIndex]) + ((1 - myAlpha * Math.abs(myCmo)) * myPrevVar);
		myVarArr[myIndex] = myValue;
		myPrevVar = myValue;
	}
	return myVarArr;
}

function myGetMA(mySrcArr, myLength, myType) {
	switch (myType) {
		case 'SMA': return sma(mySrcArr, myLength);
		case 'EMA': return ema(mySrcArr, myLength);
		case 'WMA': return wma(mySrcArr, myLength);
		case 'DEMA': return myComputeDema(mySrcArr, myLength);
		case 'HMA': return hullma(mySrcArr, myLength);
		case 'VAR': return myComputeVar(mySrcArr, myLength);
		case 'ZLEMA': return myComputeZlema(mySrcArr, myLength);
		case 'RMA': return wildma(mySrcArr, myLength);
		default: return sma(mySrcArr, myLength);
	}
}

const myMa1 = myGetMA(myPrice, myMa1Length, myMa1Type);
const myMa2 = myGetMA(myPrice, myMa2Length, myMa2Type);

// === Pattern detection (Three White Soldiers / Three Black Crows) ===
const myClose1 = shift(close, 1);
const myOpen1 = shift(open, 1);
const myClose2 = shift(close, 2);
const myOpen2 = shift(open, 2);

const myThreeWhiteSoldiers = for_every(
	close, open, myClose1, myOpen1, myClose2, myOpen2,
	(_close, _open, _close1, _open1, _close2, _open2) =>
		_close > _open && _close1 > _open1 && _close2 > _open2 &&
		_open1 <= _close2 && _close1 > _close2 &&
		_open <= _close1 && _close > _close1
);

const myThreeBlackCrows = for_every(
	close, open, myClose1, myOpen1, myClose2, myOpen2,
	(_close, _open, _close1, _open1, _close2, _open2) =>
		_close < _open && _close1 < _open1 && _close2 < _open2 &&
		_open1 >= _close2 && _close1 < _close2 &&
		_open >= _close1 && _close < _close1
);

// === Raw signals (pattern + MA filter, before cooldown) ===
const myBuySignalRaw = for_every(
	myThreeWhiteSoldiers, close, myMa1, myMa2,
	(_pattern, _close, _ma1, _ma2) => Boolean(_pattern) && _close > _ma1 && _close > _ma2
);

const mySellSignalRaw = for_every(
	myThreeBlackCrows, close, myMa1, myMa2,
	(_pattern, _close, _ma1, _ma2) => Boolean(_pattern) && _close < _ma1 && _close < _ma2
);

// === Cooldown logic (sequential state, plain loop, no indicator calls inside) ===
// NOTE: "new Array(...)" is prohibited by the scripting engine, so we build
// arrays using Array(...).fill(...) instead (no "new" keyword needed).
const myBuySignal = Array(close.length).fill(false);
const mySellSignal = Array(close.length).fill(false);
let myLastBuyBar = -Infinity;
let myLastSellBar = -Infinity;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myCanBuy = (myIndex - myLastBuyBar) > myCooldownPeriod;
	const myCanSell = (myIndex - myLastSellBar) > myCooldownPeriod;
	const myBuy = myBuySignalRaw[myIndex] && (!myUseCooldown || myCanBuy);
	const mySell = mySellSignalRaw[myIndex] && (!myUseCooldown || myCanSell);

	if (myBuy) {
		myLastBuyBar = myIndex;
	}
	if (mySell) {
		myLastSellBar = myIndex;
	}

	myBuySignal[myIndex] = myBuy;
	mySellSignal[myIndex] = mySell;
}

// === Visualization ===
paint(myMa1, { name: 'FastMA', color: 'orange', thickness: 2 });
paint(myMa2, { name: 'SlowMA', color: 'blue', thickness: 2 });

// === Signals for scanners, alerts and strategy tester ===
register_signal(myThreeWhiteSoldiers, 'Three White Soldiers Pattern');
register_signal(myThreeBlackCrows, 'Three Black Crows Pattern');
register_signal(myBuySignal, 'Buy Signal Soldiers');
register_signal(mySellSignal, 'Sell Signal Crows');
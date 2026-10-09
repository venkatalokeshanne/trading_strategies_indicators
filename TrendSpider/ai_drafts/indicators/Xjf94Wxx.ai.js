describe_indicator('Congress Smart Zones Clone', 'price');
// NOTE: This is an approximation of the original Pine Script.
// TrendSpider's custom JS engine has no box()/label() drawing
// primitives, so sell/buy "zones" are rendered as pairs of
// ladder-style lines (top/bottom) filled between them, capped
// at a fixed number of 3 slots per side (matches the script's
// default max_sell/max_buy of 3). Labels are placed with
// paint_label_at_line on the last active bar of each zone.
// FIX: each slot now has a unique line name (Top 1, Top 2, ...)
// because paint() requires unique names across all calls;
// reusing the same name for every slot caused the error.
const myPivotLen = input.number('Pivot Period', 20, { min: 1, max: 200 });
const myMacroLen = input.number('Expiration (max candles)', 250, { min: 10, max: 2000 });
const myZoneThick = input.number('Zone Thickness (x ATR)', 0.25, { min: 0.01, max: 5, step: 0.05 });
const myMaxSell = input.number('Max Sell Zones', 3, { min: 1, max: 3 });
const myMaxBuy = input.number('Max Buy Zones', 3, { min: 1, max: 3 });

const SLOTS = 3;

const myAtr = atr(high, low, close, 14);
const myPivotHigh = pivot_high(high, myPivotLen, myPivotLen);
const myPivotLow = pivot_low(low, myPivotLen, myPivotLen);
const myCandleCount = close.length;

// output series, 3 fixed slots per side
const mySellTop = Array.from({ length: SLOTS }, () => series_of(null));
const mySellBottom = Array.from({ length: SLOTS }, () => series_of(null));
const myBuyTop = Array.from({ length: SLOTS }, () => series_of(null));
const myBuyBottom = Array.from({ length: SLOTS }, () => series_of(null));

const mySellActiveSignal = series_of(false);
const myBuyActiveSignal = series_of(false);

let mySellZones = [];
let myBuyZones = [];

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myPivotCandleIndex = myIndex - myPivotLen;

	// create new sell zone when a confirmed pivot high lands at the delayed index
	if (myPivotCandleIndex >= 0 && myPivotHigh[myPivotCandleIndex] !== null) {
		const myTop = high[myPivotCandleIndex];
		const myBottom = myTop - (myAtr[myPivotCandleIndex] || 0) * myZoneThick;
		mySellZones.push({ top: myTop, bottom: myBottom, left: myPivotCandleIndex });
		if (mySellZones.length > myMaxSell) {
			mySellZones.shift();
		}
	}

	// create new buy zone when a confirmed pivot low lands at the delayed index
	if (myPivotCandleIndex >= 0 && myPivotLow[myPivotCandleIndex] !== null) {
		const myBottom = low[myPivotCandleIndex];
		const myTop = myBottom + (myAtr[myPivotCandleIndex] || 0) * myZoneThick;
		myBuyZones.push({ top: myTop, bottom: myBottom, left: myPivotCandleIndex });
		if (myBuyZones.length > myMaxBuy) {
			myBuyZones.shift();
		}
	}

	// invalidation: close breaks the zone, or zone expired (older than macro_len candles)
	mySellZones = mySellZones.filter(_zone => {
		const myExpired = (myIndex - _zone.left) > myMacroLen;
		const myBroken = close[myIndex] > _zone.top;
		return !myExpired && !myBroken;
	});

	myBuyZones = myBuyZones.filter(_zone => {
		const myExpired = (myIndex - _zone.left) > myMacroLen;
		const myBroken = close[myIndex] < _zone.bottom;
		return !myExpired && !myBroken;
	});

	for (let mySlot = 0; mySlot < SLOTS; mySlot += 1) {
		if (mySellZones[mySlot]) {
			mySellTop[mySlot][myIndex] = mySellZones[mySlot].top;
			mySellBottom[mySlot][myIndex] = mySellZones[mySlot].bottom;
		}
		if (myBuyZones[mySlot]) {
			myBuyTop[mySlot][myIndex] = myBuyZones[mySlot].top;
			myBuyBottom[mySlot][myIndex] = myBuyZones[mySlot].bottom;
		}
	}

	mySellActiveSignal[myIndex] = mySellZones.length > 0;
	myBuyActiveSignal[myIndex] = myBuyZones.length > 0;
}

// paint sell zones (fixed 3 slots), each slot has a unique line name
for (let mySlot = 0; mySlot < SLOTS; mySlot += 1) {
	const mySlotNumber = mySlot + 1;
	const myTopLine = paint(mySellTop[mySlot], { name: `Sell Zone Top ${mySlotNumber}`, color: '#ff3b3b', style: 'ladder', thickness: 1 });
	const myBottomLine = paint(mySellBottom[mySlot], { name: `Sell Zone Bottom ${mySlotNumber}`, color: '#ff3b3b', style: 'ladder', thickness: 1 });
	fill(myTopLine, myBottomLine, '#ff3b3b', 0.15, `Sell Zone Fill ${mySlotNumber}`);

	const myLastSellActiveValue = mySellTop[mySlot][myCandleCount - 1];
	if (myLastSellActiveValue !== null) {
		paint_label_at_line(myTopLine, myCandleCount - 1, 'SELL ZONE', { color: '#ff3b3b', background_color: '#330000' });
	}
}

// paint buy zones (fixed 3 slots), each slot has a unique line name
for (let mySlot = 0; mySlot < SLOTS; mySlot += 1) {
	const mySlotNumber = mySlot + 1;
	const myTopLine = paint(myBuyTop[mySlot], { name: `Buy Zone Top ${mySlotNumber}`, color: '#2ecc71', style: 'ladder', thickness: 1 });
	const myBottomLine = paint(myBuyBottom[mySlot], { name: `Buy Zone Bottom ${mySlotNumber}`, color: '#2ecc71', style: 'ladder', thickness: 1 });
	fill(myTopLine, myBottomLine, '#2ecc71', 0.15, `Buy Zone Fill ${mySlotNumber}`);

	const myLastBuyActiveValue = myBuyTop[mySlot][myCandleCount - 1];
	if (myLastBuyActiveValue !== null) {
		paint_label_at_line(myTopLine, myCandleCount - 1, 'BUY ZONE', { color: '#2ecc71', background_color: '#003300' });
	}
}

register_signal(mySellActiveSignal, 'Sell Zone Active');
register_signal(myBuyActiveSignal, 'Buy Zone Active');
describe_indicator('Supply and Demand Zones ITA', 'price');

// ─── INPUTS ──────────────────────────────────────────────────────────────────
const myDetectionTab = input.tab('Detection');
const myPivotLen = myDetectionTab.number('Zone Pivot Strength', 8, { min: 2, max: 30 });
const myMaxZones = myDetectionTab.number('Max Zones Per Side', 6, { min: 1, max: 20 });
const myZoneWidth = myDetectionTab.select('Zone Height', 'Wick', ['Wick', 'Body']);
const myRemoveTest = myDetectionTab.boolean('Remove Zone After Retest', true);

const myStyleTab = input.tab('Style');
const mySupplyColor = myStyleTab.color('Supply Zone Color', '#f23645');
const myDemandColor = myStyleTab.color('Demand Zone Color', '#089981');

// ─── SOURCE SERIES FOR ZONE BOUNDARIES ──────────────────────────────────────
// "Wick" uses High/Low, "Body" uses max/min of Open/Close, matching the
// Pine f_top()/f_bot() helper functions.
const myTopSource = myZoneWidth === 'Wick' ? high : max_of(open, close);
const myBotSource = myZoneWidth === 'Wick' ? low : min_of(open, close);

// Pivot detection always uses High/Low, regardless of the Zone Height setting,
// exactly like ta.pivothigh(high, len, len) / ta.pivotlow(low, len, len).
const myPivotHighSeries = pivot_high(high, myPivotLen, myPivotLen);
const myPivotLowSeries = pivot_low(low, myPivotLen, myPivotLen);

const myCandleCount = close.length;

// Lines showing only the MOST RECENT active zone on each side (see note below).
const mySupplyTopLine = series_of(null);
const mySupplyBottomLine = series_of(null);
const myDemandTopLine = series_of(null);
const myDemandBottomLine = series_of(null);

// Signals (1 per candle) reproducing alertcondition(supplyTest) / (demandTest)
const mySupplyRetestSignal = series_of(false);
const myDemandRetestSignal = series_of(false);

let mySupplyZones = [];
let myDemandZones = [];

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	// --- create new zones on pivot bars ---
	if (myPivotHighSeries[myIndex] !== null) {
		mySupplyZones.push({
			top: myTopSource[myIndex],
			bot: myBotSource[myIndex],
			from: myIndex - myPivotLen
		});
		if (mySupplyZones.length > myMaxZones) {
			mySupplyZones.shift();
		}
	}

	if (myPivotLowSeries[myIndex] !== null) {
		myDemandZones.push({
			top: myTopSource[myIndex],
			bot: myBotSource[myIndex],
			from: myIndex - myPivotLen
		});
		if (myDemandZones.length > myMaxZones) {
			myDemandZones.shift();
		}
	}

	// --- snapshot the most recent zone for display, BEFORE retest removal
	//     (box.set_right happens before the retest check in the Pine script) ---
	if (mySupplyZones.length > 0) {
		const myLastSupply = mySupplyZones[mySupplyZones.length - 1];
		mySupplyTopLine[myIndex] = myLastSupply.top;
		mySupplyBottomLine[myIndex] = myLastSupply.bot;
	}

	if (myDemandZones.length > 0) {
		const myLastDemand = myDemandZones[myDemandZones.length - 1];
		myDemandTopLine[myIndex] = myLastDemand.top;
		myDemandBottomLine[myIndex] = myLastDemand.bot;
	}

	// --- retest check (mirrors the Pine "for i = size-1 to 0" loop) ---
	let mySupplyTouched = false;
	for (let myZoneIndex = mySupplyZones.length - 1; myZoneIndex >= 0; myZoneIndex -= 1) {
		const myZone = mySupplyZones[myZoneIndex];
		const myTouched = high[myIndex] >= myZone.bot && high[myIndex] <= myZone.top;
		if (myRemoveTest && myTouched) {
			mySupplyTouched = true;
			mySupplyZones.splice(myZoneIndex, 1);
		}
	}
	mySupplyRetestSignal[myIndex] = mySupplyTouched;

	let myDemandTouched = false;
	for (let myZoneIndex = myDemandZones.length - 1; myZoneIndex >= 0; myZoneIndex -= 1) {
		const myZone = myDemandZones[myZoneIndex];
		const myTouched = low[myIndex] <= myZone.top && low[myIndex] >= myZone.bot;
		if (myRemoveTest && myTouched) {
			myDemandTouched = true;
			myDemandZones.splice(myZoneIndex, 1);
		}
	}
	myDemandRetestSignal[myIndex] = myDemandTouched;
}

// ─── PAINTING ────────────────────────────────────────────────────────────────
const mySupplyTopPainted = paint(mySupplyTopLine, { style: 'ladder', color: mySupplyColor, name: 'SupplyTop' });
const mySupplyBottomPainted = paint(mySupplyBottomLine, { style: 'ladder', color: mySupplyColor, name: 'SupplyBottom' });
fill(mySupplyTopPainted, mySupplyBottomPainted, mySupplyColor, 0.18);

const myDemandTopPainted = paint(myDemandTopLine, { style: 'ladder', color: myDemandColor, name: 'DemandTop' });
const myDemandBottomPainted = paint(myDemandBottomLine, { style: 'ladder', color: myDemandColor, name: 'DemandBottom' });
fill(myDemandTopPainted, myDemandBottomPainted, myDemandColor, 0.18);

// Pivot markers (visual equivalent of the Pine zone creation labels)
const mySupplyMarker = for_every(myPivotHighSeries, _v => _v !== null ? constants.icons.triangle_down : null);
const myDemandMarker = for_every(myPivotLowSeries, _v => _v !== null ? constants.icons.triangle_up : null);
paint(mySupplyMarker, { style: 'labels_above', color: mySupplyColor, name: 'SupplyPivot' });
paint(myDemandMarker, { style: 'labels_below', color: myDemandColor, name: 'DemandPivot' });

// ─── SIGNALS (for Scanners, Alerts, Strategy Tester) ───────────────────────
register_signal(mySupplyRetestSignal, 'Supply Zone Retest');
register_signal(myDemandRetestSignal, 'Demand Zone Retest');
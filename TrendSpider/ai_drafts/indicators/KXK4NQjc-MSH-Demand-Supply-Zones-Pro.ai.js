describe_indicator('MSH Demand and Supply Zones Pro', 'price');

// NOTE: This indicator approximates the Pine Script's dynamic
// box/label drawing system (unlimited, independently tracked
// zones) using a fixed, constant number of painted lines, since
// the Custom JS API requires paint() to always run the same
// number of times regardless of inputs or data. Only the most
// recently formed, still-valid Demand zone and the most recently
// formed, still-valid Supply zone are drawn (proximal/distal
// rays). Zone formation (RBR/DBR/RBD/DBD) and zone violation are
// still fully detected and exposed as scanner/alert signals.

const myCandleTab = input.tab('Candle Rules');
const myLegInBodyPct = myCandleTab.number('Leg-in Min Body %', 50, { min: 1, max: 100 }) / 100;
const myLegOutBodyPct = myCandleTab.number('Leg-out Min Body %', 50, { min: 1, max: 100 }) / 100;
const myBaseBodyPct = myCandleTab.number('Base Max Body %', 50, { min: 1, max: 100 }) / 100;
const myMaxBaseCandles = myCandleTab.number('Max Base Candles', 3, { min: 1, max: 6 });

const myDisplayTab = input.tab('Display');
const myMaxZones = myDisplayTab.number('Max Active Zones To Track', 5, { min: 1, max: 20 });

const myMaTab = input.tab('Moving Averages');
const myShowEMAs = myMaTab.boolean('Show EMAs', true);
const myRapidEmaLength = myMaTab.number('Rapid EMA', 7, { min: 1, max: 200 });
const myFastEmaLength = myMaTab.number('Fast EMA', 21, { min: 1, max: 200 });

// EMAs (plotted on price axis, this is a price indicator)
const myEma7 = ema(close, myRapidEmaLength);
const myEma21 = ema(close, myFastEmaLength);
paint(myShowEMAs ? myEma7 : constants.empty_series, { name: 'EMA7', color: '#ffd54f', thickness: 2 });
paint(myShowEMAs ? myEma21 : constants.empty_series, { name: 'EMA21', color: '#ef5350', thickness: 2 });

const myN = close.length;

// Per-candle classification (matches candleRange / candleBody / isBase / isBullLeg / isBearLeg)
const myCandleRange = sub(high, low);
const myCandleBody = for_every(close, open, (_c, _o) => Math.abs(_c - _o));
const myIsBase = for_every(myCandleRange, myCandleBody, (_r, _b) => _r > 0 && (_b / _r) <= myBaseBodyPct);
const myIsBullLeg = for_every(myCandleRange, myCandleBody, open, close, (_r, _b, _o, _c) => _r > 0 && (_b / _r) >= myLegOutBodyPct && _c > _o);
const myIsBearLeg = for_every(myCandleRange, myCandleBody, open, close, (_r, _b, _o, _c) => _r > 0 && (_b / _r) >= myLegOutBodyPct && _c < _o);

// Output signal series
const myRbrSignal = series_of(false);
const myDbrSignal = series_of(false);
const myRbdSignal = series_of(false);
const myDbdSignal = series_of(false);
const myDemandViolatedSignal = series_of(false);
const mySupplyViolatedSignal = series_of(false);

// Output painted series for most-recent valid Demand/Supply zone
const myDemandProximal = series_of(null);
const myDemandDistal = series_of(null);
const mySupplyProximal = series_of(null);
const mySupplyDistal = series_of(null);

// Active zone tracking (plain JS state machine, allowed since it is
// sequential logic, not a loop calling indicator functions)
let myActiveZones = [];
let myCurrentDemandZone = null;
let myCurrentSupplyZone = null;

for (let myIndex = 2; myIndex < myN; myIndex += 1) {
	// Zone violation check & cleanup, mirrors the Pine "for" loop over activeZones
	if (myActiveZones.length > 0) {
		const myRemaining = [];
		for (const myZone of myActiveZones) {
			const myViolated = myZone.isDemand ? (close[myIndex] < myZone.distal) : (close[myIndex] > myZone.distal);
			if (myViolated) {
				if (myZone.isDemand) {
					myDemandViolatedSignal[myIndex] = true;
				}
				else {
					mySupplyViolatedSignal[myIndex] = true;
				}
				if (myCurrentDemandZone === myZone) {
					myCurrentDemandZone = null;
				}
				if (myCurrentSupplyZone === myZone) {
					myCurrentSupplyZone = null;
				}
			}
			else {
				myRemaining.push(myZone);
			}
		}

		// Keep the max active zones count within limits (oldest removed first)
		while (myRemaining.length > myMaxZones) {
			myRemaining.shift();
		}

		myActiveZones = myRemaining;
	}

	// Zone detection: base candle at [index-1], leg-out at [index], leg-in at [index-2]
	if (myIsBase[myIndex - 1]) {
		const myIsRallyOut = myIsBullLeg[myIndex];
		const myIsDropOut = myIsBearLeg[myIndex];
		const myIsRallyIn = myIsBullLeg[myIndex - 2];
		const myIsDropIn = myIsBearLeg[myIndex - 2];

		let myDetectedType = '';
		let myIsDemandZone = false;

		if (myIsRallyOut) {
			if (myIsRallyIn) {
				myDetectedType = 'RBR';
				myIsDemandZone = true;
			}
			else if (myIsDropIn) {
				myDetectedType = 'DBR';
				myIsDemandZone = true;
			}
		}
		else if (myIsDropOut) {
			if (myIsRallyIn) {
				myDetectedType = 'RBD';
				myIsDemandZone = false;
			}
			else if (myIsDropIn) {
				myDetectedType = 'DBD';
				myIsDemandZone = false;
			}
		}

		if (myDetectedType !== '') {
			const myProx = myIsDemandZone
				? Math.max(open[myIndex - 1], close[myIndex - 1])
				: Math.min(open[myIndex - 1], close[myIndex - 1]);
			const myDist = myIsDemandZone ? low[myIndex - 1] : high[myIndex - 1];

			const myNewZone = {
				proximal: myProx,
				distal: myDist,
				isDemand: myIsDemandZone,
				zoneType: myDetectedType
			};

			myActiveZones.push(myNewZone);

			if (myDetectedType === 'RBR') { myRbrSignal[myIndex] = true; }
			else if (myDetectedType === 'DBR') { myDbrSignal[myIndex] = true; }
			else if (myDetectedType === 'RBD') { myRbdSignal[myIndex] = true; }
			else if (myDetectedType === 'DBD') { myDbdSignal[myIndex] = true; }

			if (myIsDemandZone) {
				myCurrentDemandZone = myNewZone;
			}
			else {
				myCurrentSupplyZone = myNewZone;
			}
		}
	}

	if (myCurrentDemandZone) {
		myDemandProximal[myIndex] = myCurrentDemandZone.proximal;
		myDemandDistal[myIndex] = myCurrentDemandZone.distal;
	}
	if (myCurrentSupplyZone) {
		mySupplyProximal[myIndex] = myCurrentSupplyZone.proximal;
		mySupplyDistal[myIndex] = myCurrentSupplyZone.distal;
	}
}

// Paint the most recent Demand zone (proximal/distal) and fill between them
fill(
	paint(myDemandProximal, { name: 'DemandProximal', color: '#2e7d32', style: 'ladder' }),
	paint(myDemandDistal, { name: 'DemandDistal', color: '#2e7d32', style: 'ladder' }),
	'#2e7d32',
	0.2
);

// Paint the most recent Supply zone (proximal/distal) and fill between them
fill(
	paint(mySupplyProximal, { name: 'SupplyProximal', color: '#c62828', style: 'ladder' }),
	paint(mySupplyDistal, { name: 'SupplyDistal', color: '#c62828', style: 'ladder' }),
	'#c62828',
	0.2
);

register_signal(myRbrSignal, 'RBR Zone Formed');
register_signal(myDbrSignal, 'DBR Zone Formed');
register_signal(myRbdSignal, 'RBD Zone Formed');
register_signal(myDbdSignal, 'DBD Zone Formed');
register_signal(myDemandViolatedSignal, 'Demand Zone Violated');
register_signal(mySupplyViolatedSignal, 'Supply Zone Violated');
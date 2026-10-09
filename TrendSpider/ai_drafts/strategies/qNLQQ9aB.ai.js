describe_indicator('ZigZag Elliott Wave Strategy (Demo)', 'price');

// ===================================================
// INPUTS
// ===================================================
const myZigzagLen   = input.number('ZigZag Length', 12, { min: 3 });
const myFibRetrMin  = input.number('Wave 2 Min Retracement', 0.50, { min: 0, max: 2 });
const myFibRetrMax  = input.number('Wave 2 Max Retracement', 0.618, { min: 0, max: 2 });
const myFibWave3Ext = input.number('Wave 3 Extension', 1.618, { min: 0, max: 5 });
const myFibWave4Min = input.number('Wave 4 Min Retracement', 0.382, { min: 0, max: 2 });
const myFibWave4Max = input.number('Wave 4 Max Retracement', 0.50, { min: 0, max: 2 });
const myPartialTP   = input.number('Wave 5 Partial Close (%)', 0.90, { min: 0, max: 2 });

// ===================================================
// ZIGZAG CALCULATION
// Pine's ta.pivothigh/pivotlow with equal left/right length
// map directly to pivot_high()/pivot_low()
// ===================================================
const myPivotHigh = pivot_high(high, myZigzagLen, myZigzagLen);
const myPivotLow  = pivot_low(low, myZigzagLen, myZigzagLen);

const myN = close.length;

// state series, replicating Pine's "var" persistent variables
const myLastLow   = series_of(null);
const myLastHigh  = series_of(null);
const myWave1Low  = series_of(null);
const myWave1High = series_of(null);

const myFib50       = series_of(null);
const myFib618      = series_of(null);
const myWave3Target = series_of(null);
const myWave4FibMin = series_of(null);
const myWave4FibMax = series_of(null);

const myWave2Zone = series_of(false);
const myWave4Zone = series_of(false);
const myPartialClosePrice = series_of(null);

const myLongEntrySignal   = series_of(false);
const myWave4AddSignal    = series_of(false);
const myPartialTPSignal   = series_of(false);
const myFullExitSignal    = series_of(false);

let myCurrentLastLow = null;
let myCurrentLastHigh = null;
let myCurrentWave1Low = null;
let myCurrentWave1High = null;

// Approximation of strategy.position_size, since this is not a real
// strategy backtest engine, just a signal mapper. We track a simple
// simulated position flag to approximate Pine's position state logic.
let mySimulatedInPosition = false;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	if (myPivotLow[myIndex] !== null && myPivotLow[myIndex] !== undefined) {
		myCurrentLastLow = myPivotLow[myIndex];
	}
	if (myPivotHigh[myIndex] !== null && myPivotHigh[myIndex] !== undefined) {
		myCurrentLastHigh = myPivotHigh[myIndex];
	}

	const myWave1Valid = myCurrentLastLow !== null && myCurrentLastHigh !== null && myCurrentLastHigh > myCurrentLastLow;

	if (myWave1Valid) {
		myCurrentWave1Low = myCurrentLastLow;
		myCurrentWave1High = myCurrentLastHigh;
	}

	myLastLow[myIndex] = myCurrentLastLow;
	myLastHigh[myIndex] = myCurrentLastHigh;
	myWave1Low[myIndex] = myCurrentWave1Low;
	myWave1High[myIndex] = myCurrentWave1High;

	if (myCurrentWave1Low !== null && myCurrentWave1High !== null) {
		const myWave1Range = myCurrentWave1High - myCurrentWave1Low;

		const myFib50Value = myCurrentWave1High - myWave1Range * myFibRetrMin;
		const myFib618Value = myCurrentWave1High - myWave1Range * myFibRetrMax;

		myFib50[myIndex] = myFib50Value;
		myFib618[myIndex] = myFib618Value;

		const myWave2ZoneValue = close[myIndex] <= myFib50Value && close[myIndex] >= myFib618Value;
		myWave2Zone[myIndex] = myWave2ZoneValue;

		const myWave3TargetValue = myCurrentWave1Low + myWave1Range * myFibWave3Ext;
		myWave3Target[myIndex] = myWave3TargetValue;

		const myWave4FibMinValue = myWave3TargetValue - myWave1Range * myFibWave4Min;
		const myWave4FibMaxValue = myWave3TargetValue - myWave1Range * myFibWave4Max;
		myWave4FibMin[myIndex] = myWave4FibMinValue;
		myWave4FibMax[myIndex] = myWave4FibMaxValue;

		const myWave4ZoneValue = close[myIndex] <= myWave4FibMinValue && close[myIndex] >= myWave4FibMaxValue;
		myWave4Zone[myIndex] = myWave4ZoneValue;

		const myPartialClosePriceValue = myWave3TargetValue * myPartialTP;
		myPartialClosePrice[myIndex] = myPartialClosePriceValue;

		// Long entry on Wave 2 end, only if simulated flat (approximates strategy.position_size == 0)
		if (myWave2ZoneValue && !mySimulatedInPosition) {
			myLongEntrySignal[myIndex] = true;
			mySimulatedInPosition = true;
		}

		// Wave 4 add, only if simulated in position (approximates strategy.position_size > 0)
		if (myWave4ZoneValue && mySimulatedInPosition) {
			myWave4AddSignal[myIndex] = true;
		}

		// Partial take profit
		if (close[myIndex] >= myPartialClosePriceValue && mySimulatedInPosition) {
			myPartialTPSignal[myIndex] = true;
		}

		// Full exit at wave 3 extension
		if (close[myIndex] >= myWave3TargetValue) {
			myFullExitSignal[myIndex] = true;
			mySimulatedInPosition = false;
		}
	}
}

// ===================================================
// VISUALS
// ===================================================
paint(myWave1High, { name: 'Wave1High', color: '#2ca599', style: 'dotted', thickness: 3 });
paint(myWave1Low, { name: 'Wave1Low', color: '#ee5451', style: 'dotted', thickness: 3 });
paint(myWave3Target, { name: 'Wave3Target', color: '#ff9800', style: 'line', thickness: 2 });
paint(myFib50, { name: 'Fib50', color: '#2962ff', style: 'line', thickness: 1 });
paint(myFib618, { name: 'Fib618', color: '#9c27b0', style: 'line', thickness: 1 });

// Approximation of Pine's bgcolor(): using candle coloring instead,
// since this engine has no background-zone painting primitive.
const myZoneColors = for_every(
	series_of(0),
	(_z, _p, myCandleIndex) => {
		if (myWave2Zone[myCandleIndex]) return 'rgba(76,175,80,0.25)';
		if (myWave4Zone[myCandleIndex]) return 'rgba(255,152,0,0.25)';
		return null;
	}
);
color_candles(myZoneColors);

// ===================================================
// SIGNALS (for Scanner / Alerts / Strategy Tester)
// ===================================================
register_signal(myLongEntrySignal, 'Wave 3 Long Entry');
register_signal(myWave4AddSignal, 'Wave 4 Add Entry');
register_signal(myPartialTPSignal, 'Wave 5 Partial Take Profit');
register_signal(myFullExitSignal, 'Full Exit At Wave 3 Target');
describe_indicator('LL Momentum and Curl Master', 'price');

// NOTE: This is a conversion of a Pine Script *strategy* into an
// indicator. TrendSpider custom indicators cannot place real broker
// orders or run strategy.entry/strategy.exit logic; instead this
// script simulates the same state machine (position, stop, target)
// bar-by-bar in plain JavaScript, reproducing the same trigger bars
// as the Pine script would generate. The Pine `table` dashboard is
// reproduced as a small overlay table.

const myTrendTab = input.tab('Trend Filter');
const myUseTrendFilter = myTrendTab.boolean('Enable 200 EMA Trend Guardrail', true);
const myEmaLength = myTrendTab.number('Macro Trend EMA Length', 200, { min: 1, max: 1000 });

const myRiskTab = input.tab('Risk Management');
const myAtrLength = myRiskTab.number('ATR Length', 14, { min: 1, max: 200 });
const myRiskRow = myRiskTab.row();
const myLongStopMult = myRiskRow.number('Long Stop ATR Mult', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myShortStopMult = myRiskRow.number('Short Stop ATR Mult', 1.5, { min: 0.1, max: 20, step: 0.1 });

// --- Technical calculations (computed outside loops, as required) ---
const myMacroEma = ema(close, myEmaLength);
const myAtr = atr(high, low, close, myAtrLength);
const myMom20 = momentum(close, 20);
const mySma50 = sma(close, 50);
const mySma50Change = sub(mySma50, shift(mySma50, 1));
const myVolAverage = sma(volume, 20);

const myBaseLongSignal = for_every(myMom20, mySma50Change, (_m, _s) => _m > 0 && _s > 0);
const myBaseShortSignal = for_every(myMom20, mySma50Change, (_m, _s) => _m < 0 && _s < 0);
const myVolumeFilter = for_every(volume, myVolAverage, (_v, _a) => _v > (_a * 1.2));

const myLongCondition = myUseTrendFilter
	? for_every(myBaseLongSignal, close, myMacroEma, myVolumeFilter, (_b, _c, _e, _vf) => _b && _c > _e && _vf)
	: for_every(myBaseLongSignal, myVolumeFilter, (_b, _vf) => _b && _vf);

const myShortCondition = myUseTrendFilter
	? for_every(myBaseShortSignal, close, myMacroEma, myVolumeFilter, (_b, _c, _e, _vf) => _b && _c < _e && _vf)
	: for_every(myBaseShortSignal, myVolumeFilter, (_b, _vf) => _b && _vf);

// --- State machine simulating strategy entries/exits ---
const myCandleCount = close.length;
const myLongTriggered = series_of(false);
const myShortTriggered = series_of(false);
const myExitLong = series_of(false);
const myExitShort = series_of(false);

let myPosition = 0;
let myStopPrice = 0;
let myLimitPrice = 0;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (myPosition === 0) {
		if (myLongCondition[myIndex]) {
			myPosition = 1;
			myStopPrice = low[myIndex] - (myAtr[myIndex] * myLongStopMult);
			myLimitPrice = close[myIndex] + (myAtr[myIndex] * (myLongStopMult * 2));
			myLongTriggered[myIndex] = true;
		}
		else if (myShortCondition[myIndex]) {
			myPosition = -1;
			myStopPrice = high[myIndex] + (myAtr[myIndex] * myShortStopMult);
			myLimitPrice = close[myIndex] - (myAtr[myIndex] * (myShortStopMult * 2));
			myShortTriggered[myIndex] = true;
		}
	}
	else if (myPosition === 1) {
		if (low[myIndex] <= myStopPrice || high[myIndex] >= myLimitPrice) {
			myExitLong[myIndex] = true;
			myPosition = 0;
		}
	}
	else if (myPosition === -1) {
		if (high[myIndex] >= myStopPrice || low[myIndex] <= myLimitPrice) {
			myExitShort[myIndex] = true;
			myPosition = 0;
		}
	}
}

// --- Visuals ---
paint(myMacroEma, { name: 'Macro Trend EMA', color: '#2962FF', thickness: 2 });

const myCallMarks = for_every(myLongTriggered, _t => _t ? constants.icons.triangle_up : null);
const myPutMarks = for_every(myShortTriggered, _t => _t ? constants.icons.triangle_down : null);

paint(myCallMarks, { style: 'labels_below', color: '#00ffbb', name: 'Call Label' });
paint(myPutMarks, { style: 'labels_above', color: '#ff4488', name: 'Put Label' });

// --- Dashboard overlay, mirrors the Pine table ---
// myIsBullishSeries is a full series (one boolean per candle), computed
// with for_every, so it can be used both for the overlay (last value)
// and for register_signal (which requires an actual series, not a
// single scalar boolean).
const myIsBullishSeries = for_every(close, myMacroEma, (_c, _e) => _c > _e);
const myIsBullish = myIsBullishSeries.at(-1);

paint_overlay('LLEngineStatus', { position: 'top_right' }, {
	rows: [{
		cells: [
			{ text: 'LL Engine Status', color: 'white', background_color: 'gray' },
			{ text: 'Current State', color: 'white', background_color: 'gray' }
		]
	}, {
		cells: [
			{ text: 'Macro Trend Guard', color: 'white' },
			{ text: myIsBullish ? 'BULLISH' : 'BEARISH', color: myIsBullish ? '#26A69A' : '#EF5350' }
		]
	}]
});

// --- Scanner / Alert / Strategy tester signals ---
register_signal(myLongTriggered, 'Long Entry');
register_signal(myShortTriggered, 'Short Entry');
register_signal(myExitLong, 'Long Exit');
register_signal(myExitShort, 'Short Exit');
register_signal(myIsBullishSeries, 'Macro Trend Bullish');
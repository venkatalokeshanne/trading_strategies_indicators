describe_indicator('RSI Exact Divergence Strategy', 'lower');

// ===================== Inputs =====================
const rsiTab = input.tab('RSI Settings');
const myRsiLength = rsiTab.number('RSI Length', 14, { min: 1, max: 200 });
const myPivotLookback = rsiTab.number('Pivot Lookback Period', 5, { min: 1, max: 50 });
const myMaxLookback = rsiTab.number('Max Lookback for Divergence', 60, { min: 10, max: 500 });
const myObLevel = rsiTab.number('Overbought Level', 70, { min: 50, max: 100 });
const myOsLevel = rsiTab.number('Oversold Level', 30, { min: 0, max: 50 });

const htfTab = input.tab('HTF Trend Filter');
const myUseHtfFilter = htfTab.boolean('Enable HTF Filter', true);
const myHtfResolution = htfTab.select('HTF Timeframe', 'D', constants.time_frames);
const myHtfEmaLength = htfTab.number('HTF EMA Length', 200, { min: 1, max: 500 });

// ===================== RSI =====================
const myRsiValue = rsi(close, myRsiLength);

// ===================== HTF Trend Filter =====================
// Uses the previous completed HTF bar's close vs EMA(close), as in the
// original Pine script (close[1] vs ema[1] on the HTF resolution).
const myHtfData = await request.history(current.ticker, myHtfResolution);
assert(!myHtfData.error, "Error fetching HTF data: " + myHtfData.error);

const myHtfEmaRaw = ema(myHtfData.close, myHtfEmaLength);
const myHtfEmaPrev = shift(myHtfEmaRaw, 1);
const myHtfClosePrev = shift(myHtfData.close, 1);

const myHtfEmaLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfEmaPrev, time, 'le'),
	'constant'
);
const myHtfCloseLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfClosePrev, time, 'le'),
	'constant'
);

const myHtfTrendUp = for_every(myHtfCloseLanded, myHtfEmaLanded, (_c, _e) => !myUseHtfFilter || (_c > _e));
const myHtfTrendDown = for_every(myHtfCloseLanded, myHtfEmaLanded, (_c, _e) => !myUseHtfFilter || (_c < _e));

// ===================== Pivot Points on RSI =====================
// pivot_high/pivot_low place the pivot value AT the pivot candle itself.
// In Pine, the divergence check happens on the "confirmation" bar, which is
// pivotLookback bars AFTER the pivot bar. We replicate that offset below.
const myPvHi = pivot_high(myRsiValue, myPivotLookback, myPivotLookback);
const myPvLo = pivot_low(myRsiValue, myPivotLookback, myPivotLookback);

const myN = close.length;
const myBearDiv = series_of(false);
const myBullDiv = series_of(false);
const myBearDivRsi = series_of(null);
const myBullDivRsi = series_of(null);

let myTopRsi = null, myTopBar = null, myTopPrice = null;
let myPrevTopRsi = null, myPrevTopBar = null, myPrevTopPrice = null;
let myBotRsi = null, myBotBar = null, myBotPrice = null;
let myPrevBotRsi = null, myPrevBotBar = null, myPrevBotPrice = null;

// Build maps of "confirmation index" -> pivot bar data
const myTopEvents = {};
const myBotEvents = {};

for (let myI = 0; myI < myN; myI += 1) {
	if (myPvHi[myI] !== null) {
		const myConfirmIndex = myI + myPivotLookback;
		if (myConfirmIndex < myN) {
			myTopEvents[myConfirmIndex] = { rsi: myRsiValue[myI], bar: myI, price: high[myI] };
		}
	}
	if (myPvLo[myI] !== null) {
		const myConfirmIndex = myI + myPivotLookback;
		if (myConfirmIndex < myN) {
			myBotEvents[myConfirmIndex] = { rsi: myRsiValue[myI], bar: myI, price: low[myI] };
		}
	}
}

for (let myIdx = 0; myIdx < myN; myIdx += 1) {
	if (myTopEvents[myIdx]) {
		myPrevTopRsi = myTopRsi;
		myPrevTopBar = myTopBar;
		myPrevTopPrice = myTopPrice;

		myTopRsi = myTopEvents[myIdx].rsi;
		myTopBar = myTopEvents[myIdx].bar;
		myTopPrice = myTopEvents[myIdx].price;

		const myValidLookback = myPrevTopBar !== null && (myTopBar - myPrevTopBar) <= myMaxLookback;

		if (myValidLookback) {
			const myPriceHigherHigh = myTopPrice > myPrevTopPrice;
			const myRsiLowerHigh = myTopRsi < myPrevTopRsi;
			const myInOrLeavingOb = (myPrevTopRsi >= myObLevel) || (myTopRsi >= myObLevel);

			if (myPriceHigherHigh && myRsiLowerHigh && myInOrLeavingOb) {
				myBearDiv[myIdx] = true;
				myBearDivRsi[myIdx] = myTopRsi;
			}
		}
	}

	if (myBotEvents[myIdx]) {
		myPrevBotRsi = myBotRsi;
		myPrevBotBar = myBotBar;
		myPrevBotPrice = myBotPrice;

		myBotRsi = myBotEvents[myIdx].rsi;
		myBotBar = myBotEvents[myIdx].bar;
		myBotPrice = myBotEvents[myIdx].price;

		const myValidLookback = myPrevBotBar !== null && (myBotBar - myPrevBotBar) <= myMaxLookback;

		if (myValidLookback) {
			const myPriceLowerLow = myBotPrice < myPrevBotPrice;
			const myRsiHigherLow = myBotRsi > myPrevBotRsi;
			const myInOrLeavingOs = (myPrevBotRsi <= myOsLevel) || (myBotRsi <= myOsLevel);

			if (myPriceLowerLow && myRsiHigherLow && myInOrLeavingOs) {
				myBullDiv[myIdx] = true;
				myBullDivRsi[myIdx] = myBotRsi;
			}
		}
	}
}

// ===================== Strategy Signals =====================
const myBuySignal = for_every(series_of(0), (_z, _p, _idx) => myBullDiv[_idx] && myHtfTrendUp[_idx]);
const mySellSignal = for_every(series_of(0), (_z, _p, _idx) => myBearDiv[_idx] && myHtfTrendDown[_idx]);

// position tracking to know when to exit, mirroring strategy.position_size
let myPosition = 0; // 1 long, -1 short, 0 flat
const myExitLong = series_of(false);
const myExitShort = series_of(false);

for (let myIdx = 0; myIdx < myN; myIdx += 1) {
	if (myBuySignal[myIdx]) myPosition = 1;
	if (mySellSignal[myIdx]) myPosition = -1;

	if (myBearDiv[myIdx] && myPosition > 0) {
		myExitLong[myIdx] = true;
		myPosition = 0;
	}
	if (myBullDiv[myIdx] && myPosition < 0) {
		myExitShort[myIdx] = true;
		myPosition = 0;
	}
}

// ===================== Painting =====================
paint(myRsiValue, { name: 'RSI', color: '#9b59b6', thickness: 2 });
paint(horizontal_line(myObLevel), { name: 'Overbought', color: '#e74c3c', style: 'dotted' });
paint(horizontal_line(55), { name: 'Upper Equilibrium', color: 'gray', style: 'dotted' });
paint(horizontal_line(50), { name: 'Middle Line', color: 'gray', style: 'dotted' });
paint(horizontal_line(45), { name: 'Lower Equilibrium', color: 'gray', style: 'dotted' });
paint(horizontal_line(myOsLevel), { name: 'Oversold', color: '#2ecc71', style: 'dotted' });

fill(
	paint(horizontal_line(55), { name: 'Equilibrium Upper Border', hidden: true }),
	paint(horizontal_line(45), { name: 'Equilibrium Lower Border', hidden: true }),
	'blue', 0.08
);

fill(
	paint(horizontal_line(myObLevel), { name: 'Upper Shade Border', hidden: true }),
	paint(horizontal_line(50), { name: 'Upper Shade Mid', hidden: true }),
	'red', 0.05
);

fill(
	paint(horizontal_line(myOsLevel), { name: 'Lower Shade Border', hidden: true }),
	paint(horizontal_line(50), { name: 'Lower Shade Mid', hidden: true }),
	'green', 0.05
);

paint(myBearDivRsi, { name: 'Bearish Divergence', style: 'labels_above', color: '#e74c3c' });
paint(myBullDivRsi, { name: 'Bullish Divergence', style: 'labels_below', color: '#2ecc71' });

// Price axis markers approximating force_overlay plotshapes from Pine
const myBuyPriceMark = for_every(series_of(0), (_z, _p, _idx) => myBuySignal[_idx] ? low[_idx] : null);
const mySellPriceMark = for_every(series_of(0), (_z, _p, _idx) => mySellSignal[_idx] ? high[_idx] : null);

paint(myBuyPriceMark, { name: 'Buy Marker', style: 'labels_below', color: '#2ecc71', forceUsePriceAxis: true });
paint(mySellPriceMark, { name: 'Sell Marker', style: 'labels_above', color: '#e74c3c', forceUsePriceAxis: true });

// ===================== Signals for Scanner/Alerts/Strategy =====================
// Signal names must be alphanumeric (no spaces/punctuation), renamed to
// avoid collisions with the paint() line names above and to satisfy the
// alphanumeric-only naming requirement for register_signal().
register_signal(myBuySignal, 'BuySignal');
register_signal(mySellSignal, 'SellSignal');
register_signal(myBearDiv, 'BearishDivergenceSignal');
register_signal(myBullDiv, 'BullishDivergenceSignal');
register_signal(myExitLong, 'ExitLong');
register_signal(myExitShort, 'ExitShort');
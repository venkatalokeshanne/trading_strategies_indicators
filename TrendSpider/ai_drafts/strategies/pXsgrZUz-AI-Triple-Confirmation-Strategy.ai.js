describe_indicator('AI Triple Confirmation Strategy', 'price');

// ===== Inputs =====
const myTab = input.tab('Settings');
const myTrendGroup = myTab.group('Trend (EMA)');
const myTrendRow = myTrendGroup.row();
const myEmaFastLen = myTrendRow.number('Fast EMA', 50, { min: 1, max: 500 });
const myEmaSlowLen = myTrendRow.number('Slow EMA', 200, { min: 1, max: 1000 });
const myMomentumGroup = myTab.group('Momentum (RSI)');
const myMomentumRow = myMomentumGroup.row();
const myRsiLen = myMomentumRow.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiBuy = myMomentumRow.number('RSI Buy Level', 55, { min: 1, max: 99 });
const myRsiSell = myMomentumRow.number('RSI Sell Level', 45, { min: 1, max: 99 });
const myAtrGroup = myTab.group('ATR / Risk');
const myAtrRow = myAtrGroup.row();
const myAtrLen = myAtrRow.number('ATR Length', 14, { min: 1, max: 200 });
const myRiskReward = myAtrRow.number('Risk Reward Ratio', 3.0, { min: 0.1, max: 20 });
const myStructureGroup = myTab.group('Market Structure');
const mySwingLen = myStructureGroup.number('Swing Length', 5, { min: 1, max: 100 });

// ===== Trend confirmation (EMA) =====
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);
const myBullTrend = for_every(myEmaFast, myEmaSlow, (_f, _s) => _f > _s);
const myBearTrend = for_every(myEmaFast, myEmaSlow, (_f, _s) => _f < _s);

// ===== Momentum confirmation (RSI) =====
const myRsi = rsi(close, myRsiLen);
const myBullRsi = for_every(myRsi, _r => _r > myRsiBuy);
const myBearRsi = for_every(myRsi, _r => _r < myRsiSell);

// ===== Market structure confirmation (BOS) =====
// Pivot high/low with left=right=swingLen is equivalent to Pine's ta.pivothigh/pivotlow
const myPivotHigh = pivot_high(high, mySwingLen, mySwingLen);
const myPivotLow = pivot_low(low, mySwingLen, mySwingLen);

// carry forward last known pivot value (var float lastHigh/lastLow in Pine)
const myLastHigh = for_every(myPivotHigh, (_ph, _prev) => (_ph !== null && _ph !== undefined) ? _ph : (_prev === undefined ? null : _prev));
const myLastLow = for_every(myPivotLow, (_pl, _prev) => (_pl !== null && _pl !== undefined) ? _pl : (_prev === undefined ? null : _prev));

// crossover(close, lastHigh) / crossunder(close, lastLow), replicated manually
// using close & lastHigh/lastLow with index-based lookback since for_every
// callbacks don't give access to "previous input" values directly.
const myBullBOS = series_of(false);
const myBearBOS = series_of(false);
for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myPrevClose = close[myIndex - 1];
	const myCurrClose = close[myIndex];
	const myPrevHigh = myLastHigh[myIndex - 1];
	const myCurrHigh = myLastHigh[myIndex];
	const myPrevLow = myLastLow[myIndex - 1];
	const myCurrLow = myLastLow[myIndex];

	myBullBOS[myIndex] = (myPrevHigh !== null && myCurrHigh !== null) &&
		(myPrevClose <= myPrevHigh) && (myCurrClose > myCurrHigh);
	myBearBOS[myIndex] = (myPrevLow !== null && myCurrLow !== null) &&
		(myPrevClose >= myPrevLow) && (myCurrClose < myCurrLow);
}

// ===== Final confirmation =====
const myBuySignal = for_every(myBullTrend, myBullRsi, myBullBOS, (_t, _r, _b) => _t && _r && _b);
const mySellSignal = for_every(myBearTrend, myBearRsi, myBearBOS, (_t, _r, _b) => _t && _r && _b);

// ===== ATR stop loss / take profit =====
const myAtr = atr(high, low, close, myAtrLen);
const myBuySL = sub(close, myAtr);
const myBuyTP = add(close, mult(myAtr, myRiskReward));
const mySellSL = add(close, myAtr);
const mySellTP = sub(close, mult(myAtr, myRiskReward));

// ===== Position state simulation (approximation of strategy.position_size) =====
// Pine's strategy holds a position until the opposite TP/SL level is hit intrabar.
// This JS indicator cannot execute an actual backtest engine, so position state
// here is approximated as "stay long/short until the opposite signal fires",
// which is NOT identical to Pine's actual TP/SL based exits.
const myPositionState = series_of(0);
for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevState = myIndex > 0 ? myPositionState[myIndex - 1] : 0;

	if (myBuySignal[myIndex]) {
		myPositionState[myIndex] = 1;
	}
	else if (mySellSignal[myIndex]) {
		myPositionState[myIndex] = -1;
	}
	else {
		myPositionState[myIndex] = myPrevState;
	}
}

const myBuyTpLine = for_every(myPositionState, myBuyTP, (_pos, _tp) => _pos > 0 ? _tp : null);
const myBuySlLine = for_every(myPositionState, myBuySL, (_pos, _sl) => _pos > 0 ? _sl : null);
const mySellTpLine = for_every(myPositionState, mySellTP, (_pos, _tp) => _pos < 0 ? _tp : null);
const mySellSlLine = for_every(myPositionState, mySellSL, (_pos, _sl) => _pos < 0 ? _sl : null);

// ===== Visuals =====
paint(myEmaFast, { name: 'EMA Fast', color: '#26A69A', thickness: 2 });
paint(myEmaSlow, { name: 'EMA Slow', color: '#EF5350', thickness: 2 });

const myBuyMarks = for_every(myBuySignal, _b => _b ? 1 : null);
const mySellMarks = for_every(mySellSignal, _s => _s ? 1 : null);
// Renamed the painted marker lines so their names no longer collide
// with the register_signal() output names below (names must be unique
// across paint() and register_signal() calls).
paint(myBuyMarks, { name: 'Buy Marker', style: 'labels_below', color: '#26A69A' });
paint(mySellMarks, { name: 'Sell Marker', style: 'labels_above', color: '#EF5350' });
paint(myBuyTpLine, { name: 'Buy Take Profit', color: '#26A69A', style: 'line' });
paint(myBuySlLine, { name: 'Buy Stop Loss', color: '#EF5350', style: 'line' });
paint(mySellTpLine, { name: 'Sell Take Profit', color: '#26A69A', style: 'line' });
paint(mySellSlLine, { name: 'Sell Stop Loss', color: '#EF5350', style: 'line' });

// ===== Signals for scanners, alerts and strategy tester =====
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
register_signal(myBullTrend, 'Bull Trend');
register_signal(myBearTrend, 'Bear Trend');
register_signal(myBullBOS, 'Bullish Break Of Structure');
register_signal(myBearBOS, 'Bearish Break Of Structure');
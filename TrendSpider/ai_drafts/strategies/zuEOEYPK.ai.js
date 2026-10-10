describe_indicator('BTC 4H Trend v4 LongOnly (converted)', 'price');

// ─── Inputs, mirroring the Pine groups ─────────────────────
const emaTab = input.tab('EMA Settings');
const emaFastL = emaTab.number('Fast EMA', 21, { min: 1, max: 500 });
const emaSlowL = emaTab.number('Slow EMA', 55, { min: 1, max: 500 });
const emaTrendL = emaTab.number('Trend EMA', 200, { min: 1, max: 1000 });

const rsiTab = input.tab('RSI Settings');
const rsiLen = rsiTab.number('RSI Length', 14, { min: 1, max: 200 });
const rsiOB = rsiTab.number('RSI Overbought', 70, { min: 1, max: 99 });

const riskTab = input.tab('Risk Settings');
const atrLen = riskTab.number('ATR Length', 14, { min: 1, max: 200 });
const atrSLMul = riskTab.number('SL Multiplier', 1.5, { min: 0.1, max: 20 });
const atrTPMul = riskTab.number('TP Multiplier', 3.0, { min: 0.1, max: 20 });
const trailMul = riskTab.number('Trail ATR Multiplier', 1.5, { min: 0.1, max: 20 });

const filterTab = input.tab('Filters');
const useTrend = filterTab.boolean('Trend Filter EMA200', true);
const useShort = filterTab.boolean('Enable Short recommended OFF', false);

// ─── Core calculations ──────────────────────────────────────
const myEmaFast = ema(close, emaFastL);
const myEmaSlow = ema(close, emaSlowL);
const myEmaTrend = ema(close, emaTrendL);
const myRsi = rsi(close, rsiLen);
const myAtr = atr(high, low, close, atrLen);

const myEmaFastPrev = shift(myEmaFast, 1);
const myEmaSlowPrev = shift(myEmaSlow, 1);
const myClosePrev = shift(close, 1);
const myEmaTrendPrev3 = shift(myEmaTrend, 3);

// bull/bear trend filter
const myBull = for_every(close, myEmaTrend, (_c, _t) => (!useTrend || _c > _t));
const myBear = for_every(close, myEmaTrend, (_c, _t) => (!useTrend || _c < _t));
const myTrendUp = for_every(myEmaTrend, myEmaTrendPrev3, (_t, _tp3) => _t > _tp3);
const myTrendDown = for_every(myEmaTrend, myEmaTrendPrev3, (_t, _tp3) => _t < _tp3);

// crossover / crossunder of fast vs slow EMA
const myLongCross = for_every(myEmaFast, myEmaSlow, myEmaFastPrev, myEmaSlowPrev,
	(_f, _s, _pf, _ps) => _f > _s && _pf <= _ps);
const myShortCross = for_every(myEmaFast, myEmaSlow, myEmaFastPrev, myEmaSlowPrev,
	(_f, _s, _pf, _ps) => _f < _s && _pf >= _ps);

const myLongPull = for_every(myEmaFast, myEmaSlow, close, myClosePrev,
	(_f, _s, _c, _pc) => _f > _s && _c > _f && _pc < _f);
const myShortPull = for_every(myEmaFast, myEmaSlow, close, myClosePrev,
	(_f, _s, _c, _pc) => _f < _s && _c < _f && _pc > _f);

// ─── Sequential simulation of strategy.position_size behavior ───
// NOTE: Pine's strategy.exit() mixes a hard stop, a limit, and a
// trailing stop (trail_points/trail_offset) simultaneously. This is
// approximated below with a sequential bar-by-bar simulation since
// the Custom JS engine has no native strategy/backtest engine.
const myLongEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myShortExitSignal = series_of(false);
const myPositionState = series_of(0); // 1 = long, -1 = short, 0 = flat

let myPosition = 0;
let myEntryPrice = null;
let myStopPrice = null;
let myLimitPrice = null;
let myTrailStop = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myAtrValue = myAtr[myIndex] || 0;
	const mySL = myAtrValue * atrSLMul;
	const myTP = myAtrValue * atrTPMul;
	const myTrail = myAtrValue * trailMul;

	let myDidExitThisBar = false;

	if (myPosition === 1) {
		// update trailing stop (long): ratchets up with new highs
		const myCandidateTrail = high[myIndex] - myTrail;
		if (myTrailStop === null || myCandidateTrail > myTrailStop) {
			myTrailStop = myCandidateTrail;
		}
		const myEffectiveStop = Math.max(myStopPrice, myTrailStop);
		if (low[myIndex] <= myEffectiveStop || high[myIndex] >= myLimitPrice) {
			myPosition = 0;
			myEntryPrice = null;
			myStopPrice = null;
			myLimitPrice = null;
			myTrailStop = null;
			myLongExitSignal[myIndex] = true;
			myDidExitThisBar = true;
		}
	}
	else if (myPosition === -1) {
		const myCandidateTrail = low[myIndex] + myTrail;
		if (myTrailStop === null || myCandidateTrail < myTrailStop) {
			myTrailStop = myCandidateTrail;
		}
		const myEffectiveStop = Math.min(myStopPrice, myTrailStop);
		if (high[myIndex] >= myEffectiveStop || low[myIndex] <= myLimitPrice) {
			myPosition = 0;
			myEntryPrice = null;
			myStopPrice = null;
			myLimitPrice = null;
			myTrailStop = null;
			myShortExitSignal[myIndex] = true;
			myDidExitThisBar = true;
		}
	}

	if (myPosition === 0 && !myDidExitThisBar) {
		const myLongCond = (myLongCross[myIndex] || myLongPull[myIndex]) && myBull[myIndex]
			&& myTrendUp[myIndex] && myRsi[myIndex] < rsiOB;
		const myShortCond = useShort && (myShortCross[myIndex] || myShortPull[myIndex]) && myBear[myIndex]
			&& myTrendDown[myIndex] && myRsi[myIndex] > 30;

		if (myLongCond) {
			myPosition = 1;
			myEntryPrice = close[myIndex];
			myStopPrice = myEntryPrice - mySL;
			myLimitPrice = myEntryPrice + myTP;
			myTrailStop = myEntryPrice - myTrail;
			myLongEntrySignal[myIndex] = true;
		}
		else if (myShortCond) {
			myPosition = -1;
			myEntryPrice = close[myIndex];
			myStopPrice = myEntryPrice + mySL;
			myLimitPrice = myEntryPrice - myTP;
			myTrailStop = myEntryPrice + myTrail;
			myShortEntrySignal[myIndex] = true;
		}
	}

	myPositionState[myIndex] = myPosition;
}

// ─── Painting ────────────────────────────────────────────────
paint(myEmaFast, { name: 'EMA Fast', color: '#00E5FF', thickness: 2 });
paint(myEmaSlow, { name: 'EMA Slow', color: '#FFD54F', thickness: 2 });
paint(myEmaTrend, { name: 'EMA Trend', color: '#9E9E9E', thickness: 2 });

const myLongMarks = for_every(myLongEntrySignal, low, (_sig, _l) => _sig ? _l : null);
const myShortMarks = for_every(myShortEntrySignal, high, (_sig, _h) => _sig ? _h : null);

paint(myLongMarks, { name: 'Long Entry', color: 'lime', style: 'labels_below' });
paint(myShortMarks, { name: 'Short Entry', color: 'red', style: 'labels_above' });

// background highlight for open position state
const myCandleColors = for_every(myPositionState, _pos => {
	if (_pos > 0) { return 'rgba(0,200,0,0.1)'; }
	if (_pos < 0) { return 'rgba(200,0,0,0.1)'; }
	return null;
});
color_candles(myCandleColors);

// ─── Scanner/Alert/Strategy signals ───────────────────────────
// Each signal is registered exactly once, with a unique name,
// non-conditionally, as required by the engine.
register_signal(myLongEntrySignal, 'Long Entry Signal');
register_signal(myLongExitSignal, 'Long Exit Signal');
register_signal(myShortEntrySignal, 'Short Entry Signal');
register_signal(myShortExitSignal, 'Short Exit Signal');
describe_indicator('Kloom ATR Position Sizer', 'price');

// ── Inputs ─────────────────────────────────────────────────────────────────────
const accTab = input.tab('Account');
const myEquity = accTab.number('Account equity', 10000, { min: 10 });
const myRiskPct = accTab.number('Risk per trade (%)', 1.0, { min: 0.1, max: 10, step: 0.1 });

const stopTab = input.tab('Stop distance');
const myAtrLen = stopTab.number('ATR length', 14, { min: 1, max: 100 });
const myAtrMult = stopTab.number('ATR multiplier for stop', 2.0, { min: 0.5, max: 10, step: 0.5 });

const vizTab = input.tab('Display');
const myShowLvl = vizTab.boolean('Show stop levels from current price', true);

// ── Sizing math ────────────────────────────────────────────────────────────────
// ta.atr() in Pine uses RMA (Wilder's smoothing), equivalent to wildma(tr, len).
// atr() built-in here already implements Wilder's ATR, matching ta.atr exactly.
const myAtr = atr(high, low, close, myAtrLen);
const myStopDist = mult(myAtr, myAtrMult);
const myRiskMoney = myEquity * myRiskPct / 100;

// qty = riskMoney / stopDist, or null (na) when stopDist <= 0
const myQty = for_every(myStopDist, _dist => _dist > 0 ? myRiskMoney / _dist : null);
const myPosValue = for_every(myQty, close, (_q, _c) => _q !== null ? _q * _c : null);
const myLeverage = for_every(myPosValue, _pv => _pv !== null ? _pv / myEquity : null);

const myLongStop = sub(close, myStopDist);
const myShortStop = add(close, myStopDist);

// ── Plots ──────────────────────────────────────────────────────────────────────
// Pine's style_linebr breaks the line whenever the value is na; closest
// equivalent here is a ladder-free simple line, gated to null when hidden.
const myLongStopPlot = myShowLvl ? myLongStop : constants.empty_series;
const myShortStopPlot = myShowLvl ? myShortStop : constants.empty_series;

paint(myLongStopPlot, { name: 'Long Stop', color: 'teal', style: 'line', forceUsePriceAxis: true });
paint(myShortStopPlot, { name: 'Short Stop', color: 'red', style: 'line', forceUsePriceAxis: true });

// ── Table (overlay) ────────────────────────────────────────────────────────────
const myLastAtr = myAtr[myAtr.length - 1];
const myLastStopDist = myStopDist[myStopDist.length - 1];
const myLastQty = myQty[myQty.length - 1];
const myLastPosValue = myPosValue[myPosValue.length - 1];
const myLastLeverage = myLeverage[myLeverage.length - 1];

const myHeaderColor = 'rgba(0,0,0,0.8)';
const myCellColor = 'rgba(0,0,0,0.6)';
const myLeverageCellColor = (myLastLeverage !== null && myLastLeverage > 3) ? 'rgba(220,20,20,0.7)' : myCellColor;

paint_overlay('KloomSizerTable', { position: 'top_right' }, {
	rows: [
		{ cells: [
			{ text: 'Risk', color: 'white', background_color: myHeaderColor },
			{ text: `${myRiskMoney.toFixed(2)} (${myRiskPct.toFixed(1)}%)`, color: 'white', background_color: myCellColor }
		] },
		{ cells: [
			{ text: 'ATR', color: 'white', background_color: myHeaderColor },
			{ text: myLastAtr !== null && myLastAtr !== undefined ? myLastAtr.toFixed(current.decimals) : 'na', color: 'white', background_color: myCellColor }
		] },
		{ cells: [
			{ text: 'Stop dist', color: 'white', background_color: myHeaderColor },
			{ text: myLastStopDist !== null && myLastStopDist !== undefined ? myLastStopDist.toFixed(current.decimals) : 'na', color: 'white', background_color: myCellColor }
		] },
		{ cells: [
			{ text: 'Qty', color: 'white', background_color: myHeaderColor },
			{ text: myLastQty !== null ? myLastQty.toFixed(4) : 'na', color: 'white', background_color: 'rgba(0,128,128,0.5)' }
		] },
		{ cells: [
			{ text: 'Pos. value', color: 'white', background_color: myHeaderColor },
			{ text: myLastPosValue !== null ? myLastPosValue.toFixed(2) : 'na', color: 'white', background_color: myCellColor }
		] },
		{ cells: [
			{ text: 'Leverage', color: 'white', background_color: myHeaderColor },
			{ text: myLastLeverage !== null ? `${myLastLeverage.toFixed(2)}x` : 'na', color: 'white', background_color: myLeverageCellColor }
		] }
	]
});

// ── Signals (for scanners, alerts, strategy tester) ───────────────────────────
// Price closing beyond the computed long/short ATR stop levels
const mySignalLongStopHit = for_every(close, myLongStop, (_c, _ls) => _ls !== null && _c <= _ls);
const mySignalShortStopHit = for_every(close, myShortStop, (_c, _ss) => _ss !== null && _c >= _ss);
// Leverage exceeding 3x, flagged as high risk in the original Pine table
const mySignalHighLeverage = for_every(myLeverage, _lev => _lev !== null && _lev > 3);

register_signal(mySignalLongStopHit, 'Long Stop Hit');
register_signal(mySignalShortStopHit, 'Short Stop Hit');
register_signal(mySignalHighLeverage, 'High Leverage');
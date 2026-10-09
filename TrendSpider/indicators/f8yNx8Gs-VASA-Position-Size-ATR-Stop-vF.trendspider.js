/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : VASA Position Size & ATR Stop
 * Author       : VASATrendAI
 * Source URL   : https://www.tradingview.com/script/f8yNx8Gs-VASA-Position-Size-ATR-Stop-vF
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : VASA Position Size ATR Stop_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact ATR; position table via paint_overlay; colour inputs
 *   fixed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('VASA Position Size ATR Stop_TV', 'price');
const myAcctTab = input.tab('Account and Risk');
const myAccountSize = myAcctTab.number('Account size', 10000, { min: 0, step: 100 });
const myRiskPercent = myAcctTab.number('Risk per trade %', 1.0, { min: 0.01, max: 100, step: 0.1 });
const myDirectionLong = myAcctTab.boolean('Direction Long', true);
const myEntryTab = input.tab('Entry and Stop');
const myUseClose = myEntryTab.boolean('Entry = close', true);
const myManualEntry = myEntryTab.number('Manual entry price', 0.0, { min: 0 });
const myAtrLength = myEntryTab.number('ATR length', 14, { min: 1 });
const myAtrMultiplier = myEntryTab.number('ATR mult for stop', 1.5, { min: 0.1, step: 0.1 });
const myStyleTab = input.tab('Style');
const myTablePosition = myStyleTab.select('Table position', 'bottom_right', ['top_right', 'top_left', 'bottom_right', 'bottom_left']);
const myShowLines = myStyleTab.boolean('Draw lines', true);
// pine-parity: ta.atr = SMA-seeded RMA of true range
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
let myAcc = null, mySeen = 0, mySeed = 0;
const myAtr = myTr.map(_v => {
	if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === myAtrLength) myAcc = mySeed / myAtrLength; return myAcc; }
	myAcc = (myAcc * (myAtrLength - 1) + _v) / myAtrLength; return myAcc;
});
const myEntry = close.map(_c => myUseClose ? _c : myManualEntry);
const myStopDist = myAtr.map(_a => _a === null ? null : _a * myAtrMultiplier);
const myStop = myEntry.map((_e, _i) => myStopDist[_i] === null ? null : (myDirectionLong ? _e - myStopDist[_i] : _e + myStopDist[_i]));
const myRiskCash = myAccountSize * myRiskPercent / 100.0;
const myQty = myEntry.map((_e, _i) => (myStop[_i] === null || Math.abs(_e - myStop[_i]) <= 0) ? null : myRiskCash / Math.abs(_e - myStop[_i]));
paint(myEntry.map(_v => myShowLines ? _v : null), { name: 'Entry', color: '#2563eb', thickness: 1 });
paint(myStop.map(_v => myShowLines ? _v : null), { name: 'ATR stop', color: '#b91c1c', thickness: 1 });
const myLast = close.length - 1;
const myFmt = (_v, _d) => (_v === null || _v === undefined) ? 'n/a' : _v.toFixed(_d);
const myRow = (_k, _v, _c) => ({ cells: [{ text: _k, background_color: '#16233b', color: 'white' }, { text: _v, color: _c }] });
paint_overlay('VASA Risk Table', { position: myTablePosition }, {
	rows: [
		myRow('Direction', myDirectionLong ? 'LONG' : 'SHORT', myDirectionLong ? '#15803d' : '#b91c1c'),
		myRow('Entry', myFmt(myEntry[myLast], 4), 'white'),
		myRow('ATR stop', myFmt(myStop[myLast], 4), '#b91c1c'),
		myRow('Stop distance', myFmt(myStopDist[myLast], 4), 'white'),
		myRow('Risk ($)', myFmt(myRiskCash, 2), 'white'),
		myRow('Position size', myQty[myLast] === null ? 'n/a' : myQty[myLast].toFixed(4) + ' units', '#2563eb')
	]
});
register_signal(close.map(_c => myDirectionLong), 'Direction Long');
register_signal(close.map(_c => !myDirectionLong), 'Direction Short');
register_signal(myQty.map(_q => _q !== null && _q > 0), 'Valid Position Size');

/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Renko Volume Tracker
 * Author       : VTrader2021
 * Source URL   : https://www.tradingview.com/script/qOsPq5SH-Renko-Volume-Tracker
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Renko Volume Tracker_TV
 *
 * Deviations from the original: Reviewed AI draft; renko bricks simulated from chart closes (no renko ticker; at
 *   most one brick per bar); Pine-exact ATR; circle labels as triangle icons.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Renko Volume Tracker_TV', 'price');
const myChunkTab = input.tab('Renko Chunking');
const myParamType = myChunkTab.select('Box Size Method', 'ATR', ['ATR', 'Traditional']);
const myAtrLength = myChunkTab.number('Renko ATR Period', 14, { min: 1, max: 200 });
const myBoxFixed = myChunkTab.number('Traditional Box Size', 1.0, { min: 0.0001, max: 100000 });
const myNBricks = myChunkTab.number('Chunk Window N Bricks', 3, { min: 1, max: 50 });
const myColorUp = myChunkTab.color('Pivot Color Up', 'teal');
const myColorDn = myChunkTab.color('Pivot Color Down', 'purple');
// pine-parity: ta.atr = SMA-seeded RMA of true range
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
let myAcc = null, mySeen = 0, mySeed = 0;
const myAtr = myTr.map(_v => {
	if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === myAtrLength) myAcc = mySeed / myAtrLength; return myAcc; }
	myAcc = (myAcc * (myAtrLength - 1) + _v) / myAtrLength; return myAcc;
});
// Renko bricks are simulated from the chart closes (TrendSpider has no renko ticker): at most one brick per bar
const myNewBrick = close.map(() => false);
const myTrend = close.map(() => 1);
let myRenkoClose = close[0];
let myDir = 1;
for (let myI = 1; myI < close.length; myI += 1) {
	const myBox = myParamType === 'ATR' ? (myAtr[myI] || myBoxFixed) : myBoxFixed;
	const myDiff = close[myI] - myRenkoClose;
	if (myBox > 0 && Math.abs(myDiff) >= myBox) {
		myDir = myDiff > 0 ? 1 : -1;
		myRenkoClose += myDir * myBox;
		myNewBrick[myI] = true;
	}
	myTrend[myI] = myDir;
}
const myUp = close.map(() => null);
const myDn = close.map(() => null);
let myCount = 0, myMaxVol = 0, myMaxBar = null;
for (let myI = 0; myI < close.length; myI += 1) {
	const myVol = volume[myI] || 0;
	if (myVol > myMaxVol || myMaxVol === 0) { myMaxVol = myVol; myMaxBar = myI; }
	if (myNewBrick[myI]) {
		myCount += 1;
		if (myCount >= myNBricks) {
			if (myMaxBar !== null) {
				if (myTrend[myMaxBar] === 1) myUp[myMaxBar] = constants.icons.triangle_up;
				else myDn[myMaxBar] = constants.icons.triangle_down;
			}
			myCount = 0; myMaxVol = 0; myMaxBar = null;
		}
	}
}
paint(myUp, { name: 'Top Volume Up', style: 'labels_below', color: myColorUp });
paint(myDn, { name: 'Top Volume Down', style: 'labels_above', color: myColorDn });
register_signal(myUp.map(_v => _v !== null), 'Top Volume Pivot Up Trend');
register_signal(myDn.map(_v => _v !== null), 'Top Volume Pivot Down Trend');

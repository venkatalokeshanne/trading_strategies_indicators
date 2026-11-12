/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Supply & Demand Zones [ITA]
 * Author       : itamardrori_
 * Source URL   : https://www.tradingview.com/script/Bu6Z9HqB-Supply-Demand-Zones-ITA
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Supply Demand Zones ITA_TV
 *
 * Deviations from the original: Reviewed AI draft; zones taken at the pivot bar (as Pine) and drawn as up to 8 cloud
 *   slots per side that run until retest or eviction; labels as icons.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Supply Demand Zones ITA_TV', 'price');
const myPivotLen = input.number('Zone Pivot Strength', 8, { min: 2, max: 30 });
const myMaxZones = input.number('Max Zones Per Side', 6, { min: 1, max: 6 });
const myZoneHeight = input.select('Zone Height', 'Wick', ['Wick', 'Body']);
const myRemoveTest = input.boolean('Remove After Retest', true);
const SLOTS = 8;
const myN = close.length;
const myTop = (_i) => myZoneHeight === 'Wick' ? high[_i] : Math.max(open[_i], close[_i]);
const myBot = (_i) => myZoneHeight === 'Wick' ? low[_i] : Math.min(open[_i], close[_i]);
const myPivotAt = (_src, _i, _isHigh) => {
	const myP = _i - myPivotLen;
	if (myP - myPivotLen < 0) return false;
	for (let myK = myP - myPivotLen; myK <= _i; myK += 1) {
		if (myK === myP) continue;
		if (_isHigh ? (myK < myP ? !(_src[myP] > _src[myK]) : !(_src[myP] >= _src[myK])) : (myK < myP ? !(_src[myP] < _src[myK]) : !(_src[myP] <= _src[myK]))) return false;
	}
	return true;
};
// each zone starts on its pivot bar and runs until it is retested or evicted by newer zones (as the Pine boxes)
const mySupplyAll = [], myDemandAll = [];
let mySupplyLive = [], myDemandLive = [];
const mySupplyRetest = close.map(() => false), myDemandRetest = close.map(() => false);
const mySupplyPivot = close.map(() => false), myDemandPivot = close.map(() => false);
for (let myI = 0; myI < myN; myI += 1) {
	if (myPivotAt(high, myI, true)) {
		const myP = myI - myPivotLen;
		const myZ = { top: myTop(myP), bot: myBot(myP), from: myP, to: null };
		mySupplyAll.push(myZ); mySupplyLive.push(myZ); mySupplyPivot[myP] = true;
		if (mySupplyLive.length > myMaxZones) { const myOld = mySupplyLive.shift(); myOld.to = myI; }
	}
	if (myPivotAt(low, myI, false)) {
		const myP = myI - myPivotLen;
		const myZ = { top: myTop(myP), bot: myBot(myP), from: myP, to: null };
		myDemandAll.push(myZ); myDemandLive.push(myZ); myDemandPivot[myP] = true;
		if (myDemandLive.length > myMaxZones) { const myOld = myDemandLive.shift(); myOld.to = myI; }
	}
	if (myRemoveTest) {
		mySupplyLive = mySupplyLive.filter(_z => { const myHit = high[myI] >= _z.bot && high[myI] <= _z.top; if (myHit) { _z.to = myI; mySupplyRetest[myI] = true; } return !myHit; });
		myDemandLive = myDemandLive.filter(_z => { const myHit = low[myI] <= _z.top && low[myI] >= _z.bot; if (myHit) { _z.to = myI; myDemandRetest[myI] = true; } return !myHit; });
	}
}
const myAssign = (_zones) => {
	const myTops = [], myBots = [];
	for (let myS = 0; myS < SLOTS; myS += 1) { myTops.push(close.map(() => null)); myBots.push(close.map(() => null)); }
	const myFree = close.map(() => 0);
	const myEnds = [];
	for (let myS = 0; myS < SLOTS; myS += 1) myEnds.push(-1);
	_zones.slice().sort((_a, _b) => _a.from - _b.from).forEach(_z => {
		const myEnd = _z.to === null ? myN - 1 : _z.to;
		let myPick = -1;
		for (let myS = 0; myS < SLOTS; myS += 1) { if (myEnds[myS] < _z.from) { myPick = myS; break; } }
		if (myPick === -1) return;
		myEnds[myPick] = myEnd;
		for (let myK = _z.from; myK <= myEnd; myK += 1) { myTops[myPick][myK] = _z.top; myBots[myPick][myK] = _z.bot; }
	});
	return { tops: myTops, bots: myBots };
};
const mySupply = myAssign(mySupplyAll);
const myDemand = myAssign(myDemandAll);
for (let myS = 0; myS < SLOTS; myS += 1) {
	color_cloud(mySupply.tops[myS], mySupply.bots[myS], 'rgba(242,54,69,0.25)', 'rgba(242,54,69,0.25)', 'Supply ' + myS + ' Up', 'Supply ' + myS + ' Dn');
	color_cloud(myDemand.tops[myS], myDemand.bots[myS], 'rgba(8,153,129,0.25)', 'rgba(8,153,129,0.25)', 'Demand ' + myS + ' Up', 'Demand ' + myS + ' Dn');
}
paint(mySupplyPivot.map(_f => _f ? constants.icons.triangle_down : null), { name: 'Supply Mark', style: 'labels_above', color: '#f23645' });
paint(myDemandPivot.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Demand Mark', style: 'labels_below', color: '#089981' });
register_signal(mySupplyRetest, 'Supply Zone Retest');
register_signal(myDemandRetest, 'Demand Zone Retest');

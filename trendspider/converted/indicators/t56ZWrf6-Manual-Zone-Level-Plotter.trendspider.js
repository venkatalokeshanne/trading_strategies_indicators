/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Manual Zone & Level Plotter
 * Author       : cryptoxenz
 * Source URL   : https://www.tradingview.com/script/t56ZWrf6-Manual-Zone-Level-Plotter
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Manual Zone Level Plotter_TV
 *
 * Deviations from the original: Text inputs not available: the zone/level strings are constants in the code (example
 *   strings pre-filled; empty in the original); up to 3 items per category; zones G/O as
 *   top/bottom lines plus cloud, X/R/S as single lines (ranges draw the top edge); price
 *   tags via labels.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Manual Zone Level Plotter_TV', 'price');
// Text inputs are not available: edit the two strings below.
// Zones: G = primary zone, O = secondary zone, X = marker levels; groups separated by ';', items by ','; a range draws a zone, a number a line.
// Levels: R = levels above, S = levels below.
const myBoxStr = 'G4371.83-4400;O4325-4350;X4350';
const myLvStr = 'R4350,4400;S4325,4311.89';
const myShowPx = input.boolean('Show price tags', true);
const myLineW = input.number('Line width', 1, { min: 1, max: 3 });
const SLOTS = 3;
const mySegment = (_src, _tag) => {
	let myFound = '';
	_src.replace(/\s/g, '').split(';').forEach(_p => { if (_p.length > 1 && _p.startsWith(_tag)) myFound = _p.substring(1); });
	return myFound;
};
const myParse = (_body) => {
	const myOut = [];
	if (_body.length > 0) _body.split(',').forEach(_it => {
		const myPair = _it.split('-');
		if (myPair.length === 2) { const myA = parseFloat(myPair[0]), myB = parseFloat(myPair[1]); if (!isNaN(myA) && !isNaN(myB)) myOut.push({ top: Math.max(myA, myB), bot: Math.min(myA, myB), zone: true }); }
		else { const myP = parseFloat(_it); if (!isNaN(myP)) myOut.push({ top: myP, bot: myP, zone: false }); }
	});
	return myOut.slice(0, SLOTS);
};
const myLast = close.length - 1;
// zone categories (G, O) draw top/bottom lines plus a fill; line categories (X, R, S) draw one line per item (a range draws its top edge)
const myZoneCats = [
	{ key: 'G', items: myParse(mySegment(myBoxStr, 'G')), color: 'rgb(38,166,154)', fill: 'rgba(38,166,154,0.1)' },
	{ key: 'O', items: myParse(mySegment(myBoxStr, 'O')), color: 'rgb(255,152,0)', fill: 'rgba(255,152,0,0.1)' }
];
const myLineCats = [
	{ key: 'X', items: myParse(mySegment(myBoxStr, 'X')), color: 'rgb(144,164,174)' },
	{ key: 'R', items: myParse(mySegment(myLvStr, 'R')), color: 'rgb(239,83,80)' },
	{ key: 'S', items: myParse(mySegment(myLvStr, 'S')), color: 'rgb(38,166,154)' }
];
const myEmpty = () => close.map(() => null);
for (let myC = 0; myC < myZoneCats.length; myC += 1) {
	for (let myS = 0; myS < SLOTS; myS += 1) {
		const myItem = myZoneCats[myC].items[myS];
		const myZ = !!myItem;
		const myTopP = paint(myZ ? horizontal_line(myItem.top) : myEmpty(), { name: myZoneCats[myC].key + ' Top ' + (myS + 1), color: myZoneCats[myC].color, thickness: myLineW });
		const myBotP = paint(myZ ? horizontal_line(myItem.bot) : myEmpty(), { name: myZoneCats[myC].key + ' Bot ' + (myS + 1), color: myZoneCats[myC].color, thickness: myLineW });
		color_cloud(myZ ? horizontal_line(myItem.top) : myEmpty(), myZ ? horizontal_line(myItem.bot) : myEmpty(), myZoneCats[myC].fill, myZoneCats[myC].fill, myZoneCats[myC].key + ' Fill Up ' + (myS + 1), myZoneCats[myC].key + ' Fill Dn ' + (myS + 1));
		if (myShowPx && myZ) {
			paint_label_at_line(myTopP, myLast, String(myItem.top), { color: myZoneCats[myC].color });
			if (myItem.zone) paint_label_at_line(myBotP, myLast, String(myItem.bot), { color: myZoneCats[myC].color });
		}
	}
}
for (let myC = 0; myC < myLineCats.length; myC += 1) {
	for (let myS = 0; myS < SLOTS; myS += 1) {
		const myItem = myLineCats[myC].items[myS];
		const myP = paint(myItem ? horizontal_line(myItem.top) : myEmpty(), { name: myLineCats[myC].key + ' Level ' + (myS + 1), color: myLineCats[myC].color, thickness: myLineW });
		if (myShowPx && myItem) paint_label_at_line(myP, myLast, String(myItem.top), { color: myLineCats[myC].color });
	}
}
const myR = myLineCats[1].items, myS2 = myLineCats[2].items;
const myHighR = myR.length ? Math.max(...myR.map(_i => _i.top)) : null;
const myLowS = myS2.length ? Math.min(...myS2.map(_i => _i.bot)) : null;
register_signal(close.map(_c => myHighR !== null && _c > myHighR), 'Resistance Break');
register_signal(close.map(_c => myLowS !== null && _c < myLowS), 'Support Break');

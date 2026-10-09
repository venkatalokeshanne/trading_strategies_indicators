/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Earnings Fundamentals Overlay
 * Author       : metallicalfa
 * Source URL   : https://www.tradingview.com/script/Vfdmbvf3-Earnings-Fundamentals-Overlay
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Earnings Fundamentals Overlay_TV
 *
 * Deviations from the original: Earnings labels drawn with the TrendSpider earnings and fundamentals feeds (revenue,
 *   gross profit, operating income, net income from the latest report on or before each
 *   event); one line per event with ' | ' separators; label placed on the first bar
 *   at/after the report timestamp
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Earnings Fundamentals Overlay_TV', 'price');
const myShowEps = input.boolean('Show EPS', true);
const myShowRev = input.boolean('Show Revenue', true);
const myShowMargins = input.boolean('Show Margins', true);
const myLabelBelow = input.boolean('Labels below bars', true);
const myEarn = await request.earnings(current.ticker);
assert(!myEarn.error, 'Error fetching earnings: ' + myEarn.error);
const myFund = await request.fundamental(current.ticker, ['revenue', 'gross_profit', 'operating_income_loss', 'net_income'], 24);
assert(!myFund.error, 'Error fetching fundamentals: ' + myFund.error);
const myEvents = myEarn.filter(_e => !_e.isFuture && _e.eps !== null && _e.eps !== undefined).sort((_a, _b) => _a.timestamp - _b.timestamp);
const myAsc = (_k) => (myFund[_k] || []).slice().sort((_a, _b) => _a.reportdate - _b.reportdate);
const myRev = myAsc('revenue'), myGp = myAsc('gross_profit'), myOi = myAsc('operating_income_loss'), myNi = myAsc('net_income');
const myUpTo = (_recs, _ts) => _recs.filter(_r => _r.reportdate <= _ts);
const myFmtB = (_x) => _x === null ? 'n/a' : (Math.abs(_x) >= 1e9 ? (_x / 1e9).toFixed(2) + 'B' : (_x / 1e6).toFixed(1) + 'M');
const myFmtP = (_x) => _x === null ? 'n/a' : _x.toFixed(1) + '%';
const myFmtC = (_c, _p) => (_c === null || _p === null || _p === 0) ? 'n/a' : (_c >= _p ? '+' : '') + ((_c / _p - 1) * 100).toFixed(1) + '%';
const myMargin = (_recs, _rev, _ts) => { const myU = myUpTo(_recs, _ts); return (myU.length && _rev) ? myU[myU.length - 1].value / _rev * 100 : null; };
const myN = close.length;
const myBar = (_ts) => { for (let myI = 0; myI < myN; myI += 1) if (time[myI] >= _ts) return myI; return -1; };
const myAnchor = close.map(() => null), myBeat = close.map(() => false), myMiss = close.map(() => false), myBarSig = close.map(() => false);
const myPending = [];
myEvents.forEach((_e) => {
	const myI = myBar(_e.timestamp);
	if (myI < 0 || (myI === 0 && time[0] > _e.timestamp + 86400 * 5)) return;
	const myRu = myUpTo(myRev, _e.timestamp), myCur = myRu.length ? myRu[myRu.length - 1].value : null;
	const myPrev = myRu.length > 1 ? myRu[myRu.length - 2].value : null, myYoy = myRu.length > 4 ? myRu[myRu.length - 5].value : null;
	const mySur = (_e.eps_est === null || _e.eps_est === undefined || _e.eps_est === 0) ? null : (_e.eps / _e.eps_est - 1) * 100;
	const myParts = [];
	if (myShowEps) myParts.push('EPS ' + _e.eps.toFixed(2) + ' vs ' + (_e.eps_est === null || _e.eps_est === undefined ? 'n/a' : _e.eps_est.toFixed(2)) + (mySur === null ? '' : ' (' + (mySur >= 0 ? '+' : '') + mySur.toFixed(1) + '%)'));
	if (myShowRev) myParts.push('Rev ' + myFmtB(myCur) + ' QoQ ' + myFmtC(myCur, myPrev) + ' YoY ' + myFmtC(myCur, myYoy));
	if (myShowMargins) myParts.push('GM ' + myFmtP(myMargin(myGp, myCur, _e.timestamp)) + ' OM ' + myFmtP(myMargin(myOi, myCur, _e.timestamp)) + ' NM ' + myFmtP(myMargin(myNi, myCur, _e.timestamp)));
	myAnchor[myI] = myLabelBelow ? low[myI] : high[myI];
	myBarSig[myI] = true;
	if (mySur !== null) { if (mySur >= 0) myBeat[myI] = true; else myMiss[myI] = true; }
	myPending.push({ i: myI, text: myParts.join(' | '), good: mySur === null ? null : mySur >= 0 });
});
const myAnchorP = paint(myAnchor, { name: 'Earnings Anchor', color: 'gray', style: 'dotted', marker: 'circle' });
myPending.forEach((_p) => paint_label_at_line(myAnchorP, _p.i, _p.text, { color: _p.good === null ? 'gray' : (_p.good ? 'teal' : 'red') }));
register_signal(myBeat, 'Earnings Beat');
register_signal(myMiss, 'Earnings Miss');
register_signal(myBarSig, 'Earnings Report Bar');

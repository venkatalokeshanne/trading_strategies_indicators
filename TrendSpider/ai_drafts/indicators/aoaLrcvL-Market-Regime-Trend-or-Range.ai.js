describe_indicator('Market Regime - Trend or Range', 'price');

// Regime settings
const myRegimeTab = input.tab('Regime Settings');
const myAdxLen = myRegimeTab.number('ADX Length', 14, { min: 1, max: 100 });
const myAdxTrend = myRegimeTab.number('ADX Trend Threshold', 25, { min: 0, max: 100 });
const myAdxRange = myRegimeTab.number('ADX Range Threshold', 20, { min: 0, max: 100 });
const myErLen = myRegimeTab.number('Efficiency Ratio Length', 20, { min: 1, max: 200 });
const myErTrend = myRegimeTab.number('ER Trend Threshold', 0.5, { min: 0, max: 1, step: 0.05 });
const myErRange = myRegimeTab.number('ER Range Threshold', 0.3, { min: 0, max: 1, step: 0.05 });
const myChopLen = myRegimeTab.number('Choppiness Length', 14, { min: 1, max: 200 });

const myVisualsTab = input.tab('Visuals');
const myShowBG = myVisualsTab.boolean('Regime Background (candle color proxy)', true);
const myShowDash = myVisualsTab.boolean('Dashboard', true);
const myDashPos = myVisualsTab.select('Dashboard Position', 'top_right', ['top_right', 'top_left', 'bottom_right', 'bottom_left']);

// 1) ADX via built-in indicators.adx (gives adx, dmiPlus, dmiMinus)
const myAdxObject = indicators.adx(myAdxLen);
const myAdx = myAdxObject.adx;

const myAdxVote = for_every(myAdx, _adx => {
	if (_adx > myAdxTrend) return 1;
	if (_adx < myAdxRange) return -1;
	return 0;
});

// 2) Kaufman Efficiency Ratio
const myErChange = for_every(close, shift(close, myErLen), (_c, _cPrev) => Math.abs(_c - _cPrev));
const myCloseDiff = for_every(close, shift(close, 1), (_c, _cPrev) => Math.abs(_c - _cPrev));
const myErVol = sum(myCloseDiff, myErLen);
const myEr = for_every(myErChange, myErVol, (_chg, _vol) => _vol !== 0 ? _chg / _vol : 0);
const myErVote = for_every(myEr, _er => {
	if (_er > myErTrend) return 1;
	if (_er < myErRange) return -1;
	return 0;
});

// 3) Choppiness Index
const myChopRange = sub(highest(high, myChopLen), lowest(low, myChopLen));
// atr(high, low, close, 1) with length 1 equals plain True Range per candle
const myTrueRange = atr(high, low, close, 1);
const mySumTR = sum(myTrueRange, myChopLen);
const myChop = for_every(myChopRange, mySumTR, (_range, _sumtr) => _range > 0 ? 100 * Math.log10(_sumtr / _range) / Math.log10(myChopLen) : 50);
const myChopVote = for_every(myChop, _chop => {
	if (_chop < 38.2) return 1;
	if (_chop > 61.8) return -1;
	return 0;
});

// Composite verdict (2-of-3 agreement)
const myScore = for_every(myAdxVote, myErVote, myChopVote, (_a, _e, _c) => _a + _e + _c);
const myIsTrend = for_every(myScore, _s => _s >= 2);
const myIsRange = for_every(myScore, _s => _s <= -2);

// Trend-strength meter 0-100
const myAdxN = for_every(myAdx, _adx => Math.min(_adx / 50 * 100, 100));
const myErN = for_every(myEr, _er => Math.min(_er * 100, 100));
const myChopN = for_every(myChop, _chop => Math.max(0, 100 - _chop));
const myStrength = for_every(myAdxN, myErN, myChopN, (_a, _e, _c) => (_a + _e + _c) / 3);

// Background proxy: since bgcolor() is not available in the API,
// we tint candles instead (closest equivalent available).
const myRegimeColors = for_every(myIsTrend, myIsRange, (_t, _r) => {
	if (!myShowBG) return null;
	if (_t) return 'rgba(0,128,128,0.25)';
	if (_r) return 'rgba(255,165,0,0.25)';
	return null;
});
color_candles(myRegimeColors);

// Register signals for scanners / alerts / strategies
register_signal(myIsTrend, 'Market Is Trending');
register_signal(myIsRange, 'Market Is Ranging');
const myTrendSwitch = for_every(myIsTrend, shift(myIsTrend, 1), (_now, _prev) => _now && !_prev);
const myRangeSwitch = for_every(myIsRange, shift(myIsRange, 1), (_now, _prev) => _now && !_prev);
register_signal(myTrendSwitch, 'Switched To Trend');
register_signal(myRangeSwitch, 'Switched To Range');

// Dashboard overlay showing the latest regime readout
const myLastIndex = close.length - 1;
const myLastAdx = myAdx[myLastIndex];
const myLastEr = myEr[myLastIndex];
const myLastChop = myChop[myLastIndex];
const myLastScore = myScore[myLastIndex];
const myLastStrength = myStrength[myLastIndex];
const myLastIsTrend = myIsTrend[myLastIndex];
const myLastIsRange = myIsRange[myLastIndex];
const myRegimeText = myLastIsTrend ? 'TREND' : (myLastIsRange ? 'RANGE' : 'MIXED');
const myPlaybookText = myLastIsTrend ? 'Trend tools' : (myLastIsRange ? 'Fade tools' : 'Stand aside');

paint_overlay('RegimeDashboard', { position: myDashPos }, {
	rows: myShowDash ? [
		{ cells: [{ text: 'MARKET REGIME', color: 'white' }, { text: myRegimeText, color: myLastIsTrend ? 'teal' : (myLastIsRange ? 'orange' : 'gray') }] },
		{ cells: [{ text: 'ADX', color: 'gray' }, { text: myLastAdx.toFixed(1), color: 'white' }] },
		{ cells: [{ text: 'Efficiency', color: 'gray' }, { text: myLastEr.toFixed(2), color: 'white' }] },
		{ cells: [{ text: 'Choppiness', color: 'gray' }, { text: myLastChop.toFixed(1), color: 'white' }] },
		{ cells: [{ text: 'Strength', color: 'gray' }, { text: Math.round(myLastStrength) + '/100', color: 'white' }] },
		{ cells: [{ text: 'Score', color: 'gray' }, { text: myLastScore + '/3', color: 'white' }] },
		{ cells: [{ text: 'Playbook', color: 'gray' }, { text: myPlaybookText, color: 'white' }] }
	] : []
});
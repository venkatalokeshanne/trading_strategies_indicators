describe_indicator('SMC MentorFX Pro Max');

// --- Inputs ---
const mySensitivity = input.number('OB Sensitivity', 3.2, { min: 0.1, max: 20, step: 0.1 });
const myRiskReward = input.number('Risk Reward Ratio', 2.5, { min: 0.1, max: 20, step: 0.1 });
const myUseKillZone = input.boolean('Trade Only Kill Zones', true);
const mySessionGroup = input.row();
const myKzStart1 = mySessionGroup.number('KZ1 Start Hour (UTC+3)', 9, { min: 0, max: 23 });
const myKzEnd1 = mySessionGroup.number('KZ1 End Hour (UTC+3)', 12, { min: 0, max: 23 });
const mySessionGroup2 = input.row();
const myKzStart2 = mySessionGroup2.number('KZ2 Start Hour (UTC+3)', 13, { min: 0, max: 23 });
const myKzEnd2 = mySessionGroup2.number('KZ2 End Hour (UTC+3)', 17, { min: 0, max: 23 });

// --- Core math ---
const myAtr14 = atr(high, low, close, 14);

const myPrevHigh = shift(high, 1);
const myPrevLow = shift(low, 1);

// Bullish / Bearish Order Block conditions
const myBullOb = for_every(close, myPrevHigh, open, myAtr14, (_c, _ph, _o, _a) => _c > _ph && (_c - _o) > _a * mySensitivity);
const myBearOb = for_every(close, myPrevLow, open, myAtr14, (_c, _pl, _o, _a) => _c < _pl && (_o - _c) > _a * mySensitivity);

// Inducement (IDM) - break of prior 30 bar high/low (shifted by 1, like ta.highest(..)[1])
const myHighest30Prev = shift(highest(high, 30), 1);
const myLowest30Prev = shift(lowest(low, 30), 1);
const myHasIdm = for_every(high, myHighest30Prev, low, myLowest30Prev, (_h, _hh, _l, _ll) => _h > _hh || _l < _ll);

// Crossover / Crossunder of close vs prior 15 bar highest/lowest (shifted by 1)
const myHighest15Prev = shift(highest(high, 15), 1);
const myLowest15Prev = shift(lowest(low, 15), 1);
const myPrevClose = shift(close, 1);
const myPrevHighest15Prev = shift(myHighest15Prev, 1);
const myPrevLowest15Prev = shift(myLowest15Prev, 1);

const myLongCross = for_every(close, myHighest15Prev, myPrevClose, myPrevHighest15Prev, (_c, _hh, _pc, _phh) => _c > _hh && _pc <= _phh);
const myShortCross = for_every(close, myLowest15Prev, myPrevClose, myPrevLowest15Prev, (_c, _ll, _pc, _pll) => _c < _ll && _pc >= _pll);

// --- Kill Zone session check ---
// Pine code uses time(timeframe.period, "0900-1200,1300-1700", "UTC+3").
// This platform has no built-in arbitrary-timezone session function, so we
// approximate by manually shifting the UTC hour of each candle by +3 hours
// and checking it against the two configurable kill zone windows below.
const myInSession = time.map(_t => {
	if (!myUseKillZone) {
		return true;
	}
	const myUtcSeconds = _t % 86400;
	const myUtcHour = Math.floor(myUtcSeconds / 3600);
	const myShiftedHour = (myUtcHour + 3) % 24;
	const myInZone1 = myShiftedHour >= myKzStart1 && myShiftedHour < myKzEnd1;
	const myInZone2 = myShiftedHour >= myKzStart2 && myShiftedHour < myKzEnd2;
	return myInZone1 || myInZone2;
});

// --- Final entry signals ---
const myLongEntry = for_every(myInSession, myHasIdm, myLongCross, (_s, _idm, _lc) => _s && _idm && _lc);
const myShortEntry = for_every(myInSession, myHasIdm, myShortCross, (_s, _idm, _sc) => _s && _idm && _sc);

// Register signals for scanners, alerts and strategy tester
register_signal(myLongEntry, 'Long Entry');
register_signal(myShortEntry, 'Short Entry');
register_signal(myBullOb, 'Bullish Order Block');
register_signal(myBearOb, 'Bearish Order Block');
register_signal(myHasIdm, 'Inducement Break');
register_signal(myInSession, 'In Kill Zone');

// --- Painting ---
const myLongMarks = for_every(myLongEntry, low, (_e, _l) => _e ? _l : null);
const myShortMarks = for_every(myShortEntry, high, (_e, _h) => _e ? _h : null);

paint(myLongMarks, { name: 'LongEntry', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(myShortMarks, { name: 'ShortEntry', style: 'labels_above', color: '#EF5350', thickness: 3 });

const myBullObMarks = for_every(myBullOb, low, (_o, _l) => _o ? _l : null);
const myBearObMarks = for_every(myBearOb, high, (_o, _h) => _o ? _h : null);

paint(myBullObMarks, { name: 'BullishOB', style: 'labels_below', color: '#4DA3FF', thickness: 1 });
paint(myBearObMarks, { name: 'BearishOB', style: 'labels_above', color: '#FFA726', thickness: 1 });

// --- Status overlay (replaces TradingView table) ---
// Win Rate / Last PnL from the Pine strategy module cannot be reproduced here
// because this platform's custom indicators have no strategy/backtest engine
// context (no equity curve, closed trades, netprofit). Only Session status
// and Signal readiness, which are computable from the series above, are shown.
const myLastInSession = myInSession[myInSession.length - 1];
const myLastSignalReady = myLongEntry[myLongEntry.length - 1] || myShortEntry[myShortEntry.length - 1];

paint_overlay('StatusTable', { position: 'top_right' }, {
	rows: [{
		cells: [
			{ text: 'Session', color: 'white' },
			{ text: myLastInSession ? 'YES' : 'NO', background_color: myLastInSession ? '#2962FF' : '#EF5350', color: 'white' }
		]
	}, {
		cells: [
			{ text: 'Signal', color: 'white' },
			{ text: myLastSignalReady ? 'READY' : 'WAIT', background_color: '#757575', color: 'white' }
		]
	}, {
		cells: [
			{ text: 'Risk Reward', color: 'white' },
			{ text: String(myRiskReward), background_color: '#424242', color: 'white' }
		]
	}]
});
describe_indicator('PRO Investing Nasdaq Silver Bullet Signals', 'price');

// This indicator reproduces the "entry logic" of the original
// Pine Script strategy (Silver Bullet time window, candle count
// confirmation, 200 EMA filter). The Custom JS API has no order
// execution engine (no strategy.entry/exit, no position tracking,
// no stop loss / take profit orders), so the actual backtesting
// part (SL/TP exits, time based close) of the Pine strategy can
// not be reproduced here. We expose Long/Short signal conditions
// (usable in Scanner/Alerts/Strategy Tester via register_signal)
// and we visually mark the Silver Bullet window and the signals.

const momentTz = library('moment-timezone');

const sessionTab = input.tab('Silver Bullet');
const windowRow = sessionTab.row();
const myWindowText = windowRow.text('Window (HHMM-HHMM, NY time)', '1000-1100');

const myCountNeeded = sessionTab.number('Candle Count Confirmation', 2, { min: 1, max: 20 });
const myUseEma = sessionTab.boolean('Use 200 EMA Filter?', true);

const riskGroup = sessionTab.group('Risk (for reference only)');
const riskRow = riskGroup.row();
const mySlPercent = riskRow.number('Stop Loss %', 0.3, { min: 0.01, max: 50, step: 0.1 });
const myTpPercent = riskRow.number('Take Profit %', 0.6, { min: 0.01, max: 50, step: 0.1 });

// --- parse the window text, assume format "HHMM-HHMM" ---
const myWindowMatch = /^(\d{2})(\d{2})-(\d{2})(\d{2})$/.exec(myWindowText);
assert(myWindowMatch, 'Window must be in format HHMM-HHMM, e.g. 1000-1100');

const myStartMinutes = Number(myWindowMatch[1]) * 60 + Number(myWindowMatch[2]);
const myEndMinutes = Number(myWindowMatch[3]) * 60 + Number(myWindowMatch[4]);

// --- 200 EMA filter ---
const myEma200 = ema(close, 200);

// --- is current candle inside the Silver Bullet window (NY time) ---
const myIsSbWindow = time.map(_t => {
	const myNyMoment = momentTz.unix(_t).tz('America/New_York');
	const myMinutesOfDay = myNyMoment.hours() * 60 + myNyMoment.minutes();
	return myMinutesOfDay >= myStartMinutes && myMinutesOfDay < myEndMinutes;
});

// --- consecutive up/down candle counters (mirrors Pine's var int logic) ---
const myUpCount = for_every(close, open, (_c, _o, _prev) => _c > _o ? ((_prev || 0) + 1) : 0);
const myDnCount = for_every(close, open, (_c, _o, _prev) => _c < _o ? ((_prev || 0) + 1) : 0);

// --- entry conditions ---
const myLongCond = for_every(
	myIsSbWindow, myUpCount, close, myEma200,
	(_win, _up, _c, _ema) => Boolean(_win) && _up >= myCountNeeded && (!myUseEma || _c > _ema)
);

const myShortCond = for_every(
	myIsSbWindow, myDnCount, close, myEma200,
	(_win, _dn, _c, _ema) => Boolean(_win) && _dn >= myCountNeeded && (!myUseEma || _c < _ema)
);

// --- visuals ---
// Tint candles during the Silver Bullet window (approximation of Pine's bgcolor)
const myWindowCandleColors = myIsSbWindow.map(_win => _win ? 'rgba(41,98,255,0.12)' : null);
color_candles(myWindowCandleColors);

paint(myUseEma ? myEma200 : constants.empty_series, { name: 'Trend Filter EMA200', color: '#f1c40f', thickness: 2 });

const myLongMarks = myLongCond.map(_v => _v ? constants.icons.triangle_up : null);
const myShortMarks = myShortCond.map(_v => _v ? constants.icons.triangle_down : null);

paint(myLongMarks, { name: 'SB Long', style: 'labels_below', color: 'green' });
paint(myShortMarks, { name: 'SB Short', style: 'labels_above', color: 'red' });

// --- reference SL/TP levels at the moment of signal (informational only, no actual order management) ---
const myLongStopLoss = for_every(myLongCond, close, (_cond, _c) => _cond ? _c * (1 - mySlPercent / 100) : null);
const myLongTakeProfit = for_every(myLongCond, close, (_cond, _c) => _cond ? _c * (1 + myTpPercent / 100) : null);
const myShortStopLoss = for_every(myShortCond, close, (_cond, _c) => _cond ? _c * (1 + mySlPercent / 100) : null);
const myShortTakeProfit = for_every(myShortCond, close, (_cond, _c) => _cond ? _c * (1 - myTpPercent / 100) : null);

paint(myLongStopLoss, { name: 'Long Stop Loss Level', style: 'dotted', color: '#e74c3c' });
paint(myLongTakeProfit, { name: 'Long Take Profit Level', style: 'dotted', color: '#2ecc71' });
paint(myShortStopLoss, { name: 'Short Stop Loss Level', style: 'dotted', color: '#e74c3c' });
paint(myShortTakeProfit, { name: 'Short Take Profit Level', style: 'dotted', color: '#2ecc71' });

// --- signals for scanner, alerts, strategy tester ---
register_signal(myLongCond, 'Silver Bullet Long Signal');
register_signal(myShortCond, 'Silver Bullet Short Signal');
register_signal(myIsSbWindow, 'In Silver Bullet Window');
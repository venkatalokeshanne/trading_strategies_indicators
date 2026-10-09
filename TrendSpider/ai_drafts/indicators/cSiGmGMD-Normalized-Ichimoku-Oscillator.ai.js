describe_indicator('Normalized Ichimoku Oscillator', 'lower');

// ==========================================
// INPUTS
// ==========================================
const myIchimokuTab = input.tab('Ichimoku Lengths');
const myTenkanLen = myIchimokuTab.number('Tenkan-sen Period', 9, { min: 1 });
const myKijunLen = myIchimokuTab.number('Kijun-sen Period', 26, { min: 1 });
const mySpanBLen = myIchimokuTab.number('Senkou Span B Period', 52, { min: 1 });
const myAtrLen = myIchimokuTab.number('ATR Normalization Length', 14, { min: 1 });

const myMaTab = input.tab('Kijun Deviation MA');
const myShowKijunMA = myMaTab.boolean('Show Kijun MA', true);
const myMaType = myMaTab.select('Moving Average Type', 'EMA', ['EMA', 'SMA', 'HMA']);
const myMaLen = myMaTab.number('MA Length', 10, { min: 1 });

const myVisTab = input.tab('Oscillator Visibility');
const myShowTenkan = myVisTab.boolean('Show Tenkan Deviation', true);
const myShowKijun = myVisTab.boolean('Show Kijun Deviation (Primary)', true);
const myShowSpanA = myVisTab.boolean('Show Span A Deviation', true);
const myShowSpanB = myVisTab.boolean('Show Span B Deviation', true);

const myLevelsTab = input.tab('Threshold Settings');
const myObExtreme = myLevelsTab.number('Overbought Extreme', 3.0, { min: -10, max: 10, step: 0.1 });
const myObWarning = myLevelsTab.number('Overbought Warning', 2.0, { min: -10, max: 10, step: 0.1 });
const myOsWarning = myLevelsTab.number('Oversold Warning', -2.0, { min: -10, max: 10, step: 0.1 });
const myOsExtreme = myLevelsTab.number('Oversold Extreme', -3.0, { min: -10, max: 10, step: 0.1 });

// ==========================================
// CALCULATIONS
// ==========================================

// Donchian midline: avg(highest high, lowest low) over a window
function myGetDonchian(myLen) {
	return div(add(highest(high, myLen), lowest(low, myLen)), 2);
}

const myTenkan = myGetDonchian(myTenkanLen);
const myKijun = myGetDonchian(myKijunLen);
const mySpanA = div(add(myTenkan, myKijun), 2);
const mySpanB = myGetDonchian(mySpanBLen);
const myAtr = atr(high, low, close, myAtrLen);

// Normalized distances (close - line) / atr, 0 when atr <= 0
const myOscTenkan = for_every(close, myTenkan, myAtr, (_c, _t, _a) => _a > 0 ? (_c - _t) / _a : 0);
const myOscKijun = for_every(close, myKijun, myAtr, (_c, _k, _a) => _a > 0 ? (_c - _k) / _a : 0);
const myOscSpanA = for_every(close, mySpanA, myAtr, (_c, _s, _a) => _a > 0 ? (_c - _s) / _a : 0);
const myOscSpanB = for_every(close, mySpanB, myAtr, (_c, _s, _a) => _a > 0 ? (_c - _s) / _a : 0);

// Kijun deviation MA, type selectable
let myKijunMA;
if (myMaType === 'SMA') {
	myKijunMA = sma(myOscKijun, myMaLen);
}
else if (myMaType === 'HMA') {
	myKijunMA = hullma(myOscKijun, myMaLen);
}
else {
	myKijunMA = ema(myOscKijun, myMaLen);
}

// ==========================================
// PLOTTING
// ==========================================

const myZeroLine = paint(horizontal_line(0), { name: 'Equilibrium', color: 'gray', thickness: 1 });

paint(myShowTenkan ? myOscTenkan : constants.empty_series, { name: 'TenkanDev', color: 'blue' });
const myKijunLinePainted = paint(myShowKijun ? myOscKijun : constants.empty_series, { name: 'KijunDev', color: 'white', thickness: 2 });
paint(myShowSpanA ? myOscSpanA : constants.empty_series, { name: 'SpanADev', color: 'green' });
paint(myShowSpanB ? myOscSpanB : constants.empty_series, { name: 'SpanBDev', color: 'orange' });

paint(myShowKijunMA ? myKijunMA : constants.empty_series, { name: 'KijunMA', color: 'yellow', thickness: 1 });

// Shading between Kijun deviation line and zero line
color_cloud(myOscKijun, series_of(0), '#2ca599', '#ee5451', 'KijunAbove', 'KijunBelow', 0.2);

// Threshold reference lines
paint(horizontal_line(myObExtreme), { name: 'OBExtreme', color: 'red', thickness: 2 });
paint(horizontal_line(myObWarning), { name: 'OBWarning', color: 'red', style: 'dotted' });
paint(horizontal_line(myOsWarning), { name: 'OSWarning', color: 'green', style: 'dotted' });
paint(horizontal_line(myOsExtreme), { name: 'OSExtreme', color: 'green', thickness: 2 });

// ==========================================
// SIGNALS (for scanner/alerts/strategy)
// ==========================================

// Crossunder: oscKijun was >= obExtreme previous bar, now < obExtreme
const myOscKijunPrev = shift(myOscKijun, 1);
const myKijunOBCross = for_every(myOscKijun, myOscKijunPrev, (_cur, _prev) => _prev >= myObExtreme && _cur < myObExtreme);

// Crossover: oscKijun was <= osExtreme previous bar, now > osExtreme
const myKijunOSCross = for_every(myOscKijun, myOscKijunPrev, (_cur, _prev) => _prev <= myOsExtreme && _cur > myOsExtreme);

register_signal(myKijunOBCross, 'Kijun OB Alert');
register_signal(myKijunOSCross, 'Kijun OS Alert');
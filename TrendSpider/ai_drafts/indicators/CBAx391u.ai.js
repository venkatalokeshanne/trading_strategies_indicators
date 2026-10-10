describe_indicator('UMUT - 5 EMA Trend', 'price');

// Each EMA has its own tab, matching the original Pine Script's groups
const myTab1 = input.tab('EMA 1');
const myLen1 = myTab1.number('Length', 9, { min: 1, max: 1000 });
const myShow1 = myTab1.boolean('Show', true);

const myTab2 = input.tab('EMA 2');
const myLen2 = myTab2.number('Length', 21, { min: 1, max: 1000 });
const myShow2 = myTab2.boolean('Show', true);

const myTab3 = input.tab('EMA 3');
const myLen3 = myTab3.number('Length', 34, { min: 1, max: 1000 });
const myShow3 = myTab3.boolean('Show', true);

const myTab4 = input.tab('EMA 4');
const myLen4 = myTab4.number('Length', 55, { min: 1, max: 1000 });
const myShow4 = myTab4.boolean('Show', true);

const myTab5 = input.tab('EMA 5');
const myLen5 = myTab5.number('Length', 200, { min: 1, max: 1000 });
const myShow5 = myTab5.boolean('Show', true);

const myPriceTab = input.tab('Price Line');
const myShowPrice = myPriceTab.boolean('Show Price Line', true);

// EMA calculations
const myEma1 = ema(close, myLen1);
const myEma2 = ema(close, myLen2);
const myEma3 = ema(close, myLen3);
const myEma4 = ema(close, myLen4);
const myEma5 = ema(close, myLen5);

// Lines (same amount of paint() calls regardless of "show" flags,
// to keep paint() calls constant across all parameter sets)
const myLine1 = paint(myShow1 ? myEma1 : constants.empty_series, { name: 'EMA1', color: '#f4c20d', thickness: 2 });
const myLine2 = paint(myShow2 ? myEma2 : constants.empty_series, { name: 'EMA2', color: '#ff8c1a', thickness: 2 });
const myLine3 = paint(myShow3 ? myEma3 : constants.empty_series, { name: 'EMA3', color: '#1ad1ea', thickness: 2 });
const myLine4 = paint(myShow4 ? myEma4 : constants.empty_series, { name: 'EMA4', color: '#2b6cff', thickness: 2 });
const myLine5 = paint(myShow5 ? myEma5 : constants.empty_series, { name: 'EMA5', color: '#d946ef', thickness: 2 });
const myPriceLine = paint(myShowPrice ? close : constants.empty_series, { name: 'PriceLine', color: 'white', thickness: 1 });

// Last value labels, equivalent to Pine's "barstate.islast" label block
const myLastIndex = close.length - 1;
paint_label_at_line(myLine1, myLastIndex, 'EMA ' + myLen1 + '  ' + myEma1[myLastIndex].toFixed(current.decimals), { background_color: '#f4c20d', color: 'black' });
paint_label_at_line(myLine2, myLastIndex, 'EMA ' + myLen2 + '  ' + myEma2[myLastIndex].toFixed(current.decimals), { background_color: '#ff8c1a', color: 'black' });
paint_label_at_line(myLine3, myLastIndex, 'EMA ' + myLen3 + '  ' + myEma3[myLastIndex].toFixed(current.decimals), { background_color: '#1ad1ea', color: 'black' });
paint_label_at_line(myLine4, myLastIndex, 'EMA ' + myLen4 + '  ' + myEma4[myLastIndex].toFixed(current.decimals), { background_color: '#2b6cff', color: 'black' });
paint_label_at_line(myLine5, myLastIndex, 'EMA ' + myLen5 + '  ' + myEma5[myLastIndex].toFixed(current.decimals), { background_color: '#d946ef', color: 'black' });
paint_label_at_line(myPriceLine, myLastIndex, 'Price  ' + close[myLastIndex].toFixed(current.decimals), { background_color: 'white', color: 'black' });

// Trend signals for scanner/alert/strategy usage:
// Bullish stacking - all EMAs ordered fast > slow (price trending up)
const myBullishStack = for_every(myEma1, myEma2, myEma3, myEma4, myEma5, (_e1, _e2, _e3, _e4, _e5) =>
	_e1 > _e2 && _e2 > _e3 && _e3 > _e4 && _e4 > _e5
);

// Bearish stacking - all EMAs ordered fast < slow (price trending down)
const myBearishStack = for_every(myEma1, myEma2, myEma3, myEma4, myEma5, (_e1, _e2, _e3, _e4, _e5) =>
	_e1 < _e2 && _e2 < _e3 && _e3 < _e4 && _e4 < _e5
);

// Price above/below the fastest EMA, often used as a quick momentum signal
const myPriceAboveFast = for_every(close, myEma1, (_c, _e1) => _c > _e1);
const myPriceBelowFast = for_every(close, myEma1, (_c, _e1) => _c < _e1);

register_signal(myBullishStack, 'Bullish EMA Stack');
register_signal(myBearishStack, 'Bearish EMA Stack');
register_signal(myPriceAboveFast, 'Price Above Fast EMA');
register_signal(myPriceBelowFast, 'Price Below Fast EMA');
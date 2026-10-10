describe_indicator('Webhook Alert Strategy Template', 'price');

// NOTE: TradingView's syminfo.mintick (true tick size of the symbol) is not
// exposed by the TrendSpider Custom JS API. As an approximation, tick size is
// derived from current.decimals (10^-decimals). This can diverge from the
// Pine Script "pip size" logic on some symbols/brokers.
const entryTab = input.tab('Demo entry');
const fastLen = entryTab.number('Fast MA length', 20, { min: 1, max: 500 });
const slowLen = entryTab.number('Slow MA length', 50, { min: 1, max: 500 });
const maType = entryTab.select('MA type', 'EMA', ['EMA', 'SMA', 'WMA', 'RMA']);

const riskTab = input.tab('Risk / exits');
const useAtrStop = riskTab.boolean('Use ATR stop distance', true);
const atrLen = riskTab.number('ATR length', 14, { min: 1, max: 500 });
const atrMult = riskTab.number('ATR stop multiplier', 1.5, { min: 0.1, max: 50 });
// shortened title (was too long for the engine's input name limit)
const fixedPips = riskTab.number('Fixed SL distance', 100, { min: 0.1, max: 100000 });
const rr = riskTab.number('Risk:Reward for TP', 2.0, { min: 0.1, max: 50 });
const tpslType = riskTab.select('TPSLTYPE tag in alert', 'PIPS', ['PIPS', 'PRICE', 'TICKS']);

const alertTab = input.tab('Webhook alert message');
const useChartSymbol = alertTab.boolean('Use chart symbol in alert', true);
// shortened title (was too long for the engine's input name limit)
const customSymbol = alertTab.text('Custom symbol', 'XAUUSD');
const vol = alertTab.number('VOL in alert message', 0.01, { min: 0.01, max: 100000 });
const showLabels = alertTab.boolean('Show entry labels', true);

// MA selection, mirrors Pine's switch on maType
function computeMA(mySrc, myLen) {
	if (maType == 'SMA') return sma(mySrc, myLen);
	if (maType == 'WMA') return wma(mySrc, myLen);
	if (maType == 'RMA') return wildma(mySrc, myLen);
	return ema(mySrc, myLen);
}

const myFast = computeMA(close, fastLen);
const mySlow = computeMA(close, slowLen);

paint(myFast, { name: 'Fast MA', color: 'teal', thickness: 1 });
paint(mySlow, { name: 'Slow MA', color: 'orange', thickness: 1 });

// crossover / crossunder, replicating ta.crossover / ta.crossunder
const myLongCond = for_every(myFast, mySlow, (_f, _s, _prev, _i) => {
	if (_i < 1) return false;
	return myFast[_i - 1] <= mySlow[_i - 1] && _f > _s;
});

const myShortCond = for_every(myFast, mySlow, (_f, _s, _prev, _i) => {
	if (_i < 1) return false;
	return myFast[_i - 1] >= mySlow[_i - 1] && _f < _s;
});

const myAtr = atr(high, low, close, atrLen);

// pip size approximated from current.decimals since syminfo.mintick is
// not available in the Custom JS API
const myTick = Math.pow(10, -current.decimals);
const myPipSize = myTick < 0.01 ? myTick * 10.0 : myTick;

const mySlDist = for_every(myAtr, (_a, _prev, _i) => useAtrStop ? _a * atrMult : fixedPips * myPipSize);
const myTpDist = mult(mySlDist, rr);
const mySlPips = div(mySlDist, myPipSize);
const myTpPips = div(myTpDist, myPipSize);

const mySymbol = useChartSymbol ? current.ticker.replace(/!/g, '') : customSymbol;

// Builds the buy/sell/close webhook messages, same format as Pine template
function buildEntryMsg(mySide, mySlPipsValue, myTpPipsValue) {
	return mySide + ',' + mySymbol + ',VOL=' + vol + ',SL=' + mySlPipsValue.toFixed(2) + ',TP=' + myTpPipsValue.toFixed(2) + ',TPSLTYPE=' + tpslType;
}

const myCloseMsg = 'CLOSE,' + mySymbol;

// Buy/Sell conditions (position state is not modeled here since this is a
// signal indicator, not an actual strategy backtester; Pine's
// "strategy.position_size" gating is approximated by using raw crossovers)
const myBuySignal = myLongCond;
const mySellSignal = myShortCond;

register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
register_signal(for_every(myBuySignal, mySellSignal, (_b, _s) => _b || _s), 'Close Signal');

// Labels on crossover bars.
// NOTE: paint_label_at_line() does not support attaching labels to lines
// painted with style 'labels_below' / 'labels_above' (that was causing the
// "Can't paint a label on that type of a line" error). To attach custom
// text per point, we instead paint a plain (hidden) 'line' style series at
// the buy/sell levels and put the label on that line instead.
const myBuyLabelSeries = for_every(myLongCond, low, (_c, _l) => _c ? _l : null);
const mySellLabelSeries = for_every(myShortCond, high, (_c, _h) => _c ? _h : null);

const myBuyLabelLine = paint(showLabels ? myBuyLabelSeries : constants.empty_series, { name: 'Buy Label', style: 'line', hidden: true, color: 'teal' });
const mySellLabelLine = paint(showLabels ? mySellLabelSeries : constants.empty_series, { name: 'Sell Label', style: 'line', hidden: true, color: 'red' });

const myBuyIndexes = indexed_points_of(showLabels ? myBuyLabelSeries : constants.empty_series);
myBuyIndexes.forEach(_p => {
	paint_label_at_line(myBuyLabelLine, _p.candleIndex, buildEntryMsg('BUY', mySlPips[_p.candleIndex], myTpPips[_p.candleIndex]), { color: 'white', background_color: 'teal', vertical_align: 'bottom' });
});

const mySellIndexes = indexed_points_of(showLabels ? mySellLabelSeries : constants.empty_series);
mySellIndexes.forEach(_p => {
	paint_label_at_line(mySellLabelLine, _p.candleIndex, buildEntryMsg('SELL', mySlPips[_p.candleIndex], myTpPips[_p.candleIndex]), { color: 'white', background_color: 'red', vertical_align: 'top' });
});
describe_indicator('RSI Mean Reversion', 'lower');

// Groups mirror the Pine script's "RSI Settings" / "Strategy" / "Visuals" groups
const rsiTab = input.tab('RSI Settings');
const myRsiLength = rsiTab.number('RSI Period', 3, { min: 1, max: 50 });
const myOversold = rsiTab.number('Oversold Level', 40, { min: 5, max: 49 });
const myOverbought = rsiTab.number('Overbought Level', 70, { min: 51, max: 95 });

const stratTab = input.tab('Strategy');
const myTradeDirection = stratTab.select('Trade Direction', 'Both', ['Long Only', 'Short Only', 'Both']);
// Note: "Await Bar Confirmation" has no equivalent here, since Custom JS scripts
// only ever evaluate confirmed (closed) bars - there is no intrabar repaint state
// to await, so this behaves like awaitBarConfirmation = true always.

const visualTab = input.tab('Visuals');
const myShowSignals = visualTab.boolean('Show Buy/Sell Labels', true);
const myShowRSIBackground = visualTab.boolean('Show RSI Background Shading', true);

// RSI calculation
const myRsi = rsi(close, myRsiLength);
const myOversoldLine = horizontal_line(myOversold);
const myOverboughtLine = horizontal_line(myOverbought);

// Crossover / Crossunder logic (replicating ta.crossover / ta.crossunder)
const myLongSignal = for_every(myRsi, (_r, _prev, _i) => {
	if (_i < 1) return false;
	return myRsi[_i - 1] <= myOversold && _r > myOversold;
});

const myShortSignal = for_every(myRsi, (_r, _prev, _i) => {
	if (_i < 1) return false;
	return myRsi[_i - 1] >= myOverbought && _r < myOverbought;
});

// Trade direction filters, mirroring canLong / canShort used for strategy entries
const myCanLong = myTradeDirection === 'Long Only' || myTradeDirection === 'Both';
const myCanShort = myTradeDirection === 'Short Only' || myTradeDirection === 'Both';

const myLongEntrySignal = for_every(myLongSignal, _l => _l && myCanLong);
const myShortEntrySignal = for_every(myShortSignal, _s => _s && myCanShort);

// Paint RSI with oversold/overbought reference lines
const myRsiPainted = paint(myRsi, { name: 'RSI', color: '#4DA3FF', thickness: 2 });
paint(myOversoldLine, { name: 'Oversold', color: 'gray', style: 'dotted' });
paint(myOverboughtLine, { name: 'Overbought', color: 'gray', style: 'dotted' });

// Approximate "background shading in extreme zones" using a filled cloud,
// since bgcolor() is not available in Custom JS Scripting API
const myOversoldZone = myShowRSIBackground ? for_every(myRsi, _r => _r < myOversold ? _r : null) : constants.empty_series;
const myOverboughtZone = myShowRSIBackground ? for_every(myRsi, _r => _r > myOverbought ? _r : null) : constants.empty_series;

color_cloud(myOversoldZone, myOversoldLine, '#2ca599', '#2ca599', 'OversoldZone', 'OversoldZone2', 0.15);
color_cloud(myOverboughtZone, myOverboughtLine, '#ee5451', '#ee5451', 'OverboughtZone', 'OverboughtZone2', 0.15);

// Buy/Sell labels on the RSI line (approximating plotshape labels)
const myBuyLabelSeries = myShowSignals ? for_every(myLongSignal, (_l, _p, _i) => _l ? myRsi[_i] : null) : constants.empty_series;
const mySellLabelSeries = myShowSignals ? for_every(myShortSignal, (_s, _p, _i) => _s ? myRsi[_i] : null) : constants.empty_series;

paint(myBuyLabelSeries, { name: 'BuySignal', style: 'labels_below', color: 'green' });
paint(mySellLabelSeries, { name: 'SellSignal', style: 'labels_above', color: 'red' });

// Signals for Scanner / Alerts / Strategy Tester
register_signal(myLongSignal, 'RSI MR Buy');
register_signal(myShortSignal, 'RSI MR Sell');
register_signal(for_every(myLongSignal, myShortSignal, (_l, _s) => _l || _s), 'RSI MR Any Signal');
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
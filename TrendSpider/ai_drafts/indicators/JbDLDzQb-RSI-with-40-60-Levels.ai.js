describe_indicator('RSI with 40/60 Levels', 'lower');

// RSI Settings
const myRsiTab = input.tab('RSI Settings');
const myRsiLength = myRsiTab.number('RSI Length', 14, { min: 1, max: 200 });
const myPriceSource = myRsiTab.select('Source', 'close', constants.price_source_options);

// Smoothing
const mySmoothingTab = input.tab('Smoothing');
const myMaType = mySmoothingTab.select('MA Type', 'SMA', ['SMA', 'EMA', 'WMA', 'RMA']);
const myMaLength = mySmoothingTab.number('MA Length', 5, { min: 1, max: 200 });

// Zone Colors
const myZoneTab = input.tab('Zone Colors');
const myZone4060Color = myZoneTab.color('40-60 Zone Color', 'rgba(121,114,114,0.15)');
const myZoneOuterColor = myZoneTab.color('30-40 / 60-70 Zone Color', 'rgba(123,31,162,0.10)');

const myPrice = market[myPriceSource];

// RSI value. Pine's ta.rma-based RSI with up==0/down==0 edge cases is
// mathematically equivalent to the built-in rsi() function here.
const myRsiValue = rsi(myPrice, myRsiLength);

// MA of RSI, following the chosen smoothing method
function myComputeMA(mySeries, myLength, myType) {
	if (myType === 'EMA') return ema(mySeries, myLength);
	if (myType === 'WMA') return wma(mySeries, myLength);
	if (myType === 'RMA') return wildma(mySeries, myLength);
	return sma(mySeries, myLength);
}
const myMaValue = myComputeMA(myRsiValue, myMaLength, myMaType);

// MA color: red when MA above RSI, green when MA below RSI
const myMaColor = for_every(myMaValue, myRsiValue, (_ma, _rsi) => _ma > _rsi ? 'red' : 'green');

// Reference levels
const myLevel70 = horizontal_line(70);
const myLevel60 = horizontal_line(60);
const myLevel50 = horizontal_line(50);
const myLevel40 = horizontal_line(40);
const myLevel30 = horizontal_line(30);

const myRsiLinePainted = paint(myRsiValue, { name: 'RSI', color: '#7E57C2', thickness: 2 });
paint(myMaValue, { name: 'RSIMA', color: myMaColor, thickness: 1 });

const myLine70Painted = paint(myLevel70, { name: 'Overbought70', color: 'rgba(255,0,0,0.5)', style: 'line', thickness: 1 });
const myLine60Painted = paint(myLevel60, { name: 'Upper60', color: 'rgba(255,165,0,0.8)', style: 'line', thickness: 1 });
paint(myLevel50, { name: 'Midline50', color: 'rgba(128,128,128,0.3)', style: 'line', thickness: 1 });
const myLine40Painted = paint(myLevel40, { name: 'Lower40', color: 'rgba(255,165,0,0.8)', style: 'line', thickness: 1 });
const myLine30Painted = paint(myLevel30, { name: 'Oversold30', color: 'rgba(0,128,0,0.5)', style: 'line', thickness: 1 });

// Zone shading (single color fills; gradient top/bottom colors from Pine
// are not supported by fill() here, approximated with flat opacity)
fill(myLine40Painted, myLine60Painted, myZone4060Color, 1, 'Zone4060');
fill(myLine60Painted, myLine70Painted, myZoneOuterColor, 1, 'Zone6070');
fill(myLine30Painted, myLine40Painted, myZoneOuterColor, 1, 'Zone3040');

// Approximation of the gradient fills hugging the RSI line, using
// the midline as the other border (gradient coloring not supported,
// flat semi transparent fills used instead)
const myOverboughtAnchor = for_every(myRsiValue, _rsi => _rsi > 50 ? _rsi : 50);
const myOversoldAnchor = for_every(myRsiValue, _rsi => _rsi < 50 ? _rsi : 50);
const myOverboughtPainted = paint(myOverboughtAnchor, { name: 'OverboughtFillHelper', hidden: true });
const myOversoldPainted = paint(myOversoldAnchor, { name: 'OversoldFillHelper', hidden: true });
const myMidlineHelperPainted = paint(series_of(50), { name: 'MidlineHelper', hidden: true });
fill(myOverboughtPainted, myMidlineHelperPainted, 'green', 0.2, 'OverboughtFill');
fill(myOversoldPainted, myMidlineHelperPainted, 'red', 0.2, 'OversoldFill');

// Scanner / Alert / Strategy signals
const myRsiCrossAbove60 = for_every(myRsiValue, (_rsi, _prev, _idx) => _idx > 0 && _rsi > 60 && myRsiValue[_idx - 1] <= 60);
const myRsiCrossBelow40 = for_every(myRsiValue, (_rsi, _prev, _idx) => _idx > 0 && _rsi < 40 && myRsiValue[_idx - 1] >= 40);
const myRsiOverbought70 = for_every(myRsiValue, _rsi => _rsi > 70);
const myRsiOversold30 = for_every(myRsiValue, _rsi => _rsi < 30);
const myMaAboveRsi = for_every(myMaValue, myRsiValue, (_ma, _rsi) => _ma > _rsi);
const myMaBelowRsi = for_every(myMaValue, myRsiValue, (_ma, _rsi) => _ma < _rsi);

register_signal(myRsiCrossAbove60, 'RSI Cross Above 60');
register_signal(myRsiCrossBelow40, 'RSI Cross Below 40');
register_signal(myRsiOverbought70, 'RSI Overbought Above 70');
register_signal(myRsiOversold30, 'RSI Oversold Below 30');
register_signal(myMaAboveRsi, 'RSI MA Above RSI');
register_signal(myMaBelowRsi, 'RSI MA Below RSI');
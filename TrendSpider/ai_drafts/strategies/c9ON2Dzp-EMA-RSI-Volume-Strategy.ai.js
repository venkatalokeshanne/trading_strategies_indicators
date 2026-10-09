describe_indicator('EMA RSI Volume Strategy', 'lower');

// EMA1 settings
const myEma1Length = input.number('EMA1 Length', 9, { min: 1, max: 500 });
const myEma1 = ema(close, myEma1Length);

// EMA2 settings
const myEma2Length = input.number('EMA2 Length', 26, { min: 1, max: 500 });
const myEma2 = ema(close, myEma2Length);

// RSI settings
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 500 });
const myRsi = rsi(close, myRsiLength);

// Indicator settings
const myGreenMinRsi = input.number('Green RSI Min', 50, { min: 0, max: 100 });
const myGreenMaxRsi = input.number('Green RSI Max', 70, { min: 0, max: 100 });
const myNumberOfBars = input.number('Number of Bars', 3, { min: 1, max: 500 });
const myVolumeMultiplier = input.number('Volume Multiplier', 1, { min: 1, max: 100 });

// Market conditions, exactly mirroring Pine logic
const myLongCondition = for_every(myEma1, myEma2, myRsi, (_e1, _e2, _r) => _e1 > _e2 && _r > myGreenMinRsi && _r < myGreenMaxRsi);
const myShortCondition = for_every(myEma1, myEma2, myRsi, (_e1, _e2, _r) => _e1 < _e2 && _r > myGreenMinRsi && _r < myGreenMaxRsi);

// Pine's "ta.sma(volume[1], numberOfBars)" means SMA of volume shifted back by 1 bar
const myShiftedVolume = shift(volume, 1);
const myAverageVolume = sma(myShiftedVolume, myNumberOfBars);
const myHighVolume = for_every(volume, myAverageVolume, (_v, _avg) => _v >= _avg * myVolumeMultiplier);

const myBuyCondition = for_every(myLongCondition, myHighVolume, (_l, _h) => _l && _h);
const mySellCondition = for_every(myShortCondition, myHighVolume, (_s, _h) => _s && _h);

// Market condition reference line (close + 10), colored teal/red like Pine's finalColor
const myMarketConditionLine = add(close, 10);
const myMarketConditionColor = for_every(myLongCondition, _l => _l ? 'teal' : 'red');

// Paint EMAs on the price axis (forced since this is a lower indicator)
paint(myEma1, { name: 'EMA1', color: 'green', thickness: 2, forceUsePriceAxis: true });
paint(myEma2, { name: 'EMA2', color: 'orange', thickness: 2, forceUsePriceAxis: true });
paint(myMarketConditionLine, { name: 'Market Condition', color: myMarketConditionColor, thickness: 2, forceUsePriceAxis: true });

// Paint RSI with reference lines and fill
const myUpperLine = paint(horizontal_line(70), { name: 'Upper Line', color: 'gray', style: 'dotted' });
const myLowerLine = paint(horizontal_line(30), { name: 'Lower Line', color: 'gray', style: 'dotted' });
paint(horizontal_line(50), { name: 'Middle Line', color: 'gray', style: 'dotted' });
paint(myRsi, { name: 'RSI', color: 'blue' });
fill(myUpperLine, myLowerLine, 'blue', 0.05);

// Signals for scanner/alerts/strategy tester
register_signal(myLongCondition, 'Long Condition');
register_signal(myShortCondition, 'Short Condition');
register_signal(myBuyCondition, 'Buy Entry');
register_signal(mySellCondition, 'Sell Entry');
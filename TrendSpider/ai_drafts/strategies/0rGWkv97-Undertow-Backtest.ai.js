describe_indicator('Undertow Backtest', 'lower');

// ───────────── Inputs ─────────────
const myWtTab = input.tab('WaveTrend');
const mySrcOpt = myWtTab.select('WT Source', 'hlc3', ['hlc3', 'hl2', 'close']);
const myN1 = myWtTab.number('WT Channel Length', 9, { min: 1, max: 100 });
const myN2 = myWtTab.number('WT Average Length', 12, { min: 1, max: 100 });
const mySigLen = myWtTab.number('WT Signal Smoothing', 3, { min: 1, max: 100 });
const mySigType = myWtTab.select('WT Signal Type', 'SMA', ['SMA', 'EMA']);

const myLevelsTab = input.tab('Levels');
// shortened input names to satisfy the platform's input name length limit
const myObLevel = myLevelsTab.number('Overbought', 60, { min: -100, max: 100 });
const myOsLevel = myLevelsTab.number('Oversold', -40, { min: -100, max: 100 });

const myStrategyTab = input.tab('Strategy');
const myBuyMode = myStrategyTab.select('Buy On', 'Strong dots only', ['Strong dots only', 'All dots']);
const mySellMode = myStrategyTab.select('Sell On', 'Strong dots only', ['Strong dots only', 'All dots']);

// ───────────── WaveTrend ─────────────
const myAp = mySrcOpt === 'hlc3' ? hlc3 : mySrcOpt === 'hl2' ? hl2 : close;
const myEsa = ema(myAp, myN1);
const myAbsDiff = for_every(myAp, myEsa, (_a, _e) => Math.abs(_a - _e));
const myDe = ema(myAbsDiff, myN1);
const myCi = for_every(myAp, myEsa, myDe, (_a, _e, _d) => (_a - _e) / (0.015 * (_d === 0 ? 1e-10 : _d)));
const myWt1 = ema(myCi, myN2);
const myWt2 = mySigType === 'SMA' ? sma(myWt1, mySigLen) : ema(myWt1, mySigLen);

// ───────────── Crossovers ─────────────
// crossUp: wt1 crosses above wt2; crossDown: wt1 crosses below wt2
const myWt1Prev = shift(myWt1, 1);
const myWt2Prev = shift(myWt2, 1);
const myCrossUp = for_every(myWt1, myWt2, myWt1Prev, myWt2Prev, (_w1, _w2, _w1p, _w2p) => {
	return _w1p <= _w2p && _w1 > _w2;
});
const myCrossDown = for_every(myWt1, myWt2, myWt1Prev, myWt2Prev, (_w1, _w2, _w1p, _w2p) => {
	return _w1p >= _w2p && _w1 < _w2;
});

const myBuyStrong = for_every(myCrossUp, myWt2, (_cu, _w2) => _cu && _w2 <= myOsLevel);
const mySellStrong = for_every(myCrossDown, myWt2, (_cd, _w2) => _cd && _w2 >= myObLevel);

const myLongEntry = myBuyMode === 'All dots' ? myCrossUp : myBuyStrong;
const myLongExit = mySellMode === 'All dots' ? myCrossDown : mySellStrong;

// ───────────── Visuals: bound lines ─────────────
paint(horizontal_line(myObLevel), { name: 'UpperBound', color: 'gray', style: 'line', thickness: 1 });
paint(horizontal_line(myOsLevel), { name: 'LowerBound', color: 'gray', style: 'line', thickness: 1 });
paint(horizontal_line(100), { name: 'Top', color: 'silver', style: 'dotted', thickness: 1 });
paint(horizontal_line(0), { name: 'Zero', color: 'silver', style: 'line', thickness: 1 });
paint(horizontal_line(-100), { name: 'Bottom', color: 'silver', style: 'dotted', thickness: 1 });

// ───────────── Visuals: WaveTrend lines ─────────────
paint(myWt1, { name: 'WTWave1', color: '#80f7ff', style: 'line', thickness: 2 });
paint(myWt2, { name: 'WTWave2', color: '#3949ab', style: 'line', thickness: 2 });

// ───────────── Visuals: dots ─────────────
const myBuyStrongDots = for_every(myBuyStrong, myWt2, (_b, _w2) => _b ? _w2 : null);
const mySellStrongDots = for_every(mySellStrong, myWt2, (_s, _w2) => _s ? _w2 : null);
const myBuyWeakDots = for_every(myCrossUp, myBuyStrong, myWt2, (_cu, _b, _w2) => (_cu && !_b) ? _w2 : null);
const mySellWeakDots = for_every(myCrossDown, mySellStrong, myWt2, (_cd, _s, _w2) => (_cd && !_s) ? _w2 : null);

paint(myBuyStrongDots, { name: 'BuyStrong', color: '#00a050', style: 'labels_below', thickness: 2 });
paint(mySellStrongDots, { name: 'SellStrong', color: '#e60026', style: 'labels_above', thickness: 2 });
paint(myBuyWeakDots, { name: 'BuyWeak', color: '#66c99a', style: 'labels_below', thickness: 1 });
paint(mySellWeakDots, { name: 'SellWeak', color: '#f08a99', style: 'labels_above', thickness: 1 });

// ───────────── Signals for scanner/strategy/alerts ─────────────
register_signal(myLongEntry, 'Long Entry');
register_signal(myLongExit, 'Long Exit');
register_signal(myBuyStrong, 'Buy Strong Dot');
register_signal(mySellStrong, 'Sell Strong Dot');
register_signal(myCrossUp, 'Any Buy Dot');
register_signal(myCrossDown, 'Any Sell Dot');
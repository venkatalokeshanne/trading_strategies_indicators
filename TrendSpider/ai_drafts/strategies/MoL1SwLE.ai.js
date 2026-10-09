describe_indicator('3 Strategy Switch - Range Trend Breakout', 'price');

// ============================================================
// This indicator reproduces the Pine Script logic as closely
// as the TrendSpider Custom JS API allows. Pine's strategy
// engine (position tracking, strategy.entry/exit, bgcolor,
// table) does not exist here, so entries are exposed as
// signals/overlays instead of actual trades. See notes below.
// ============================================================

const myTab1 = input.tab('Indicators');
const myRsiLen = myTab1.number('RSI Length', 14, { min: 1, max: 200 });
const myAdxLen = myTab1.number('ADX Length', 14, { min: 1, max: 200 });
const myBbRow = myTab1.row();
const myBbLen = myBbRow.number('Bollinger Length', 20, { min: 1, max: 200 });
const myBbMult = myBbRow.number('Bollinger Mult', 2.0, { min: 0.1, max: 10, step: 0.1 });
const myAtrLen = myTab1.number('ATR Length', 14, { min: 1, max: 200 });

const myTab2 = input.tab('Risk');
const myRiskRow = myTab2.row();
const myRiskPct = myRiskRow.number('Risk Per Trade %', 1.0, { min: 0.5, max: 100, step: 0.1 });
const myRrRatio = myRiskRow.number('Reward Risk Ratio', 2.5, { min: 1.5, max: 20, step: 0.1 });

// ==================== Core indicators ====================
const myRsi = rsi(close, myRsiLen);
const myAdxObj = indicators.adx(myAdxLen);
const myAdx = myAdxObj.adx;

const myBbMid = sma(close, myBbLen);
const myBbDev = mult(stdev(close, myBbLen), myBbMult);
const myBbUpper = add(myBbMid, myBbDev);
const myBbLower = sub(myBbMid, myBbDev);

const myAtr = atr(high, low, close, myAtrLen);
const myVolMa = sma(volume, 20);
const myEma50 = ema(close, 50);
const myEma200 = ema(close, 200);

// ==================== Crossover helpers ====================
// Pine's ta.crossover(a, b) == (a[0] > b[0]) and (a[1] <= b[1])
const myCrossCloseBbUpper = for_every(
	close, myBbUpper, shift(close, 1), shift(myBbUpper, 1),
	(_c, _u, _pc, _pu) => (_c > _u) && (_pc <= _pu)
);

const myCrossEma50Ema200 = for_every(
	myEma50, myEma200, shift(myEma50, 1), shift(myEma200, 1),
	(_e50, _e200, _pe50, _pe200) => (_e50 > _e200) && (_pe50 <= _pe200)
);

// ==================== Market regime ====================
const myIsRanging = for_every(
	myAdx, close, myBbLower, myBbUpper,
	(_adx, _c, _lo, _hi) => (_adx < 25) && (_c > _lo) && (_c < _hi)
);

const myIsTrending = for_every(
	myAdx, close, myEma50, myEma200,
	(_adx, _c, _e50, _e200) => (_adx > 25) && (_c > _e50) && (_e50 > _e200)
);

const myIsBreakout = for_every(
	volume, myVolMa, myCrossCloseBbUpper, myAdx,
	(_v, _vma, _cross, _adx) => (_v > _vma * 1.8) && _cross && (_adx > 20)
);

// ==================== Entry conditions ====================
const myRangeLong = for_every(
	myIsRanging, myRsi, close, myBbLower, volume, myVolMa,
	(_rng, _rsi, _c, _bl, _v, _vma) => _rng && (_rsi < 35) && (_c <= _bl * 1.01) && (_v > _vma * 1.2)
);

const myTrendLong = for_every(
	myIsTrending, myCrossEma50Ema200, myRsi, close, myBbMid,
	(_trend, _cross, _rsi, _c, _mid) => _trend && _cross && (_rsi > 50) && (_c > _mid)
);

const myBreakoutLong = for_every(
	myIsBreakout, myRsi, shift(close, 1), shift(myBbUpper, 1),
	(_brk, _rsi, _pc, _pu) => _brk && (_rsi > 50) && (_pc < _pu)
);

const myAnyLongEntry = for_every(
	myRangeLong, myTrendLong, myBreakoutLong,
	(_r, _t, _b) => _r || _t || _b
);

// ==================== Stop loss / take profit (per entry bar) ====================
// Pine tracks a live position (strategy.position_avg_price). Without a real
// strategy engine we approximate SL/TP using the entry bar's close as the
// assumed average entry price.
const myStopLoss = for_every(
	myAnyLongEntry, close, myAtr,
	(_entry, _c, _atr) => _entry ? (_c - _atr * 1.5) : null
);

const myTakeProfit = for_every(
	myAnyLongEntry, close, myStopLoss,
	(_entry, _c, _sl) => _entry ? (_c + (_c - _sl) * myRrRatio) : null
);

// ==================== Visuals ====================
// bgcolor() has no direct equivalent; approximated via candle coloring.
const myRegimeColor = for_every(
	myIsRanging, myIsTrending, myIsBreakout,
	(_rng, _trend, _brk) => _rng ? 'rgba(76,175,80,0.35)' : (_trend ? 'rgba(66,133,244,0.35)' : (_brk ? 'rgba(255,152,0,0.35)' : null))
);
color_candles(myRegimeColor);

paint(myEma50, { name: 'EMA50', color: '#42A5F5', thickness: 2 });
paint(myEma200, { name: 'EMA200', color: '#AB47BC', thickness: 2 });
paint(myBbUpper, { name: 'BB Upper', color: '#9E9E9E', style: 'dotted' });
paint(myBbMid, { name: 'BB Mid', color: '#616161', style: 'dotted' });
paint(myBbLower, { name: 'BB Lower', color: '#9E9E9E', style: 'dotted' });
paint(myStopLoss, { name: 'Stop Loss', color: '#EF5350', style: 'ladder' });
paint(myTakeProfit, { name: 'Take Profit', color: '#26A69A', style: 'ladder' });

// ==================== Scanner / Strategy signals ====================
register_signal(myRangeLong, 'Range Long Entry');
register_signal(myTrendLong, 'Trend Long Entry');
register_signal(myBreakoutLong, 'Breakout Long Entry');
register_signal(myAnyLongEntry, 'Any Long Entry');
register_signal(myIsRanging, 'Market Is Ranging');
register_signal(myIsTrending, 'Market Is Trending');
register_signal(myIsBreakout, 'Market Is Breakout');
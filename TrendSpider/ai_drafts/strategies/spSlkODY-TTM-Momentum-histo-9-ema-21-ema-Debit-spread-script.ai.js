describe_indicator('TTM Squeeze + EMA Cross Signal', 'price');

// --- Inputs ---
const myLength = input.number('Squeeze Length', 20, { min: 1, max: 200 });
const myMultK = input.number('Keltner Multiplier', 2.0, { min: 0.1, max: 10 });
const myMultB = input.number('Bollinger Multiplier', 1.5, { min: 0.1, max: 10 });

// --- Bollinger Bands ---
const myBasis = sma(close, myLength);
const myDev = mult(stdev(close, myLength), myMultB);
const myUpperBB = add(myBasis, myDev);
const myLowerBB = sub(myBasis, myDev);

// --- Keltner Channel ---
const myMa = sma(close, myLength);
// true range approximated via atr() with length 1 (equivalent to raw TR)
const myRange = atr(high, low, close, 1);
const myRangeEma = ema(myRange, myLength);
const myUpperKC = add(myMa, mult(myRangeEma, myMultK));
const myLowerKC = sub(myMa, mult(myRangeEma, myMultK));

// --- Squeeze state ---
const mySqzOn = for_every(myLowerBB, myLowerKC, myUpperBB, myUpperKC, (_lbb, _lkc, _ubb, _ukc) => (_lbb > _lkc) && (_ubb < _ukc));
const mySqzOff = for_every(myLowerBB, myLowerKC, myUpperBB, myUpperKC, (_lbb, _lkc, _ubb, _ukc) => (_lbb < _lkc) && (_ubb > _ukc));

// --- Momentum (linear regression of close - avg) ---
const myHighestH = highest(high, myLength);
const myLowestL = lowest(low, myLength);
const mySmaClose = sma(close, myLength);
const myAvgHL = div(add(myHighestH, myLowestL), 2);
const myAvg = div(add(myAvgHL, mySmaClose), 2);
const myMomSource = sub(close, myAvg);
const myMom = linreg(myMomSource, myLength);

const myMomPrev = shift(myMom, 1);
const myIsFullBlue = for_every(myMom, myMomPrev, (_m, _mp) => _m !== null && _mp !== null && _m > 0 && _m > _mp);

// --- EMA Cross ---
const myEma9 = ema(close, 9);
const myEma21 = ema(close, 21);
// emaCross simplifies to "ema9 >= ema21" since crossover implies that condition
const myEmaCross = for_every(myEma9, myEma21, (_e9, _e21) => _e9 >= _e21);

// --- Squeeze release: sqzOn[2] and sqzOff[1] and sqzOff[0] ---
const mySqzOn2 = shift(mySqzOn, 2);
const mySqzOff1 = shift(mySqzOff, 1);
const mySqzRelease = for_every(mySqzOn2, mySqzOff1, mySqzOff, (_on2, _off1, _off0) => Boolean(_on2) && Boolean(_off1) && Boolean(_off0));

// --- Combined long signal ---
const myLongSignal = for_every(mySqzRelease, myEmaCross, myIsFullBlue, (_r, _c, _b) => Boolean(_r) && Boolean(_c) && Boolean(_b));

// --- Plotting EMAs ---
paint(myEma9, { name: 'EMA9', color: '#2E86DE', thickness: 2 });
paint(myEma21, { name: 'EMA21', color: '#EE5253', thickness: 2 });

// --- Long signal shape (triangle up below bar) ---
const myLongSignalMarks = for_every(myLongSignal, low, (_sig, _l) => _sig ? _l : null);
paint(myLongSignalMarks, { name: 'LongSignal', style: 'labels_below', color: '#10AC84', thickness: 2 });

// --- Register signals for scanners/alerts/strategy ---
register_signal(myLongSignal, 'TTM Squeeze Long Signal');
register_signal(mySqzOn, 'Squeeze On');
register_signal(mySqzOff, 'Squeeze Off');

// --- Simple strategy-style SMA(14)/SMA(28) cross signals ---
const mySma14 = sma(close, 14);
const mySma28 = sma(close, 28);
const mySma14Prev = shift(mySma14, 1);
const mySma28Prev = shift(mySma28, 1);

const myLongCondition = for_every(mySma14, mySma28, mySma14Prev, mySma28Prev,
	(_s14, _s28, _s14p, _s28p) => _s14 > _s28 && _s14p <= _s28p);
const myShortCondition = for_every(mySma14, mySma28, mySma14Prev, mySma28Prev,
	(_s14, _s28, _s14p, _s28p) => _s14 < _s28 && _s14p >= _s28p);

register_signal(myLongCondition, 'Strategy Long Entry');
register_signal(myShortCondition, 'Strategy Short Entry');
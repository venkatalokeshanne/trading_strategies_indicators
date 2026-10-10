describe_indicator('Volatility Surge Strategy VSS', 'lower');

const myTab = input.tab('Volatility Index');
const myLookback = myTab.number('Lookback Period', 22, { min: 5, max: 200 });

const myBbTab = input.tab('BB Filter');
const myBbPeriod = myBbTab.number('BB Period', 20, { min: 5, max: 500 });
const myBbMult = myBbTab.number('BB Multiplier', 2.0, { min: 0.5, max: 5, step: 0.1 });

// ATR based SL/TP levels are computed for reference only; this platform's
// Custom JS API does not support broker-style strategy.entry/exit orders,
// so actual trade execution logic from Pine can't be reproduced here.
// Use the registered signals below with the Strategy Tester component instead.
const myRmTab = input.tab('Risk Management');
const myAtrPeriod = myRmTab.number('ATR Period', 14, { min: 1, max: 500 });
const myAtrMult = myRmTab.number('SL ATR Multiplier', 1.5, { min: 0.5, max: 5, step: 0.1 });
const myRrRatio = myRmTab.number('Risk Reward Ratio', 1.5, { min: 0.5, max: 5, step: 0.1 });

// Volatility Index: drop depth% from highest close over lookback to current low
const myHighestClose = highest(close, myLookback);
const myVi = mult(div(sub(myHighestClose, low), myHighestClose), 100);

// Bollinger Band filter on the VI series
const myViSma = sma(myVi, myBbPeriod);
const myViStdev = stdev(myVi, myBbPeriod);
const myViUpper = add(myViSma, mult(myViStdev, myBbMult));

// Conditions
const myIsHigh = for_every(myVi, myViUpper, (_vi, _upper) => _vi >= _upper);
const myIsBull = for_every(close, open, (_c, _o) => _c > _o);

const myIsHighPrev = shift(myIsHigh, 1);
const myWasBullPrev = shift(myIsBull, 1);

const myBullSwitch = for_every(myIsHighPrev, myIsHigh, myIsBull, myWasBullPrev, (_hp, _h, _b, _wb) => Boolean(_hp && _h && _b && !_wb));
const myBearSwitch = for_every(myIsHighPrev, myIsHigh, myIsBull, myWasBullPrev, (_hp, _h, _b, _wb) => Boolean(_hp && _h && !_b && _wb));

// ATR for SL/TP reference values (not used for order placement)
const myAtr = atr(high, low, close, myAtrPeriod);
const myBuyStop = sub(close, mult(myAtr, myAtrMult));
const myBuyLimit = add(close, mult(myAtr, myAtrMult, myRrRatio));
const mySellStop = add(close, mult(myAtr, myAtrMult));
const mySellLimit = sub(close, mult(myAtr, myAtrMult, myRrRatio));

// Histogram color: spike bullish = yellow, spike bearish = red, else gray
const myBarColor = for_every(myIsHigh, myIsBull, (_h, _b) => _h ? (_b ? 'rgb(255,220,0)' : 'rgb(255,60,60)') : 'rgb(110,110,110)');

paint(myVi, { name: 'VI', style: 'column', color: myBarColor, thickness: 4 });
paint(myViUpper, { name: 'Upper Band', color: '#00e0e0', thickness: 1 });
paint(myViSma, { name: 'Mid SMA', color: '#999999', thickness: 1 });

const myBullMarks = for_every(myBullSwitch, low, (_s, _l) => _s ? _l : null);
const myBearMarks = for_every(myBearSwitch, high, (_s, _h) => _s ? _h : null);

paint(myBullMarks, { name: 'Bull Switch', style: 'labels_below', color: '#ffd700', thickness: 3 });
paint(myBearMarks, { name: 'Bear Switch', style: 'labels_above', color: '#ff3030', thickness: 3 });

register_signal(myIsHigh, 'High Volatility');
register_signal(myBullSwitch, 'Bullish Switch');
register_signal(myBearSwitch, 'Bearish Switch');
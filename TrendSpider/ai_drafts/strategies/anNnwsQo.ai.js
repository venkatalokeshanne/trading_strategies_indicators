describe_indicator('SuperTrend BB Strategy STB', 'price');

// ─── Inputs ──────────────────────────────────────────────────
const stTab = input.tab('SuperTrend');
const myStAtrLength = stTab.number('ATR Period', 10, { min: 1, max: 100 });
const myStMultiplier = stTab.number('Multiplier', 3.0, { min: 0.1, max: 20, step: 0.1 });

const bbTab = input.tab('Bollinger Bands');
const myBbPeriod = bbTab.number('BB Period (SMA Filter)', 50, { min: 1, max: 500 });
const myBbMultiplier = bbTab.number('BB Multiplier', 2.0, { min: 0.1, max: 10, step: 0.1 });

const riskTab = input.tab('Risk Management');
const myRiskRow = riskTab.row();
const mySlAtrMultiplier = myRiskRow.number('SL ATR Multiplier', 1.5, { min: 0.1, max: 10, step: 0.1 });
const myRrRatio = myRiskRow.number('RR Ratio', 1.5, { min: 0.1, max: 10, step: 0.1 });

// ─── SuperTrend (built-in matches ta.supertrend logic) ────────
const mySupertrend = supertrend(myStAtrLength, myStMultiplier, false);
// supertrend() returns the line itself; direction is derived by comparing
// the line position relative to close (line below close => uptrend/-1,
// line above close => downtrend/1), matching Pine's dir semantics.
const myDirection = for_every(close, mySupertrend, (_close, _st) => (_st < _close ? -1 : 1));

// ─── Bollinger Bands ───────────────────────────────────────────
const myBbMid = sma(close, myBbPeriod);
const myBbDev = stdev(close, myBbPeriod);
const myBbUpper = add(myBbMid, mult(myBbDev, myBbMultiplier));
const myBbLower = sub(myBbMid, mult(myBbDev, myBbMultiplier));

// ─── ATR(14) for risk management ───────────────────────────────
const myAtr14 = atr(high, low, close, 14);

// ─── Signals (direction flip + close vs BB mid filter) ─────────
// st_up: direction flips from 1 (down) to -1 (up)
// st_down: direction flips from -1 (up) to 1 (down)
const myStUp = for_every(myDirection, (_dir, _p, _idx) => _idx > 0 ? (_dir === -1 && myDirection[_idx - 1] === 1) : false);
const myStDown = for_every(myDirection, (_dir, _p, _idx) => _idx > 0 ? (_dir === 1 && myDirection[_idx - 1] === -1) : false);

const myBuySignal = for_every(myStUp, close, myBbMid, (_up, _close, _mid) => _up && _close > _mid);
const mySellSignal = for_every(myStDown, close, myBbMid, (_down, _close, _mid) => _down && _close < _mid);

// ─── Stop loss / Take profit levels (for reference, computed per bar) ──
const myLongStopLoss = sub(close, mult(myAtr14, mySlAtrMultiplier));
const myLongTakeProfit = for_every(close, myLongStopLoss, (_close, _sl) => _close + (_close - _sl) * myRrRatio);

const myShortStopLoss = add(close, mult(myAtr14, mySlAtrMultiplier));
const myShortTakeProfit = for_every(close, myShortStopLoss, (_close, _sl) => _close - (_sl - _close) * myRrRatio);

// ─── Painting ────────────────────────────────────────────────────
const mySupertrendColor = for_every(myDirection, _dir => (_dir < 0 ? 'teal' : 'red'));
const mySupertrendPainted = paint(mySupertrend, { name: 'SuperTrend', color: mySupertrendColor, thickness: 2 });

const myBbUpperPainted = paint(myBbUpper, { name: 'BB Upper', color: 'rgba(70,130,220,0.5)', thickness: 1 });
paint(myBbMid, { name: 'BB Mid', color: 'orange', thickness: 1 });
const myBbLowerPainted = paint(myBbLower, { name: 'BB Lower', color: 'rgba(70,130,220,0.5)', thickness: 1 });
fill(myBbUpperPainted, myBbLowerPainted, 'blue', 0.08);

const myBuyMarks = for_every(myBuySignal, (_buy, _p, _idx) => (_buy ? low[_idx] : null));
const mySellMarks = for_every(mySellSignal, (_sell, _p, _idx) => (_sell ? high[_idx] : null));

paint(myBuyMarks, { name: 'BUY', style: 'labels_below', color: 'teal' });
paint(mySellMarks, { name: 'SELL', style: 'labels_above', color: 'red' });

// ─── Signals for scanner/alerts/strategy ────────────────────────
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
register_signal(for_every(myBuySignal, mySellSignal, (_b, _s) => _b || _s), 'Buy Or Sell Signal');
describe_indicator('Strong Bar Highlighter');

// ═══════════════════════════════════════════════════════════════
// INPUTS
// ═══════════════════════════════════════════════════════════════

const myAtrTab = input.tab('ATR Filter');
const myAtrLen = myAtrTab.number('ATR Lookback (bars)', 20, { min: 1, max: 200 });
const myAtrMult = myAtrTab.number('Min Bar Size (x ATR)', 1.2, { min: 0.1, max: 5.0, step: 0.1 });

const myCloseTab = input.tab('Close Position Filter');
const myBullClosePct = myCloseTab.number('Bullish Close Threshold', 0.60, { min: 0.5, max: 1.0, step: 0.05 });
const myBearClosePct = myCloseTab.number('Bearish Close Threshold', 0.40, { min: 0.0, max: 0.5, step: 0.05 });

const myBodyTab = input.tab('Body Size Filter');
const myBodyPct = myBodyTab.number('Min Body Size', 0.50, { min: 0.0, max: 1.0, step: 0.05 });

// Colors (default values only; user can override via platform color pickers
// through paint()/color_candles, but we hardcode sensible defaults here)
const myBullColor = 'rgba(0, 0, 255, 0.4)';
const myBearColor = 'rgba(255, 0, 0, 0.4)';

// ═══════════════════════════════════════════════════════════════
// CALCULATIONS
// ═══════════════════════════════════════════════════════════════

const myAtrVal = atr(high, low, close, myAtrLen);
const myBarRange = sub(high, low);

// Avoid division by zero on doji bars
const myClosePos = for_every(close, low, myBarRange, (_c, _l, _r) => _r > 0 ? (_c - _l) / _r : 0.5);
const myBodySize = for_every(close, open, myBarRange, (_c, _o, _r) => _r > 0 ? Math.abs(_c - _o) / _r : 0.0);

// Core conditions
const myIsBig = for_every(myBarRange, myAtrVal, (_r, _a) => _r >= _a * myAtrMult);
const myIsBullBar = for_every(close, open, (_c, _o) => _c >= _o);
const myIsBearBar = for_every(close, open, (_c, _o) => _c < _o);
const myHasBody = for_every(myBodySize, _b => _b >= myBodyPct);

// Bullish strong bar
const myIsStrongBull = for_every(myIsBig, myIsBullBar, myHasBody, myClosePos, (_big, _bull, _body, _pos) =>
	_big && _bull && _body && _pos >= myBullClosePct
);

// Bearish strong bar
const myIsStrongBear = for_every(myIsBig, myIsBearBar, myHasBody, myClosePos, (_big, _bear, _body, _pos) =>
	_big && _bear && _body && _pos <= myBearClosePct
);

// ═══════════════════════════════════════════════════════════════
// VISUALS
// ═══════════════════════════════════════════════════════════════

const myCandleColors = for_every(myIsStrongBull, myIsStrongBear, (_bull, _bear) =>
	_bull ? myBullColor : (_bear ? myBearColor : null)
);
color_candles(myCandleColors);

// ═══════════════════════════════════════════════════════════════
// SIGNALS (for scanners, alerts, strategy tester)
// ═══════════════════════════════════════════════════════════════

register_signal(myIsStrongBull, 'Strong Bull Bar');
register_signal(myIsStrongBear, 'Strong Bear Bar');
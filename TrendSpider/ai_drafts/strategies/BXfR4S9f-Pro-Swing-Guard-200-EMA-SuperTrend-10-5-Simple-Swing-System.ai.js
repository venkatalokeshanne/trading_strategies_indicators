describe_indicator('Pro Swing Guard: 200 EMA and SuperTrend 10 5', 'price');

// --- Strategy Toggles ---
const myToggleTab = input.tab('Strategy Toggles');
const myEnableLong = myToggleTab.boolean('Enable Long Trades', true);
const myEnableShort = myToggleTab.boolean('Enable Short Trades', false);

// --- Parameters ---
// Renamed from "Inputs" because that tab name is reserved by the platform
const myParamsTab = input.tab('Parameters');
const mySTPeriod = myParamsTab.number('SuperTrend Period', 10, { min: 1, max: 100 });
const mySTFactor = myParamsTab.number('SuperTrend Multiplier', 5.0, { min: 0.1, max: 20, step: 0.1 });
const myEmaLen = myParamsTab.number('EMA Length', 200, { min: 1, max: 500 });
const myShowEma = myParamsTab.boolean('Show 200 EMA', true);

// --- Indicators ---
// supertrend() built-in returns the SuperTrend line itself; direction is derived
// by comparing close to the SuperTrend line, matching Pine's ta.supertrend() direction semantics:
// direction < 0 means uptrend (price above SuperTrend), direction > 0 means downtrend.
const mySuperTrendLine = supertrend(mySTPeriod, mySTFactor, false);
const myEma200 = ema(close, myEmaLen);

// direction: true (uptrend, like Pine's direction < 0) when close is above SuperTrend line
const myDirectionUp = for_every(close, mySuperTrendLine, (_c, _st) => _c > _st);

// --- Logic Conditions ---
const myAboveEma = for_every(close, myEma200, (_c, _e) => _c > _e);
const myBelowEma = for_every(close, myEma200, (_c, _e) => _c < _e);
const myEmaUp = for_every(myEma200, (_e, _p, _i) => _i > 0 ? _e > myEma200[_i - 1] : false);
const myEmaDown = for_every(myEma200, (_e, _p, _i) => _i > 0 ? _e < myEma200[_i - 1] : false);

// stBuy = direction < 0 (uptrend); stSell = direction > 0 (downtrend)
const myStBuy = myDirectionUp;
const myStSell = for_every(myDirectionUp, _u => !_u);

// --- Entry Logic ---
const myLongCondition = for_every(myStBuy, myAboveEma, myEmaUp, (_b, _a, _u) => myEnableLong && _b && _a && _u);
const myShortCondition = for_every(myStSell, myBelowEma, myEmaDown, (_s, _b, _d) => myEnableShort && _s && _b && _d);

// Exit logic signals: when in a long, exit on ST flip to sell; when in a short, exit on ST flip to buy.
// Note: actual position tracking (strategy.position_size) is not available in Custom JS indicators,
// so these exit signals represent "ST Sell occurred" / "ST Buy occurred" flip events for use in
// scanners/alerts/strategy tester logic that tracks position state externally.
const myLongExitSignal = myStSell;
const myShortExitSignal = myStBuy;

// --- Signals for scanning/strategy use ---
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit ST Flip');
register_signal(myShortExitSignal, 'Short Exit ST Flip');

// --- Visuals ---
const mySuperTrendColor = for_every(myDirectionUp, _u => _u ? '#26A69A' : '#EF5350');
paint(mySuperTrendLine, { name: 'SuperTrend', color: mySuperTrendColor, thickness: 2 });

const myEmaColor = for_every(myEmaUp, myEmaDown, (_u, _d) => _u ? '#26A69A' : (_d ? '#EF5350' : '#9E9E9E'));
paint(myShowEma ? myEma200 : series_of(null), { name: 'EMA200', color: myEmaColor, thickness: 3 });

// Background color cue via candle coloring (closest equivalent to bgcolor in Custom JS)
const myBackgroundColors = for_every(myLongCondition, myShortCondition, (_l, _s) => _l ? 'rgba(38,166,154,0.15)' : (_s ? 'rgba(239,83,80,0.15)' : null));
color_candles(myBackgroundColors);
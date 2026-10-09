describe_indicator('TU RSI Crossover Signals', 'price');

// --- Input Settings ---
const myRsiLength = input.number('RSI Length', 14, { min: 1 });
const myMaLength = input.number('RSI MA Length', 14, { min: 1 });
const mySourceName = input.select('Source', 'close', constants.price_source_options);
const mySource = market[mySourceName];

// --- RSI Filter Settings ---
const myBuyFilter = input.number('Max RSI for Buy', 45, { min: 0, max: 100 });
const mySellFilter = input.number('Min RSI for Sell', 65, { min: 0, max: 100 });

// --- Momentum Filter Settings ---
const myUseTrendFilter = input.boolean('Require Price > EMA (Avoid Falling Knives)', false);
const myEmaLength = input.number('Trend EMA Length', 9, { min: 1 });

// --- Calculations ---
const myRsiVal = rsi(mySource, myRsiLength);
const myRsiMa = sma(myRsiVal, myMaLength);
const myEmaVal = ema(mySource, myEmaLength);

// --- Crossover Conditions (replicating ta.crossover / ta.crossunder) ---
const myPrevRsiVal = shift(myRsiVal, 1);
const myPrevRsiMa = shift(myRsiMa, 1);

const myBuyCross = for_every(myRsiVal, myRsiMa, myPrevRsiVal, myPrevRsiMa,
	(_rsi, _ma, _prsi, _pma) => _rsi > _ma && _prsi <= _pma);

const mySellCross = for_every(myRsiVal, myRsiMa, myPrevRsiVal, myPrevRsiMa,
	(_rsi, _ma, _prsi, _pma) => _rsi < _ma && _prsi >= _pma);

// --- Momentum Logic ---
const myTrendIsUp = for_every(close, myEmaVal,
	(_close, _ema) => myUseTrendFilter ? (_close > _ema) : true);

const myBuySignal = for_every(myBuyCross, myRsiVal, myTrendIsUp,
	(_cross, _rsi, _trendUp) => _cross && (_rsi < myBuyFilter) && _trendUp);

const mySellSignal = for_every(mySellCross, myRsiVal,
	(_cross, _rsi) => _cross && (_rsi > mySellFilter));

// --- Plot Signals on Price Chart ---
const myBuyMarks = for_every(myBuySignal, _buy => _buy ? constants.icons.triangle_up : null);
const mySellMarks = for_every(mySellSignal, _sell => _sell ? constants.icons.triangle_down : null);

paint(myBuyMarks, { style: 'labels_below', color: 'green', name: 'Buy Signal' });
paint(mySellMarks, { style: 'labels_above', color: 'red', name: 'Sell Signal' });

// --- Plot the Trend EMA (only when the trend filter is enabled) ---
const myEmaToPlot = myUseTrendFilter ? myEmaVal : series_of(null);
paint(myEmaToPlot, { name: 'Trend EMA', color: 'rgba(0,0,255,0.4)', thickness: 2 });

// --- Signals for scanners/alerts/strategies ---
// Each signal is registered exactly once, with a unique name,
// outside of any conditional block, as required by the engine.
register_signal(myBuySignal, 'Buy Signal Register');
register_signal(mySellSignal, 'Sell Signal Register');
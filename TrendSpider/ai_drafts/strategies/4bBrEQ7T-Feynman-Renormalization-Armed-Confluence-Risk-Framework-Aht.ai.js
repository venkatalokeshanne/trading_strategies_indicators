describe_indicator('Feynman Renorm Armed Visuals', 'price');

// NOTE: This is a translation of a TradingView strategy script into an
// indicator. TrendSpider Custom JS indicators cannot place broker orders,
// draw box() objects, or draw labels only on the last bar the same way
// Pine does. We reproduce the scoring/armed logic exactly and expose it
// via register_signal() so it can be used in Scanners/Alerts/Strategy
// Tester, and we paint the key levels (EMA200, Buy Stop, Sell Stop) plus
// a filled "risk box" approximation between the two stop lines.

const minScore = input.number('Min Score to ARM Orders', 10, { min: 1, max: 16 });
const atrLen = input.number('ATR Length', 14, { min: 1, max: 200 });
const volMaLen = input.number('Volume Lookback', 20, { min: 1, max: 200 });

// Score components
const myAtr = atr(high, low, close, atrLen);
const myEma200 = ema(close, 200);
const myRsi = rsi(close, 14);
const myVolMa = sma(volume, volMaLen);

// Buy score: trend(3) + volume(3) + rsi space(2) + bullish bar(2)
const myBuyScore = for_every(close, myEma200, volume, myVolMa, myRsi, open,
	(_close, _ema200, _volume, _volMa, _rsi, _open) => {
		let myScore = 0;
		myScore += (_close > _ema200) ? 3 : 0;
		myScore += (_volume > _volMa) ? 3 : 0;
		myScore += (_rsi < 65) ? 2 : 0;
		myScore += (_close > _open) ? 2 : 0;
		return myScore;
	});

// Sell score: trend(3) + volume(3) + rsi space(2) + bearish bar(2)
const mySellScore = for_every(close, myEma200, volume, myVolMa, myRsi, open,
	(_close, _ema200, _volume, _volMa, _rsi, _open) => {
		let myScore = 0;
		myScore += (_close < _ema200) ? 3 : 0;
		myScore += (_volume > _volMa) ? 3 : 0;
		myScore += (_rsi > 35) ? 2 : 0;
		myScore += (_close < _open) ? 2 : 0;
		return myScore;
	});

// NOTE: for_every() requires every argument before the callback to be a
// time series. "minScore" is a plain number input, so it must be
// captured via closure instead of being passed in as a series argument.
const myIsBuyArmed = for_every(myBuyScore, _score => _score >= minScore);
const myIsSellArmed = for_every(mySellScore, _score => _score >= minScore);

// Renorm levels
const myBuyStopPrice = add(high, mult(myAtr, 1.5));
const mySellStopPrice = sub(low, mult(myAtr, 1.5));

// Dynamic colors for the stop lines: transitions to white when armed
const myTopColor = for_every(myIsBuyArmed, _armed => _armed ? 'white' : 'aqua');
const myBotColor = for_every(myIsSellArmed, _armed => _armed ? 'white' : 'orange');

// Paint EMA200 ("Macro Energy")
paint(myEma200, { name: 'Macro Energy', color: 'white', thickness: 2 });

// Paint Buy Stop and Sell Stop lines, with dynamic armed coloring
const myBuyStopPainted = paint(myBuyStopPrice, { name: 'Buy Stop', color: myTopColor, thickness: 2 });
const mySellStopPainted = paint(mySellStopPrice, { name: 'Sell Stop', color: myBotColor, thickness: 2 });

// Approximate the risk box by filling the area between the two stop lines.
// TrendSpider has no direct box() primitive, fill() between two painted
// lines is the closest equivalent.
fill(myBuyStopPainted, mySellStopPainted, 'gray', 0.12);

// Register signals for scanning/alerts/backtesting usage
register_signal(myIsBuyArmed, 'Buy Armed');
register_signal(myIsSellArmed, 'Sell Armed');
register_signal(for_every(myBuyScore, _s => _s >= minScore), 'Buy Score Reaches Threshold');
register_signal(for_every(mySellScore, _s => _s >= minScore), 'Sell Score Reaches Threshold');
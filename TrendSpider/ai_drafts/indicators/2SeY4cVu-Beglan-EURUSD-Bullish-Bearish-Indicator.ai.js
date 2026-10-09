describe_indicator('EURUSD Bullish Bearish Indicator', 'price');

const myEmaFastLength = input.number('EMA Fast', 50, { min: 1, max: 500 });
const myEmaSlowLength = input.number('EMA Slow', 200, { min: 1, max: 500 });
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });

const macdRow = input.row();
const myMacdFast = macdRow.number('MACD Fast', 12, { min: 1, max: 200 });
const myMacdSlow = macdRow.number('MACD Slow', 26, { min: 1, max: 200 });
const myMacdSignal = macdRow.number('MACD Signal', 9, { min: 1, max: 200 });

// Core indicators
const myEma50 = ema(close, myEmaFastLength);
const myEma200 = ema(close, myEmaSlowLength);
const myRsi = rsi(close, myRsiLength);

const myMacdLine = sub(ema(close, myMacdFast), ema(close, myMacdSlow));
const mySignalLine = ema(myMacdLine, myMacdSignal);
const myHist = sub(myMacdLine, mySignalLine);

// Scoring, mirroring the Pine logic exactly (1 point per condition, max 5 each side)
const myBullScore = for_every(myEma50, myEma200, close, myRsi, myMacdLine, mySignalLine, myHist,
	(_ema50, _ema200, _close, _rsiv, _macd, _signal, _hist) => {
		let myScore = 0;
		if (_ema50 > _ema200) myScore += 1;
		if (_close > _ema50) myScore += 1;
		if (_rsiv > 50) myScore += 1;
		if (_macd > _signal) myScore += 1;
		if (_hist > 0) myScore += 1;
		return myScore;
	}
);

const myBearScore = for_every(myBullScore, _bull => 5 - _bull);

const myBullish = for_every(myBullScore, _bull => _bull >= 4);
const myBearish = for_every(myBearScore, _bear => _bear >= 4);

// Background coloring approximation using candle colors (TrendSpider has no bgcolor equivalent for custom scripts)
const myCandleColors = for_every(myBullish, myBearish, (_bull, _bear) => {
	if (_bull) return 'rgba(0,200,0,0.12)';
	if (_bear) return 'rgba(200,0,0,0.12)';
	return 'rgba(128,128,128,0.08)';
});
color_candles(myCandleColors);

// EMA plots
paint(myEma50, { name: 'EMA50', color: 'orange', thickness: 2 });
paint(myEma200, { name: 'EMA200', color: 'blue', thickness: 2 });

// Dashboard overlay (replaces Pine's table)
const myLastIndex = close.length - 1;
const myDirectionText = myBullish[myLastIndex] ? 'BULLISH' : (myBearish[myLastIndex] ? 'BEARISH' : 'NEUTRAL');
const myDirectionColor = myBullish[myLastIndex] ? '#2ecc71' : (myBearish[myLastIndex] ? '#e74c3c' : '#95a5a6');
const myRsiColor = myRsi[myLastIndex] > 50 ? '#2ecc71' : '#e74c3c';

paint_overlay('EURUSDDashboard', { position: 'top_right' }, {
	rows: [{
		cells: [
			{ text: 'EURUSD', background_color: '#000000', color: '#ffffff' },
			{ text: 'MARKET BIAS', background_color: '#000000', color: '#ffffff' }
		]
	}, {
		cells: [
			{ text: 'Direction', background_color: '#282828', color: '#ffffff' },
			{ text: myDirectionText, background_color: myDirectionColor, color: '#ffffff' }
		]
	}, {
		cells: [
			{ text: 'Bull Score', background_color: '#282828', color: '#ffffff' },
			{ text: `${myBullScore[myLastIndex]} slash 5`, color: '#2ecc71' }
		]
	}, {
		cells: [
			{ text: 'Bear Score', background_color: '#282828', color: '#ffffff' },
			{ text: `${myBearScore[myLastIndex]} slash 5`, color: '#e74c3c' }
		]
	}, {
		cells: [
			{ text: 'RSI', background_color: '#282828', color: '#ffffff' },
			{ text: myRsi[myLastIndex].toFixed(1), color: myRsiColor }
		]
	}]
});

// Signals for scanners, alerts, strategy tester (replace alertcondition())
const myBullishChangeSignal = for_every(myBullish, (_bull, _prev, _index) => _index > 0 && _bull && !myBullish[_index - 1]);
const myBearishChangeSignal = for_every(myBearish, (_bear, _prev, _index) => _index > 0 && _bear && !myBearish[_index - 1]);

register_signal(myBullish, 'Market Bullish');
register_signal(myBearish, 'Market Bearish');
register_signal(myBullishChangeSignal, 'Turned Bullish');
register_signal(myBearishChangeSignal, 'Turned Bearish');
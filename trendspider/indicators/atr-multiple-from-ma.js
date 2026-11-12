<code x-ref="code" class="hljs" data-clipboard-text>
describe_indicator('ATR multiple from MA', 'price', { warmup: 300 });

const atrLength = input.number('ATR Length', 15, { min: 0, max: 150 });
const maLength = input.number('MA Length', 50, { min: 0, max: 150 });
const maType = input('MA Type', 'sma', ['sma', 'ema', 'wildma', 'vwma', 'wma', 'hullma']);
const threshold = input('Threshold', 7, { min: 0, max: 100});
const showMA = input.boolean('Paint MA', true);
const maValues = indicators[maType](close, maLength);

const atrPercentage = mult(div(atr(atrLength), close), 100);
const gainFromMa = mult(div(sub(close, maValues), maValues), 100);
const atrMultiple = div(gainFromMa, atrPercentage);

const dotsDistance = mult(atr(15), 1);
const sellSignals = add(atrMultiple.map((value, index) => value >= threshold ? high[index] : null), dotsDistance);
const buySignals = sub(atrMultiple.map((value, index) => value <= -threshold ? low[index] : null), dotsDistance);

register_signal(sellSignals, 'Sell');
register_signal(buySignals, 'Buy');

const VALUE_COLUMN_STYLE = { fontWeight: 'bold', paddingLeft: 10 };
const currentGain = gainFromMa[gainFromMa.length - 1].toFixed(2);

paint_overlay('Table', { position: 'bottom_left', order: 'above_all' }, {
	paddingBottom: 15,
    background: 'var(--background-color)',
	rows: [{
		cells: [
			{ colspan: 2, text: `xATR(${atrLength}) from ${maType}(${maLength})`, padding: 2, background: 'orange', color: 'black' },
			{ }
		]
	}, {
		cells: [
			{ text: 'ATR% Multiple distance', padding: 2 },
			{ text: atrMultiple[atrMultiple.length - 1].toFixed(2), ...VALUE_COLUMN_STYLE, color: currentGain > 0 ? 'green' : 'red'}
		]
	}, {
		cells: [
			{ text: `% Gain from ${maType}`, padding: 2 },
			{ text: `${currentGain}%`, ...VALUE_COLUMN_STYLE, color: currentGain > 0 ? 'green' : 'red' }
		]
	}, {
		cells: [
			{ text: 'ATR%', padding: 2 },
			{ text: `${atrPercentage[atrPercentage.length - 1].toFixed(2)}%`, ...VALUE_COLUMN_STYLE }
		]
	}]
});

paint(sellSignals, { name: 'Sell Signals', color: 'red', style: 'dotted', thickness: 3, hideInScriptEditor: true, hideInLegend: true });
paint(buySignals, { name: 'Buy Signals', color: 'green', style: 'dotted', thickness: 3, hideInScriptEditor: true, hideInLegend: true });

paint(showMA ? maValues : series_of(null), { name: "MA", color: 'orange' });</code>
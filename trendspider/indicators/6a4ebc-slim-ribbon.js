<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Slim Ribbon', 'price');

// ================= Inputs =================
const priceSource  = input('Price source', 'close', constants.price_source_options);
const superfastLen = input.number('Superfast EMA length', 8,  { min: 1, max: 200 });
const fastLen      = input.number('Fast EMA length',      13, { min: 1, max: 200 });
const slowLen      = input.number('Slow EMA length',      21, { min: 1, max: 200 });

const paintCandles = input.boolean('Color candles', true);
const showArrows   = input.boolean('Show signal arrows', true);

const buyColor     = input.color('Buy color', '#1B5E20');      // dark green
const sellColor    = input.color('Sell color', '#EF5350');     // red
const neutralColor = input.color('Neutral color', '#FFD54F');  // yellow

const price = market[priceSource];

// ================= EMAs =================
const emaSuperfast = ema(price, superfastLen);
const emaFast      = ema(price, fastLen);
const emaSlow      = ema(price, slowLen);

// ================= Signal state machine =================
const buyState  = series_of(0);
const sellState = series_of(0);

const buyStartMarks  = series_of(null);
const buyStopMarks   = series_of(null);
const sellStartMarks = series_of(null);
const sellStopMarks  = series_of(null);
const candleColors   = series_of(null);

for (let i = 0; i < close.length; i += 1) {
	const prevBuy  = i > 0 ? buyState[i - 1]  : 0;
	const prevSell = i > 0 ? sellState[i - 1] : 0;

	// Buy: ribbon stacked bullish AND low riding above the superfast EMA
	const buy     = emaSuperfast[i] > emaFast[i] && emaFast[i] > emaSlow[i] && low[i] > emaSuperfast[i];
	const stopBuy = emaSuperfast[i] <= emaFast[i];

	// Sell: ribbon stacked bearish AND high pinned below the superfast EMA
	const sell     = emaSuperfast[i] < emaFast[i] && emaFast[i] < emaSlow[i] && high[i] < emaSuperfast[i];
	const stopSell = emaSuperfast[i] >= emaFast[i];

	// buy implies !stopBuy (and vice versa), so this collapses cleanly:
	buyState[i]  = buy  ? 1 : (stopBuy  ? 0 : prevBuy);
	sellState[i] = sell ? 1 : (stopSell ? 0 : prevSell);

	if (showArrows) {
		if (prevBuy === 0 && buyState[i] === 1)   buyStartMarks[i]  = constants.icons.arrow_up;
		if (prevBuy === 1 && buyState[i] === 0)   buyStopMarks[i]   = constants.icons.arrow_down;
		if (prevSell === 0 && sellState[i] === 1) sellStartMarks[i] = constants.icons.arrow_down;
		if (prevSell === 1 && sellState[i] === 0) sellStopMarks[i]  = constants.icons.arrow_up;
	}

	if (paintCandles) {
		candleColors[i] = buyState[i] === 1 ? buyColor
			: sellState[i] === 1 ? sellColor
			: neutralColor;
	}
}

// ================= Painting =================
paint(emaSuperfast, { name: 'Superfast EMA', color: '#2196F3', thickness: 2 });
paint(emaFast,      { name: 'Fast EMA',      color: '#FF9800', thickness: 2 });
paint(emaSlow,      { name: 'Slow EMA',      color: '#E91E63', thickness: 2 });

paint(buyStartMarks,  { style: 'labels_below', color: buyColor,     name: 'Buy Signal' });
paint(buyStopMarks,   { style: 'labels_above', color: neutralColor, name: 'Momentum Down' });
paint(sellStartMarks, { style: 'labels_above', color: sellColor,    name: 'Sell Signal' });
paint(sellStopMarks,  { style: 'labels_below', color: neutralColor, name: 'Momentum Up' });

color_candles(candleColors);

// ================= Scannable / alertable signals =================
// These replace the four ToS Alert() calls — and unlock scanner,
// multi-factor alerts, and strategy tester usage.
register_signal(buyState,  'Buy Momentum');
register_signal(sellState, 'Sell Momentum');</code>
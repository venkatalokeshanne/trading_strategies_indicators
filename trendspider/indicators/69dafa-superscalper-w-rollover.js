<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('SuperScalper w/ Rollover');

// ─────────────────────────────────────────────────────────────────────────────
// SuperScalper Inputs
// ─────────────────────────────────────────────────────────────────────────────
const periods        = input.number('ATR Period', 10, { min: 1, max: 100 });
const sourceType     = input.select('Source', 'hl2', constants.price_source_options);
const source         = market[sourceType];
const multiplier     = input.number('ATR Multi (1.75=Scalp)', 1.75, { min: 0.1, max: 10 });
const showSignals    = input.boolean('Show Buy/Sell Signals ?', true);
const highlighting   = input.boolean('Highlighter On/Off ?', false);
const showPrice      = input.boolean('Show Price in Labels ?', false);

// ─────────────────────────────────────────────────────────────────────────────
// Rollover Inputs
// ─────────────────────────────────────────────────────────────────────────────
const enableRollover = input.boolean('Enable Rollover Signal ?', true);
const smaFastLength  = input.number('RO Fast Close SMA Len', 5,  { min:1, step:1 });
const stochLen       = input.number('RO Stochastic Length',        14, { min:1, step:1 });
const stochKSmooth   = input.number('RO %K Smoothing',             3,  { min:1, step:1 });
const stochDSmooth   = input.number('RO %D Smoothing',             3,  { min:1, step:1 });
const obThreshold    = input.number('RO Overbought Threshold',     80, { min:0, step:1 });
const roColor        = input.color('RO Label Color',       'white');
const roBgColor      = input.color('RO Background Color',  '#fff9c4');
const roOffset       = input.number('RO Label Offset',      50, { min:0, step:1 });

// ─────────────────────────────────────────────────────────────────────────────
// SuperScalper Core Logic
// ─────────────────────────────────────────────────────────────────────────────

// Calculate ATR (True Range, always)
const myAtr = atr(high, low, close, periods);

// Calculate up and down bands
const myUp = for_every(source, myAtr, close, (_source, _atr, _close, _prevUp, _index) => {
	const rawUp = _source - (multiplier * _atr);
	if (_index === 0) return rawUp;
	const up1 = _prevUp !== null ? _prevUp : rawUp;
	return close[_index - 1] > up1 ? Math.max(rawUp, up1) : rawUp;
});

const myDn = for_every(source, myAtr, close, (_source, _atr, _close, _prevDn, _index) => {
	const rawDn = _source + (multiplier * _atr);
	if (_index === 0) return rawDn;
	const dn1 = _prevDn !== null ? _prevDn : rawDn;
	return close[_index - 1] < dn1 ? Math.min(rawDn, dn1) : rawDn;
});

// Calculate trend
const myTrend = for_every(close, myUp, myDn, (_close, _up, _dn, _prevTrend, _index) => {
	if (_index === 0) return 1;
	const prevTrend = _prevTrend !== null ? _prevTrend : 1;
	const prevUp = myUp[_index - 1];
	const prevDn = myDn[_index - 1];
	
	if (prevTrend === -1 && _close > prevDn) return 1;
	if (prevTrend === 1 && _close < prevUp) return -1;
	return prevTrend;
});

// Create series for plotting
const myUpTrendLine = for_every(myTrend, myUp, (_trend, _up) => _trend === 1 ? _up : null);
const myDnTrendLine = for_every(myTrend, myDn, (_trend, _dn) => _trend === -1 ? _dn : null);

// Buy / Sell signals
const myBuySignal = for_every(myTrend, (_trend, _prev, _index) => {
	if (_index === 0) return false;
	return _trend === 1 && myTrend[_index - 1] === -1;
});

const mySellSignal = for_every(myTrend, (_trend, _prev, _index) => {
	if (_index === 0) return false;
	return _trend === -1 && myTrend[_index - 1] === 1;
});

// Plot lines
const upTrendId = paint(myUpTrendLine, { name: 'Up Trend', style: 'line', color: 'green' });
const dnTrendId = paint(myDnTrendLine, { name: 'Down Trend', style: 'line', color: 'red' });

// Clouds
const cloudTopBuy = for_every(myTrend, close, myUp, (_trend, _close, _up) =>
	_trend === 1 ? Math.max(_close, _up) : null);

const cloudBottomBuy = for_every(myTrend, close, myUp, (_trend, _close, _up) =>
	_trend === 1 ? Math.min(_close, _up) : null);

const cloudTopSell = for_every(myTrend, close, myDn, (_trend, _close, _dn) =>
	_trend === -1 ? Math.max(_close, _dn) : null);

const cloudBottomSell = for_every(myTrend, close, myDn, (_trend, _close, _dn) =>
	_trend === -1 ? Math.min(_close, _dn) : null);

const cloudTopBuyId = paint(cloudTopBuy, { name: 'CloudTopBuy', style: 'line', hidden: true });
const cloudBottomBuyId = paint(cloudBottomBuy, { name: 'CloudBottomBuy', style: 'line', hidden: true });
fill(cloudTopBuyId, cloudBottomBuyId, 'green', 0.2);

const cloudTopSellId = paint(cloudTopSell, { name: 'CloudTopSell', style: 'line', hidden: true });
const cloudBottomSellId = paint(cloudBottomSell, { name: 'CloudBottomSell', style: 'line', hidden: true });
fill(cloudTopSellId, cloudBottomSellId, 'red', 0.2);

// Place labels
for (let i = 0; i < close.length; i++) {
	if (myBuySignal[i] && showSignals) {
		const labelText = showPrice ? `BULLn$${close[i].toFixed(2)}` : 'BULL';
		paint_label_at_line(upTrendId, i, labelText, {
			color: 'white',
			background_color: 'green',
			vertical_align: 'bottom'
		});
	}
	if (mySellSignal[i] && showSignals) {
		const labelText = showPrice ? `BEARn$${close[i].toFixed(2)}` : 'BEAR';
		paint_label_at_line(dnTrendId, i, labelText, {
			color: 'white',
			background_color: 'red',
			vertical_align: 'top'
		});
	}
}

// Highlighting
const myCandleColors = for_every(myTrend, (_trend) => {
	if (!highlighting) return null;
	return _trend === 1 ? 'green' : 'red';
});
color_candles(myCandleColors);

// Direction Change
const myChangeCond = for_every(myTrend, (_trend, _prev, _index) => {
	if (_index === 0) return false;
	return _trend !== myTrend[_index - 1];
});

// ────────────────────────────────────────────────
// Rollover Logic
// ────────────────────────────────────────────────

// Fast SMA
const smaCloseFast = sma(close, smaFastLength);

// Stochastic calculation (%K and %D)
const lowArr   = lowest(low,  stochLen);
const highArr  = highest(high, stochLen);

const stochK   = close.map((c,i) => (highArr[i] - lowArr[i]) !== 0
	? 100 * (c - lowArr[i]) / (highArr[i] - lowArr[i])
	: 0);

const stochBck = sma(stochK,   stochKSmooth);
const stochBcd = sma(stochBck, stochDSmooth);

// Rollover condition series
const isROArr = close.map((c,i) =>
	i > 0 &&
	c < smaCloseFast[i] &&
	c < open[i] &&
	low[i] < low[i-1] &&
	stochBcd[i-1] > obThreshold &&
	stochBcd[i]   <= obThreshold
);

// Paint Rollover labels only if enabled
paint(isROArr.map(v => v && enableRollover ? '⚠️' : null), {
	name:            'Rollover',
	style:           'labels_above',
	verticalOffset:  roOffset,
	color:           roColor,
	background_color: roBgColor
});

// ────────────────────────────────────────────────
// Signals (for Visual Scripts / Scans)
// ────────────────────────────────────────────────
register_signal(myBuySignal,  'SuperScalper Buy');
register_signal(mySellSignal, 'SuperScalper Sell');
register_signal(myChangeCond, 'SuperScalper Trend Flip');
register_signal(isROArr,      'SuperScalper Rollover');</code>
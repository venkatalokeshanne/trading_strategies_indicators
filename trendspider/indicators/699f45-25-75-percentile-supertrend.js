<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('25-75 Percentile SuperTrend');

// Inputs
const subject = input.number('Supertrend length', 14, { min: 2 });
const myMult = input.number('Multiplier', 1, { min: 0, max: 10 });
const slen = input.number('Percentile length', 27, { min: 1, max: 300 });

const priceSourceOptions = ['high', 'low', 'close', 'open', 'hl2', 'hlc3', 'ohlc4'];
const src_2575_input = input.select('Median smoothing source', 'high', priceSourceOptions);
const src_2575 = market[src_2575_input];

// Helper function to compute percentile
const percentile_nearest_rank = (series, length, percentile) => {
	return sliding_window_function(series, length, window => {
		const sorted = [...window].sort((a, b) => a - b);
		const index = Math.ceil((percentile / 100) * sorted.length) - 1;
		return sorted[Math.max(0, index)];
	});
};

// Calculate percentiles
const smooth_lower = percentile_nearest_rank(src_2575, slen, 25);
const smooth_upper = percentile_nearest_rank(src_2575, slen, 75);

// ATR calculation
const myAtr = atr(high, low, close, subject);

// Calculate upper and lower bands
const src_long = smooth_upper;
const src_short = smooth_lower;
const upper_initial = add(src_long, mult(myAtr, myMult));
const lower_initial = sub(src_short, mult(myAtr, myMult));

// SuperTrend logic using for_every
// The issue was accessing prev.lower when prev could be null on the first candle
// We need to check if prev exists before accessing its properties
const supertrend_result = for_every(upper_initial, lower_initial, close, (u, l, c, prev, idx) => {
	if (idx === 0 || !prev) {
		return { upper: u, lower: l, dist: 1, st: u };
	}
	
	const pl = prev.lower;
	const pu = prev.upper;
	
	const new_lower = (l > pl || close[idx - 1] < pl) ? l : pl;
	const new_upper = (u < pu || close[idx - 1] > pu) ? u : pu;
	
	let dist;
	if (prev.st === pu) {
		dist = c > new_upper ? -1 : 1;
	} else {
		dist = c < new_lower ? 1 : -1;
	}
	
	const st = dist === -1 ? new_lower : new_upper;
	
	return { upper: new_upper, lower: new_lower, dist: dist, st: st };
});

// Extract series from result
const x = supertrend_result.map(r => r ? r.st : null);
const dist = supertrend_result.map(r => r ? r.dist : null);

// Detect crossovers
const ST_L = for_every(dist, (d, prev_d) => prev_d >= 0 && d < 0 ? true : false);
const ST_S = for_every(dist, (d, prev_d) => prev_d <= 0 && d > 0 ? true : false);

// State tracking
const Mattes = for_every(ST_L, ST_S, (long, short, prev_state) => {
	if (long && !short) return 1;
	if (short) return -1;
	return prev_state || 0;
});

// Colors
const syscol = Mattes.map(m => m === 1 ? '#2da2fc' : m === -1 ? '#713bf9' : 'gray');
const BlueTransparent = 'rgba(45, 162, 252, 0.5)';
const PurpleTransparent = 'rgba(113, 59, 249, 0.5)';

// Color candles
color_candles(syscol);

// Plot trends
const upTrendSeries = dist.map((d, i) => d < 0 ? x[i] : null);
const downTrendSeries = dist.map((d, i) => d >= 0 ? x[i] : null);

const upTrendLine = paint(upTrendSeries, { name: 'Up Trend', color: '#2da2fc', style: 'line' });
const downTrendLine = paint(downTrendSeries, { name: 'Down Trend', color: '#713bf9', style: 'line' });

// Middle line
const middleLine = div(add(smooth_lower, smooth_upper), 2);
const middleLinePainted = paint(middleLine, { color: syscol, name: 'Middle', hidden: true });

// Fill areas
fill(middleLinePainted, upTrendLine, BlueTransparent);
fill(middleLinePainted, downTrendLine, PurpleTransparent);
</code>
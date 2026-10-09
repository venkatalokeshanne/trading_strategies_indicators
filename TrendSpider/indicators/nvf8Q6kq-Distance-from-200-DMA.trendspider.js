/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Distance from 200 DMA
 * Author       : tyjkot
 * Source URL   : https://www.tradingview.com/script/nvf8Q6kq-Distance-from-200-DMA
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Distance from 200 DMA_TV
 *
 * The Pine original, in words: % distance of the price from the daily SMA 200, as a histogram, with an SMA(15) of
 *   it coloured by slope.
 *
 * Deviations from the original: fixed from the AI draft, which landed each daily SMA at the daily bar's OPEN
 *   (intraday bars saw that day's not-yet-known close): intraday bars now use the
 *   previous completed day; the Pine shows the new value one bar earlier, on the day's
 *   last bar.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Distance from 200 DMA_TV', 'lower');

// Price source selection, mirroring Pine's srcOption
const mySrcOption = input.select('Price Source', 'Close', ['Close', 'Open', 'High', 'Low', 'HL2', 'HLC3', 'OHLC4']);
const myLenMA = input.number('MA Length of Distance', 15, { min: 1, max: 500 });

const mySrcMap = {
	Close: close,
	Open: open,
	High: high,
	Low: low,
	HL2: hl2,
	HLC3: hlc3,
	OHLC4: ohlc4
};

const mySrc = mySrcMap[mySrcOption];

// Always fetch Daily data, regardless of chart timeframe, to compute
// the 200-period Daily SMA on the selected price source.
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, `Error fetching daily data: "${myDailyData.error}"`);

const myDailySrcMap = {
	Close: myDailyData.close,
	Open: myDailyData.open,
	High: myDailyData.high,
	Low: myDailyData.low,
	HL2: div(add(myDailyData.high, myDailyData.low), 2),
	HLC3: div(add(add(myDailyData.high, myDailyData.low), myDailyData.close), 3),
	OHLC4: div(add(add(add(myDailyData.open, myDailyData.high), myDailyData.low), myDailyData.close), 4)
};

const myDailySrc = myDailySrcMap[mySrcOption];
const myDailySMA200 = sma(myDailySrc, 200);

// Land the Daily SMA(200) onto the current chart's time series, using
// "lookahead off" semantics (only use the last Daily bar that has
// already closed relative to the current candle), then hold it
// constant until the next landed point (no interpolation/forward look).
// No look-ahead: a daily bar's SMA is only known at its close, so intraday bars use the previous
// completed day's value (Pine lookahead_off). On a daily or higher chart the chart's own SMA is used.
const myIntraday = /^\d+$/.test(String(current.resolution));
const myDailyPrev = myDailySMA200.map((_v, _k) => (_k === 0 ? null : myDailySMA200[_k - 1]));
const myDailySMALanded = land_points_onto_series(myDailyData.time, myIntraday ? myDailyPrev : myDailySMA200, time, 'le');
const myDailySMAOnChart = interpolate_sparse_series(myDailySMALanded, 'constant');

// Distance from the selected price source to the Daily SMA(200), in %
const myDistance = for_every(mySrc, myDailySMAOnChart, (_s, _m) => _m ? (_s - _m) / _m * 100 : null);

// Moving average of the distance (signal line)
const myDistMA = sma(myDistance, myLenMA);

// Dynamic color: lime when the MA is rising, purple when falling
const myMAColor = for_every(myDistMA, shift(myDistMA, 1), (_cur, _prev) => _prev !== null && _cur > _prev ? 'lime' : 'purple');

paint(myDistance, { name: 'Distance to 200 DMA', style: 'column', color: '#00bcd4' });
paint(myDistMA, { name: 'MA of Distance', style: 'line', color: myMAColor, thickness: 2 });
paint(horizontal_line(0), { name: 'Zero', style: 'dotted', color: 'gray' });

// Scanning / strategy signals
register_signal(for_every(myDistance, _d => _d !== null && _d > 0), 'Distance Above Zero');
register_signal(for_every(myDistance, _d => _d !== null && _d < 0), 'Distance Below Zero');
register_signal(for_every(myDistMA, shift(myDistMA, 1), (_cur, _prev) => _prev !== null && _cur > _prev), 'Distance MA Rising');
register_signal(for_every(myDistMA, shift(myDistMA, 1), (_cur, _prev) => _prev !== null && _cur < _prev), 'Distance MA Falling');
register_signal(for_every(myDistance, shift(myDistance, 1), (_cur, _prev) => _prev !== null && _cur !== null && _cur > 0 && _prev <= 0), 'Distance Crosses Above Zero');
register_signal(for_every(myDistance, shift(myDistance, 1), (_cur, _prev) => _prev !== null && _cur !== null && _cur < 0 && _prev >= 0), 'Distance Crosses Below Zero');

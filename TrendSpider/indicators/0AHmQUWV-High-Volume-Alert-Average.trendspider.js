/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : High Volume Alert (Above Average)
 * Author       : zahidedge14
 * Source URL   : https://www.tradingview.com/script/0AHmQUWV-High-Volume-Alert-Average
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : High Volume Alert (Above Average)_TV
 *
 * The Pine original, in words: volume columns, red when volume exceeds the SMA of the
 * PREVIOUS `lookback` volumes (volume[1]), plus that average and a marker on spikes.
 *
 * Deviations from the original: none in the values.
 * Not carried over: alert()/alertcondition() — use the 'Volume Above Average' signal in
 * TrendSpider alerts instead.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('High Volume Alert (Above Average)_TV', 'lower');

const myLookback = input.number('Lookback Period (candles)', 20, { min: 1, max: 500 });

// ta.sma(volume[1], lookback): average of the previous `lookback` candles
const myAvgVol = sma(shift(volume, 1), myLookback);

const myVolumeSpike = for_every(volume, myAvgVol, (_v, _a) => _a !== null && _v > _a);
const myVolColor = for_every(myVolumeSpike, _s => _s ? 'red' : 'gray');

paint(volume, { name: 'Volume', style: 'column', color: myVolColor });
paint(myAvgVol, { name: 'Average Volume (Last 20)', color: 'orange', thickness: 1 });

const myMarker = for_every(myVolumeSpike, _s => _s ? constants.icons.triangle_up : null);
paint(myMarker, { name: 'Volume Spike', style: 'labels_above', color: 'red' });

register_signal(myVolumeSpike, 'Volume Above Average');

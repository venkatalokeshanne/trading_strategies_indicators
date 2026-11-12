/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Velas H6 / H8 / H12 Real em Tempo Real - Aderaldo
 * Author       : aderaldonunesjuniortst
 * Source URL   : https://www.tradingview.com/script/S2uqHedC
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Velas H6 H8 H12 Real Time_TV
 *
 * Deviations from the original: Rebuilt: candle boxes not possible; forming 6h/8h/12h candle tracked from chart bars
 *   in UTC-aligned buckets, shown as candle colouring plus open/high/low lines.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Velas H6 H8 H12 Real Time_TV', 'price');
const myTimeframeChoice = input.select('Timeframe', '12h', ['6h', '8h', '12h']);
const myShowIndicator = input.boolean('Exibir Indicador', true);
// Pine groups chart bars with timeframe.change(); here chart bars are grouped into UTC-aligned
// buckets of 6h/8h/12h and the forming candle is tracked bar by bar (no look-ahead).
const myBucketSeconds = { '6h': 21600, '8h': 28800, '12h': 43200 }[myTimeframeChoice];
const myKey = time.map(_t => Math.floor(_t / myBucketSeconds));
const myOpen = [];
const myHigh = [];
const myLow = [];
for (let myI = 0; myI < close.length; myI += 1) {
	const myNew = myI === 0 || myKey[myI] !== myKey[myI - 1];
	myOpen.push(myNew ? open[myI] : myOpen[myI - 1]);
	myHigh.push(myNew ? high[myI] : Math.max(myHigh[myI - 1], high[myI]));
	myLow.push(myNew ? low[myI] : Math.min(myLow[myI - 1], low[myI]));
}
const myBull = close.map((_c, _i) => _c >= myOpen[_i]);
const myColors = myBull.map(_b => myShowIndicator ? (_b ? '#3CB371' : '#FF6347') : null);
color_candles(myColors);
const myGate = (_s) => _s.map(_v => myShowIndicator ? _v : null);
paint(myGate(myOpen), { name: 'HTF Open', color: '#999999', thickness: 1 });
paint(myGate(myHigh), { name: 'HTF High', color: myColors, thickness: 1 });
paint(myGate(myLow), { name: 'HTF Low', color: myColors, thickness: 1 });
register_signal(myBull, 'HTF Candle Bullish');
register_signal(myBull.map(_b => !_b), 'HTF Candle Bearish');

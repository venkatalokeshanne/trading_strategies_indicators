/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Bollinger Bands  (TEMPLATE EXAMPLE — replace every field)
 * Author       : TradingView (built-in)
 * Source URL   : https://www.tradingview.com/support/solutions/43000501840/
 * Pine version : v5
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-08 by Claude (pine-to-trendspider skill)
 * TrendSpider name : Bollinger Bands_TV
 * Live tested  : <YYYY-MM-DD> on <TICKER> <res> — saved in TrendSpider: yes | no (why)
 *
 * Deviations from the original:
 *   - none. ta.stdev defaults to biased (population); TrendSpider's stdev() is
 *     population too, so the bands match.
 *
 * Not carried over:
 *   - plot `offset` is reproduced with the reserved `offset` input rather than
 *     Pine's per-plot offset argument.
 * ───────────────────────────────────────────────────────────────────────
 *
 * Layout every conversion follows:
 *   header → describe_indicator → inputs → helpers → computation → paints → signals
 * All paint / fill / register_signal calls are top-level, unconditional, literal names.
 */

describe_indicator('Bollinger Bands_TV', 'overlay', { shortName: 'BB' });

// ── Inputs ── short titles (< ~20 chars), Pine's exact defaults ───────────
const length = input.number('Length', 20, { min: 1 });
const stdMult = input.number('StdDev', 2.0, { min: 0.001, max: 50 });   // not `mult`: reserved built-in

// ── Helpers (copied from templates/helpers.js — only what this script uses) ──
const isNa = v => v === null || v === undefined || Number.isNaN(v);

// ── Computation ───────────────────────────────────────────────────────────
// Pine: basis = ta.sma(src, length); dev = mult * ta.stdev(src, length)
const src = close;                       // Pine `input(close, "Source")` — see note below
const basis = sma(src, length);
const sd = stdev(src, length);           // not `dev`/`stdev` as a name: avoid built-ins
const upper = basis.map((b, i) => (isNa(b) || isNa(sd[i]) ? null : b + stdMult * sd[i]));
const lower = basis.map((b, i) => (isNa(b) || isNa(sd[i]) ? null : b - stdMult * sd[i]));

// ── Paints ── unconditional, fixed literal names ─────────────────────────
const basisLine = paint(basis, { name: 'Basis', color: '#FF6D00', thickness: 1 });
const upperLine = paint(upper, { name: 'Upper', color: '#2962FF', thickness: 1 });
const lowerLine = paint(lower, { name: 'Lower', color: '#2962FF', thickness: 1 });
fill(upperLine, lowerLine, '#2196F3', 0.05, 'Background');   // Pine transp 95 → opacity 0.05

/*
 * Note on the Source input. Pine's `input(close, "Source")` lets the user pick a price
 * source. The TrendSpider equivalent is
 *     const srcName = input.select('Source', 'close', constants.price_source_options);
 *     const src = market[srcName];
 * [VERIFY] the option values before using it; this template keeps `close` fixed so it
 * runs as-is.
 */

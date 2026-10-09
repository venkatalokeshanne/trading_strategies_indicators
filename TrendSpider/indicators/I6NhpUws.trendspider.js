/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Volume with Alert
 * Author       : BullBearSR
 * Source URL   : https://www.tradingview.com/script/I6NhpUws
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Volume with Alert_TV
 *
 * The Pine original, in words: volume columns (teal up bar, red down bar, yellow when volume >= threshold), a
 *   volume SMA and a dashed threshold line.
 *
 * Deviations from the original: input titles shortened (TrendSpider rejects long titles): 'Alert volume >=', 'Volume
 *   MA length'.
 * Not carried over: alertcondition — use the 'Volume exceeds threshold' signal for alerts.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Volume with Alert_TV', 'lower');

const myThreshold = input.number('Alert volume >=', 1000, { min: 0 });
const myMaLength = input.number('Volume MA length', 20, { min: 1 });

const myMaVol = sma(volume, myMaLength);
const myTriggered = for_every(volume, _v => _v >= myThreshold);
const myColor = for_every(close, open, myTriggered, (_c, _o, _t) => _t ? '#FFEB3B' : (_c >= _o ? '#009688' : '#F44336'));

paint(volume, { name: 'Volume', style: 'column', color: myColor });
paint(myMaVol, { name: 'Volume Moving Average', color: '#2962FF', thickness: 1 });
paint(horizontal_line(myThreshold), { name: 'Threshold Line', color: '#FF9800', style: 'dotted' });
register_signal(myTriggered, 'Volume exceeds threshold');

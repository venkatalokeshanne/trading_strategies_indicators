/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : TRIX Strong Hand - Didi
 * Author       : Agulhada
 * Source URL   : https://www.tradingview.com/script/Gg9z9tjF-TRIX-Strong-Hand-Didi
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : TRIX Strong Hand - Didi_TV
 *
 * The Pine original, in words: TRIX = 10000 x change of the triple EMA(9) of log(close), with an SMA (or EMA) of 4
 *   and a cross marker; filled between them.
 *
 * Deviations from the original: colour inputs not exposed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('TRIX Strong Hand - Didi_TV', 'lower');

const myTrixLen = input.number('TRIX Length', 9, { min: 1 });
const myMaLen = input.number('Moving Average', 4, { min: 1 });
const myUseEma = input.boolean('Use Ema', false);
const myUseFill = input.boolean('Fill', true);

// TRIX = 10000 * change(triple EMA of log(close))
const myLogClose = close.map(_c => Math.log(_c));
const myTripleEma = ema(ema(ema(myLogClose, myTrixLen), myTrixLen), myTrixLen);
const myTrix = mult(sub(myTripleEma, shift(myTripleEma, 1)), 10000);
const myEmaOfTrix = ema(myTrix, myMaLen);
const mySmaOfTrix = sma(myTrix, myMaLen);
const myMa = myUseEma ? myEmaOfTrix : mySmaOfTrix;

// Zero reference line
paint(horizontal_line(0), { name: 'Zero Line', color: '#000000', style: 'line' });

// Main lines
const myTrixPainted = paint(myTrix, { name: 'TRIX', color: '#5b9bf5', thickness: 2 });
const myMaPainted = paint(myMa, { name: 'MA Trix', color: '#ffee58', thickness: 2 });

// Cross detection: true when Trix and MA cross in either direction
const myCrossSignal = for_every(myMa, myTrix, (_ma, _trix, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevMa = myMa[_i - 1];
	const myPrevTrix = myTrix[_i - 1];
	if (myPrevMa === null || myPrevTrix === null || _ma === null || _trix === null) return false;
	const myWasAboveOrEqual = myPrevMa >= myPrevTrix;
	const myIsAboveOrEqual = _ma >= _trix;
	return myWasAboveOrEqual !== myIsAboveOrEqual;
});

// Cross marker, placed at the Trix value, only on cross candles
const myCrossMarks = for_every(myTrix, myCrossSignal, (_trix, _cross) => _cross ? constants.icons.cross : null);
// Renamed this painted series so its name no longer collides with the
// register_signal() name below (both can't share the exact same name).
paint(myCrossMarks, { name: 'Trix Cross MA Marker', style: 'labels_above', color: '#ffffff', thickness: 2 });

// Dynamic fill color: Trix color (above) or MA color (below), only when fill enabled.
// Note: fill() only accepts a single static color, not a per-point series.
// color_cloud() is the correct function for a dynamically colored band
// between two lines, and it also handles the "disable fill" case by using
// fully transparent colors when myUseFill is false.
const myFillColorAbove = myUseFill ? '#5b9bf5' : 'rgba(0,0,0,0)';
const myFillColorBelow = myUseFill ? '#ffee58' : 'rgba(0,0,0,0)';
color_cloud(myTrix, myMa, myFillColorAbove, myFillColorBelow, 'Trix Above', 'Trix Below');

// Signals for scanner/alerts/strategy use
register_signal(myCrossSignal, 'Trix Cross MA');
register_signal(for_every(myTrix, myMa, (_trix, _ma) => _trix !== null && _ma !== null && _trix > _ma), 'Trix Above MA');
register_signal(for_every(myTrix, myMa, (_trix, _ma) => _trix !== null && _ma !== null && _trix < _ma), 'Trix Below MA');

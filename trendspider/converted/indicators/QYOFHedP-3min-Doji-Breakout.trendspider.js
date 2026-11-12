/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : 3min Doji Breakout
 * Author       : himashu911363
 * Source URL   : https://www.tradingview.com/script/QYOFHedP-3min-Doji-Breakout
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Doji Breakout 3m_TV
 *
 * Deviations from the original: Reviewed AI draft; previous completed 3m bar values (no look-ahead); labels as
 *   icons; trade lines and alert text not carried over; best used on charts of 3m or
 *   lower.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Doji Breakout 3m_TV', 'price');
const myWickMult = input.number('Body < X * Wicks', 0.2, { min: 0.01, max: 2, step: 0.05 });
const my3m = await request.history(current.ticker, '3');
assert(!my3m.error, 'Error fetching 3m data: ' + my3m.error);
const myIsDoji = my3m.close.map((_c, _i) => {
	const myBody = Math.abs(_c - my3m.open[_i]);
	const myWicks = (my3m.high[_i] - Math.max(my3m.open[_i], _c)) + (Math.min(my3m.open[_i], _c) - my3m.low[_i]);
	return myWicks > 0 ? myBody < myWicks * myWickMult : false;
});
// request.security(..., high[1]): the previous completed 3m bar, landed from its successor's open
const myLand = (_vals) => interpolate_sparse_series(land_points_onto_series(my3m.time, shift(_vals, 1), time, 'le'), 'constant');
const myDojiHigh = myLand(my3m.high);
const myDojiLow = myLand(my3m.low);
const myDojiCheck = myLand(myIsDoji.map(_b => _b ? 1 : 0));
const myBuy = close.map((_c, _i) => myDojiCheck[_i] === 1 && myDojiHigh[_i] !== null && _c > myDojiHigh[_i]);
const mySell = close.map((_c, _i) => myDojiCheck[_i] === 1 && myDojiLow[_i] !== null && _c < myDojiLow[_i]);
let myLastH = null, myLastL = null;
const myLastHigh = close.map((_c, _i) => { if (myDojiCheck[_i] === 1) myLastH = myDojiHigh[_i]; return myLastH; });
const myLastLow = close.map((_c, _i) => { if (myDojiCheck[_i] === 1) myLastL = myDojiLow[_i]; return myLastL; });
paint(myLastHigh, { name: 'Doji High', color: '#FFD600', thickness: 2 });
paint(myLastLow, { name: 'Doji Low', color: '#FFD600', thickness: 2 });
paint(myDojiCheck.map(_c => _c === 1 ? constants.icons.triangle_down : null), { name: 'Doji Mark', style: 'labels_above', color: 'yellow' });
paint(myBuy.map(_b => _b ? constants.icons.triangle_up : null), { name: 'Buy Mark', style: 'labels_below', color: '#00C853' });
paint(mySell.map(_s => _s ? constants.icons.triangle_down : null), { name: 'Sell Mark', style: 'labels_above', color: '#D50000' });
register_signal(myBuy, '3m Buy Breakout');
register_signal(mySell, '3m Sell Breakout');
register_signal(myDojiCheck.map(_c => _c === 1), 'Doji Detected');

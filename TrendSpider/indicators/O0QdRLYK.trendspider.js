/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : IFR Níveis Móveis
 * Author       : cristianoveludo
 * Source URL   : https://www.tradingview.com/script/O0QdRLYK
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : IFR Niveis Moveis_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact RSI; window highs/lows hand-rolled; bgcolor option not
 *   carried over; level styles not dashed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('IFR Niveis Moveis_TV', 'lower');
const mySrcName = input.select('Fonte de Dados', 'close', ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']);
const myPeriodo = input.number('Periodo do IFR', 14, { min: 1 });
const myOb = input.number('Sobrecompra fixo', 70, { min: 1, max: 100 });
const myOs = input.number('Sobrevenda fixo', 30, { min: 1, max: 100 });
const myMediaCurta = input.number('Media Curta', 9, { min: 1 });
const myMediaLonga = input.number('Media Longa', 50, { min: 1 });
const myLimites = input.number('Periodo Max/Min IFR', 200, { min: 1 });
const myPct = input.number('Taxa de Desconto %', 5, { min: 0, max: 100, step: 0.1 });
const myNiveisFixos = input.boolean('Mostrar Niveis Fixos', false);
const myColorir = input.boolean('Colorir Linha IFR', true);
const mySrc = close.map((_c, _i) => {
	if (mySrcName === 'open') return open[_i];
	if (mySrcName === 'high') return high[_i];
	if (mySrcName === 'low') return low[_i];
	if (mySrcName === 'hl2') return (high[_i] + low[_i]) / 2;
	if (mySrcName === 'hlc3') return (high[_i] + low[_i] + _c) / 3;
	if (mySrcName === 'ohlc4') return (open[_i] + high[_i] + low[_i] + _c) / 4;
	return _c;
});
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null) return myAcc;
		if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _n) myAcc = mySeed / _n; return myAcc; }
		myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc;
	});
};
const myG = myRma(mySrc.map((_v, _i) => _i === 0 ? null : Math.max(_v - mySrc[_i - 1], 0)), myPeriodo);
const myL = myRma(mySrc.map((_v, _i) => _i === 0 ? null : Math.max(mySrc[_i - 1] - _v, 0)), myPeriodo);
const myRsi = myG.map((_g, _i) => (_g === null || myL[_i] === null) ? null : (myL[_i] === 0 ? 100 : 100 - 100 / (1 + _g / myL[_i])));
const myWin = (_s, _n, _f) => _s.map((_v, _i) => {
	if (_i < _n - 1) return null;
	let myR = null;
	const myW = [];
	for (let myK = _i - _n + 1; myK <= _i; myK += 1) { if (_s[myK] === null) return null; myW.push(_s[myK]); }
	return _f(myW);
});
const myMax = myWin(myRsi, myLimites, _w => Math.max(..._w));
const myMin = myWin(myRsi, myLimites, _w => Math.min(..._w));
const myCentral = myMax.map((_v, _i) => (_v === null || myMin[_i] === null) ? null : (_v + myMin[_i]) / 2);
const mySup = myMax.map((_v, _i) => myCentral[_i] === null ? null : _v - myCentral[_i] * 2 * myPct / 100);
const myInf = myMin.map((_v, _i) => myCentral[_i] === null ? null : _v + myCentral[_i] * 2 * myPct / 100);
const myShort = myWin(myRsi, myMediaCurta, _w => _w.reduce((_a, _b) => _a + _b, 0) / myMediaCurta);
const myLong = myWin(myRsi, myMediaLonga, _w => _w.reduce((_a, _b) => _a + _b, 0) / myMediaLonga);
const myColor = myRsi.map((_r, _i) => !myColorir ? 'blue' : ((_r !== null && mySup[_i] !== null && _r >= mySup[_i]) ? 'red' : ((_r !== null && myInf[_i] !== null && _r <= myInf[_i]) ? 'green' : 'blue')));
paint(myRsi, { name: 'IFR', color: myColor, thickness: 2 });
paint(myShort, { name: 'Media Curta', color: 'green', thickness: 1 });
paint(myLong, { name: 'Media Longa', color: 'orange', thickness: 1 });
paint(mySup, { name: 'Nivel Sup Movel', color: 'red', thickness: 1 });
paint(myInf, { name: 'Nivel Inf Movel', color: 'green', thickness: 1 });
paint(myCentral, { name: 'Nivel Central', color: 'gray', thickness: 1 });
paint(myNiveisFixos ? horizontal_line(myOb) : close.map(() => null), { name: 'Sobrecompra Fixo', color: 'red' });
paint(myNiveisFixos ? horizontal_line(myOs) : close.map(() => null), { name: 'Sobrevenda Fixo', color: 'green' });
paint(myNiveisFixos ? horizontal_line(50) : close.map(() => null), { name: 'Nivel 50 Fixo', color: 'gray' });
register_signal(myRsi.map((_r, _i) => _r !== null && mySup[_i] !== null && _r >= mySup[_i]), 'IFR Acima Nivel Sup Movel');
register_signal(myRsi.map((_r, _i) => _r !== null && myInf[_i] !== null && _r <= myInf[_i]), 'IFR Abaixo Nivel Inf Movel');
register_signal(myRsi.map((_r, _i) => _r !== null && myShort[_i] !== null && _r > myShort[_i]), 'IFR Acima Media Curta');
register_signal(myRsi.map((_r, _i) => _r !== null && myShort[_i] !== null && _r < myShort[_i]), 'IFR Abaixo Media Curta');

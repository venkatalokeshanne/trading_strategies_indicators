describe_indicator('BB plus RSI Strategy Visualizer', 'price');

// NOTE: TrendSpider Custom JS does not have a native backtesting/strategy
// engine like Pine Script's strategy.*() calls. This script reproduces the
// Pine logic (Bollinger Bands + RSI entry conditions, fixed % stop-loss and
// a risk/reward based take-profit) and simulates the resulting single-position
// state (entry price, SL, TP) candle by candle in plain JS, assuming only one
// position can be open at a time, exactly like strategy.position_size==0 check
// in the original script. Position sizing (qty) is not visual and is omitted
// since it has no chart representation.

const myBBTab = input.tab('Bandas de Bollinger');
const myBBLength = myBBTab.number('Longitud BB', 20, { min: 1, max: 500 });
const myBBMult = myBBTab.number('Desv Estandar', 2, { min: 0.1, max: 10 });

const myRSITab = input.tab('RSI');
const myRSILength = myRSITab.number('Longitud RSI', 14, { min: 1, max: 200 });
const myRSIOverbought = myRSITab.number('Sobrecompra', 70, { min: 1, max: 99 });
const myRSIOversold = myRSITab.number('Sobreventa', 30, { min: 1, max: 99 });

const myRiskTab = input.tab('Gestion de Riesgo');
const myRiskRatio = myRiskTab.number('Ratio R/B', 2, { min: 0.1, max: 20 });
// shortened title to avoid "input(): name is too lengthy" error
const myStopLossPercent = myRiskTab.number('Dist. Stop Loss %', 0.5, { min: 0.01, max: 50, step: 0.1 });
const myStopLossFractionValue = myStopLossPercent / 100;

// === Indicators ===
const myBasis = sma(close, myBBLength);
const myBand = compute_band(myBasis, 'St.Dev.', myBBMult, myBBLength);
const myUpper = myBand.upper;
const myLower = myBand.lower;
const myRsi = rsi(close, myRSILength);

// === Conditions ===
const myLongCondition = for_every(close, myLower, myRsi, (_c, _l, _r) => (_c < _l) && (_r < myRSIOversold));
const myShortCondition = for_every(close, myUpper, myRsi, (_c, _u, _r) => (_c > _u) && (_r > myRSIOverbought));

// === Position simulation (single position at a time) ===
// State object kept across candles: { position: 0|1|-1, entry, sl, tp }
const myState = for_every(close, myLongCondition, myShortCondition, (_c, _lc, _sc, _prev, _idx) => {
	const myPrevState = _prev || { position: 0, entry: null, sl: null, tp: null };

	if (myPrevState.position === 0) {
		if (_lc) {
			return {
				position: 1,
				entry: _c,
				sl: _c * (1 - myStopLossFractionValue),
				tp: _c * (1 + myStopLossFractionValue * myRiskRatio)
			};
		}
		if (_sc) {
			return {
				position: -1,
				entry: _c,
				sl: _c * (1 + myStopLossFractionValue),
				tp: _c * (1 - myStopLossFractionValue * myRiskRatio)
			};
		}
		return { position: 0, entry: null, sl: null, tp: null };
	}
	else {
		// position already open: check if TP or SL was hit this candle to close it
		if (myPrevState.position === 1) {
			if (_c >= myPrevState.tp || _c <= myPrevState.sl) {
				return { position: 0, entry: null, sl: null, tp: null };
			}
		}
		else if (myPrevState.position === -1) {
			if (_c <= myPrevState.tp || _c >= myPrevState.sl) {
				return { position: 0, entry: null, sl: null, tp: null };
			}
		}
		return myPrevState;
	}
});

const myEntryLine = myState.map(_s => (_s && _s.position !== 0) ? _s.entry : null);
const myTpLine = myState.map(_s => (_s && _s.position !== 0) ? _s.tp : null);
const mySlLine = myState.map(_s => (_s && _s.position !== 0) ? _s.sl : null);

// === Paint Bollinger Bands ===
paint(myBasis, { name: 'Media BB', color: 'gray', thickness: 1 });
const myUpperPainted = paint(myUpper, { name: 'Banda Superior', color: 'red', thickness: 1, hidden: true });
const myLowerPainted = paint(myLower, { name: 'Banda Inferior', color: 'green', thickness: 1, hidden: true });
fill(myUpperPainted, myLowerPainted, 'blue', 0.05, 'Fondo BB');

// === Paint trade box lines ===
const myEntryPainted = paint(myEntryLine, { name: 'Linea Entrada', color: 'blue', thickness: 2, style: 'ladder' });
const myTpPainted = paint(myTpLine, { name: 'Linea Take Profit', color: 'green', thickness: 2, style: 'ladder' });
const mySlPainted = paint(mySlLine, { name: 'Linea Stop Loss', color: 'red', thickness: 2, style: 'ladder' });
fill(myEntryPainted, myTpPainted, 'green', 0.15, 'Caja Profit');
fill(myEntryPainted, mySlPainted, 'red', 0.15, 'Caja Loss');

// === Signals for Scanner / Alerts / Strategy Tester ===
register_signal(myLongCondition, 'Senal de Compra');
register_signal(myShortCondition, 'Senal de Venta');

const myPositionOpened = for_every(myState, (_s, _prev) => {
	const myPrevState = _prev;
	return !!(_s && _s.position !== 0 && (!myPrevState || myPrevState.position === 0));
});
register_signal(myPositionOpened, 'Posicion Abierta');

const myPositionClosed = for_every(myState, (_s, _prev) => {
	const myPrevState = _prev;
	return !!(myPrevState && myPrevState.position !== 0 && (!_s || _s.position === 0));
});
register_signal(myPositionClosed, 'Posicion Cerrada');
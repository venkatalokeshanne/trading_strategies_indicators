describe_indicator('CRT H3 Zonas Vela 0 and CHoCH', 'price');

// === Experimental note ===
// This is a best-effort conversion of a TradingView Pine Script strategy
// into a TrendSpider indicator. TradingView strategies (strategy.entry,
// strategy.exit, pyramiding, actual broker-style order execution) do not
// exist in the Custom JS API. This script reproduces the SIGNAL LOGIC
// (CRT H3 zone liquidity grabs + CHoCH entries) and exposes them as
// register_signal() outputs usable in Scanners/Alerts/Strategy Tester,
// plus visual lines/labels. It does not simulate actual trade fills,
// P/L, or TP/SL execution the way a Pine strategy would.
// Boxes (zonaH3) are not reproduced since drawing boxes is not supported
// by this API; the H3 vela 0 / vela 1 high-low levels are painted as
// lines instead, which conveys equivalent information.
// "180" minute bars and the daily reset are both assumed to use the
// America/New_York timezone (Pine's time("180") normally uses the
// chart's own timezone, but we align it with the daily reset timezone
// for consistency, since the API has no per-call timezone parameter).

const myMoment = library('moment-timezone');

const mySwingLen = input.number('Fuerza del Swing / CHoCH', 3, { min: 1, max: 50 });
const myRR = input.number('Risk Reward', 1.0, { min: 0.1, max: 20 });

// === Precompute pivots (must happen outside the loop) ===
const mySwingHighRaw = pivot_high(high, mySwingLen, mySwingLen);
const mySwingLowRaw = pivot_low(low, mySwingLen, mySwingLen);
const myPrevClose = shift(close, 1);

const myN = close.length;

// output series
const myH3High0 = series_of(null);
const myH3Low0 = series_of(null);
const myH3High1 = series_of(null);
const myH3Low1 = series_of(null);
const myTomaHighH3 = series_of(false);
const myTomaLowH3 = series_of(false);
const myCompra = series_of(false);
const myVenta = series_of(false);
const myStopCompra = series_of(null);
const myStopVenta = series_of(null);
const myTpCompra = series_of(null);
const myTpVenta = series_of(null);

let myLastDayKey = null;
let myLastBucketKey = null;

let myH3High0Val = null;
let myH3Low0Val = null;
let myH3High1Val = null;
let myH3Low1Val = null;

let myEntradaHoy = false;
let myBuscarVenta = false;
let myBuscarCompra = false;

let myLastSwingHigh = null;
let myLastSwingLow = null;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myTimestamp = time[myIndex];
	const myNYTime = myMoment.tz(myTimestamp * 1000, 'America/New_York');
	const myDayKey = myNYTime.format('YYYY-MM-DD');
	const myBucketKey = `${myDayKey}_${Math.floor(myNYTime.hours() / 3)}`;

	// === daily reset (New York) ===
	const myNuevoDiaNY = myLastDayKey !== null && myDayKey !== myLastDayKey;
	myLastDayKey = myDayKey;

	if (myNuevoDiaNY) {
		myEntradaHoy = false;
	}

	// === H3 bucket change detection ===
	const myNuevaH3 = myLastBucketKey !== null && myBucketKey !== myLastBucketKey;
	myLastBucketKey = myBucketKey;

	if (myH3High0Val === null) {
		myH3High0Val = high[myIndex];
		myH3Low0Val = low[myIndex];
	}
	else if (myNuevaH3) {
		myH3High1Val = myH3High0Val;
		myH3Low1Val = myH3Low0Val;

		myH3High0Val = high[myIndex];
		myH3Low0Val = low[myIndex];
	}
	else {
		myH3High0Val = Math.max(myH3High0Val, high[myIndex]);
		myH3Low0Val = Math.min(myH3Low0Val, low[myIndex]);
	}

	myH3High0[myIndex] = myH3High0Val;
	myH3Low0[myIndex] = myH3Low0Val;
	myH3High1[myIndex] = myH3High1Val;
	myH3Low1[myIndex] = myH3Low1Val;

	// === liquidity takes ===
	const myTomaHighH3Bar = myH3High1Val !== null && myH3High0Val > myH3High1Val;
	const myTomaLowH3Bar = myH3Low1Val !== null && myH3Low0Val < myH3Low1Val;

	myTomaHighH3[myIndex] = myTomaHighH3Bar;
	myTomaLowH3[myIndex] = myTomaLowH3Bar;

	// === states ===
	if (myNuevaH3) {
		myBuscarVenta = false;
		myBuscarCompra = false;
	}

	if (!myEntradaHoy && myTomaHighH3Bar) {
		myBuscarVenta = true;
		myBuscarCompra = false;
	}

	if (!myEntradaHoy && myTomaLowH3Bar) {
		myBuscarCompra = true;
		myBuscarVenta = false;
	}

	// === CHoCH tracking ===
	if (mySwingHighRaw[myIndex] !== null && mySwingHighRaw[myIndex] !== undefined) {
		myLastSwingHigh = mySwingHighRaw[myIndex];
	}
	if (mySwingLowRaw[myIndex] !== null && mySwingLowRaw[myIndex] !== undefined) {
		myLastSwingLow = mySwingLowRaw[myIndex];
	}

	const myChochAlcista = myLastSwingHigh !== null
		&& close[myIndex] > myLastSwingHigh
		&& myPrevClose[myIndex] <= myLastSwingHigh;

	const myChochBajista = myLastSwingLow !== null
		&& close[myIndex] < myLastSwingLow
		&& myPrevClose[myIndex] >= myLastSwingLow;

	// === entries (no live position tracking beyond "one trade per day") ===
	const myCompraBar = !myEntradaHoy && myBuscarCompra && myChochAlcista;
	const myVentaBar = !myEntradaHoy && myBuscarVenta && myChochBajista;

	const myStopCompraVal = myH3Low0Val;
	const myRiesgoCompra = close[myIndex] - myStopCompraVal;
	const myTpCompraVal = close[myIndex] + myRiesgoCompra * myRR;

	const myStopVentaVal = myH3High0Val;
	const myRiesgoVenta = myStopVentaVal - close[myIndex];
	const myTpVentaVal = close[myIndex] - myRiesgoVenta * myRR;

	myStopCompra[myIndex] = myStopCompraVal;
	myTpCompra[myIndex] = myTpCompraVal;
	myStopVenta[myIndex] = myStopVentaVal;
	myTpVenta[myIndex] = myTpVentaVal;

	if (myCompraBar && myRiesgoCompra > 0) {
		myCompra[myIndex] = true;
		myBuscarCompra = false;
		myEntradaHoy = true;
	}

	if (myVentaBar && myRiesgoVenta > 0) {
		myVenta[myIndex] = true;
		myBuscarVenta = false;
		myEntradaHoy = true;
	}
}

// === register signals for Scanners / Alerts / Strategy Tester ===
register_signal(myCompra, 'Compra CRT');
register_signal(myVenta, 'Venta CRT');
register_signal(myTomaHighH3, 'Toma High H3');
register_signal(myTomaLowH3, 'Toma Low H3');

// === lines ===
paint(myH3High0, { name: 'MaximoH3Vela0', color: '#e53935', thickness: 2 });
paint(myH3Low0, { name: 'MinimoH3Vela0', color: '#43a047', thickness: 2 });
paint(myH3High1, { name: 'MaximoH3Vela1', color: '#ef9a9a', thickness: 1, style: 'dotted' });
paint(myH3Low1, { name: 'MinimoH3Vela1', color: '#a5d6a7', thickness: 1, style: 'dotted' });

paint(myStopCompra, { name: 'StopCompra', color: '#2e7d32', thickness: 2 });
paint(myStopVenta, { name: 'StopVenta', color: '#c62828', thickness: 2 });

// === labels (markers) ===
const myTomaHighMarks = for_every(myTomaHighH3, _t => _t ? constants.icons.triangle_down : null);
const myTomaLowMarks = for_every(myTomaLowH3, _t => _t ? constants.icons.triangle_up : null);
const myCompraMarks = for_every(myCompra, _c => _c ? constants.icons.triangle_up : null);
const myVentaMarks = for_every(myVenta, _v => _v ? constants.icons.triangle_down : null);

paint(myTomaHighMarks, { name: 'TomaHighH3', style: 'labels_above', color: '#e53935' });
paint(myTomaLowMarks, { name: 'TomaLowH3', style: 'labels_below', color: '#43a047' });
paint(myCompraMarks, { name: 'CompraCRT', style: 'labels_below', color: '#2e7d32' });
paint(myVentaMarks, { name: 'VentaCRT', style: 'labels_above', color: '#c62828' });
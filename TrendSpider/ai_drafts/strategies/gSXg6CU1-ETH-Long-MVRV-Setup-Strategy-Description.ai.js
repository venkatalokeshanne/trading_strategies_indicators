describe_indicator('ETH Long MVRV Setup', 'price');

// NOTE: This is a conversion of a Pine Script v6 strategy into a
// TrendSpider indicator. TrendSpider Custom JS indicators cannot place
// actual orders, manage position sizing or execute multi-target
// exits (strategy.entry / strategy.exit). Those parts of the Pine
// script are not expressible here. Instead, the long entry condition
// is exposed as a register_signal() so it can be used in Scanners,
// Alerts and the Strategy Tester module of TrendSpider.

const myTab = input.tab('Trade Levels');
const myEntryRow = myTab.row();
const myEntryZoneLow = myEntryRow.number('Entry Zone Lower', 1800.0, { min: 0, max: 1000000 });
const myEntryZoneHigh = myEntryRow.number('Entry Zone Upper', 1950.0, { min: 0, max: 1000000 });

const myTpRow = myTab.row();
const mySlLevel = myTpRow.number('Stop Loss', 1680.0, { min: 0, max: 1000000 });
const myTp1Level = myTpRow.number('TP1 Realized Price', 2245.0, { min: 0, max: 1000000 });

const myTpRow2 = myTab.row();
const myTp2Level = myTpRow2.number('TP2 Intermediate', 2650.0, { min: 0, max: 1000000 });
const myTp3Level = myTpRow2.number('TP3 Final Target', 3000.0, { min: 0, max: 1000000 });

const myRsiTab = input.tab('RSI / Filters');
const myRsiRow = myRsiTab.row();
const myRsiLowBound = myRsiRow.number('RSI Lower Bound', 45, { min: 0, max: 100 });
const myRsiHighBound = myRsiRow.number('RSI Upper Bound', 70, { min: 0, max: 100 });

// ─── Technical Indicators (same math as Pine ta.ema / ta.rsi / ta.sma) ───
const myEma21 = ema(close, 21);
const myEma55 = ema(close, 55);
const myEma200 = ema(close, 200);
const myRsi = rsi(close, 14);
const myVolMa = sma(volume, 20);

// ─── Entry Condition, replicates Pine's longCondition exactly ───
// Note: "strategy.position_size == 0" cannot be replicated here since
// there is no actual position tracking in an indicator context; that
// clause is omitted (approximation), meaning this signal can fire on
// consecutive bars if all other conditions are still true.
const myLongCondition = for_every(
	close, myEma21, myEma55, myRsi, volume, myVolMa,
	(_close, _ema21, _ema55, _rsiValue, _volume, _volMa) => (
		_close >= myEntryZoneLow &&
		_close <= myEntryZoneHigh &&
		_ema21 > _ema55 &&
		_close > 1800.0 &&
		_rsiValue > myRsiLowBound &&
		_rsiValue < myRsiHighBound &&
		_volume > _volMa
	)
);

register_signal(myLongCondition, 'Long Entry Condition');

// ─── Level Visualization ───
paint(myEma21, { name: 'EMA 21', color: '#f4c20d', thickness: 1 });
paint(myEma55, { name: 'EMA 55', color: '#ff9800', thickness: 1 });
paint(myEma200, { name: 'EMA 200', color: '#e53935', thickness: 2 });

paint(horizontal_line(1580.0), { name: 'Support 1580', color: '#9e9e9e', style: 'dotted' });
const myEntryLevelLine = paint(horizontal_line(1800.0), { name: 'MVRV 08 1800', color: '#00e5ff', thickness: 2 });
paint(horizontal_line(2245.0), { name: 'Realized 2245', color: '#9c27b0', style: 'dotted', thickness: 2 });
paint(horizontal_line(myTp2Level), { name: 'TP2 2650', color: '#8bc34a', style: 'dotted' });
paint(horizontal_line(3000.0), { name: 'Target 3000', color: '#2e7d32', thickness: 2 });
paint(horizontal_line(mySlLevel), { name: 'SL 1680', color: '#d32f2f', thickness: 2 });

// ─── Entry Zone Band ───
fill(
	paint(horizontal_line(myEntryZoneHigh), { name: 'Entry Zone Upper', color: '#2962ff', hidden: true }),
	paint(horizontal_line(myEntryZoneLow), { name: 'Entry Zone Lower', color: '#2962ff', hidden: true }),
	'#2962ff',
	0.12
);

// ─── Info Table (replaces Pine's table.new / table.cell) ───
paint_overlay('TradeLevelsInfo', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'Parameter', color: '#f4c20d' }, { text: 'Level', color: '#f4c20d' }] },
		{ cells: [{ text: 'Entry (zone)', color: '#ffffff' }, { text: '1800 to 1950', color: '#00e5ff' }] },
		{ cells: [{ text: 'Stop Loss', color: '#ffffff' }, { text: '1680', color: '#e53935' }] },
		{ cells: [{ text: 'TP1 (40%)', color: '#ffffff' }, { text: '2245', color: '#8bc34a' }] },
		{ cells: [{ text: 'TP2 (35%)', color: '#ffffff' }, { text: '2650', color: '#8bc34a' }] },
		{ cells: [{ text: 'TP3 (25%)', color: '#ffffff' }, { text: '3000', color: '#2e7d32' }] },
		{ cells: [{ text: 'R:R', color: '#ffffff' }, { text: 'approx 1 to 4.5', color: '#9c27b0' }] }
	]
});
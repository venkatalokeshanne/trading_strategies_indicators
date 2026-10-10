describe_indicator('Custom Position Size Calculator', 'price');

// ─── Inputs ────────────────────────────────────────────────
const fixedTab = input.tab('Fixed / Instrument settings');
const myAccountSize = fixedTab.number('Account size (US$)', 100000.0, { min: 0 });
const myPipSize = fixedTab.number('Pip size', 0.0001, { min: 0 });
const myPipValue = fixedTab.number('Pip value / 1.0 lot (US$)', 10.0, { min: 0 });

const tradeTab = input.tab('Trade parameters');
const myTp = tradeTab.number('TP (pips)', 10.4, { min: 0 });
const mySl = tradeTab.number('S/L (pips)', 5.2, { min: 0.01 });
const myRiskPct = tradeTab.number('Total risk (%) per trade', 1.0, { min: 0.01, max: 100 });

// ─── Calculations ──────────────────────────────────────────
const myRiskAmount = myAccountSize * myRiskPct / 100.0;
const myLots = mySl > 0 ? myRiskAmount / (mySl * myPipValue) : 0.0;
const myRr = mySl > 0 ? myTp / mySl : 0.0;
const myGrossProfit = myRiskAmount * myRr;
const myBeWinrate = myRr > 0 ? 100.0 / (1.0 + myRr) : 0.0;

// helper formatting
const myFmt2 = _v => _v.toFixed(2);
const myFmtMoney = _v => _v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// ─── Table (overlay) ─────────────────────────────────────────────────
paint_overlay('PositionSizeCalculator', { position: 'bottom_left' }, {
	rows: [
		{ cells: [{ text: 'Position Size Calculator', color: 'white', background_color: '#2962FF', align: 'center' }] },
		{ cells: [{ text: 'Account size', align: 'left' }, { text: myFmtMoney(myAccountSize) + ' US$', align: 'right' }] },
		{ cells: [{ text: 'Pip size', align: 'left' }, { text: String(myPipSize), align: 'right' }] },
		{ cells: [{ text: 'Pip value / 1.0 lot', align: 'left' }, { text: myFmt2(myPipValue) + ' US$', align: 'right' }] },
		{ cells: [{ text: 'Custom inputs', color: 'white', background_color: '#808080' }] },
		{ cells: [{ text: 'TP (pips)', align: 'left', background_color: 'rgba(255,255,0,0.15)' }, { text: myFmt2(myTp), align: 'right', background_color: 'rgba(255,255,0,0.15)' }] },
		{ cells: [{ text: 'S/L (pips)', align: 'left', background_color: 'rgba(255,255,0,0.15)' }, { text: myFmt2(mySl), align: 'right', background_color: 'rgba(255,255,0,0.15)' }] },
		{ cells: [{ text: 'Risk % per trade', align: 'left', background_color: 'rgba(0,128,0,0.15)' }, { text: myFmt2(myRiskPct) + ' %', align: 'right', background_color: 'rgba(0,128,0,0.15)' }] },
		{ cells: [{ text: 'Output', color: 'white', background_color: '#808080' }] },
		{ cells: [{ text: 'Lots / position', align: 'left', background_color: 'rgba(0,128,128,0.2)' }, { text: myFmt2(myLots) + ' Lots', align: 'right', background_color: 'rgba(0,128,128,0.2)' }] },
		{ cells: [{ text: 'Gross profit (TP) + RR', align: 'left' }, { text: myFmtMoney(myGrossProfit) + ' US$  |  1:' + myFmt2(myRr) + ' RR', align: 'right', color: 'green' }] },
		{ cells: [{ text: 'Risk / Entry (SL)', align: 'left' }, { text: myFmtMoney(myRiskAmount) + ' US$', align: 'right', color: 'red' }] },
		{ cells: [{ text: 'Req. / BE winrate', align: 'left' }, { text: myFmt2(myBeWinrate) + ' %', align: 'right' }] }
	]
});

// ─── Signals for scanners/alerts/backtests ────────────────────────────
register_signal(series_of(myLots), 'Lots Per Position');
register_signal(series_of(myRr), 'Risk Reward Ratio');
register_signal(series_of(myRiskAmount), 'Risk Amount');
register_signal(series_of(myBeWinrate), 'Breakeven Winrate');
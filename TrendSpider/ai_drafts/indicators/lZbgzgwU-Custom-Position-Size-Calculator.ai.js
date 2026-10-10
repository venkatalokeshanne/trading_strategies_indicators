describe_indicator('Position Size and RR Calculator', 'price');

// This indicator is a pure calculator (position sizing / risk-reward).
// It has no price-action-based condition, so there is no genuine
// true/false "signal" to expose to scanners/alerts/strategies.
// We still register a constant signal (always true) just so the
// indicator can technically be referenced in Visual Scripts, but it
// carries no real trading meaning.

const fixedTab = input.tab('Fixed / Instrument settings');
const myAccountSize = fixedTab.number('Account size (USD)', 100000.0, { min: 0 });
const myPipSize = fixedTab.number('Pip size', 0.0001, { min: 0 });
const myPipValue = fixedTab.number('Pip value per 1.0 lot (USD)', 10.0, { min: 0 });

const tradeTab = input.tab('Trade parameters');
const myTp = tradeTab.number('TP (pips)', 10.4, { min: 0 });
const mySl = tradeTab.number('S/L (pips)', 5.2, { min: 0.01 });
const myRiskPct = tradeTab.number('Total risk percent per trade', 1.0, { min: 0.01, max: 100 });

// ─── Calculations (mirrors the Pine script math exactly) ───
const myRiskAmount = myAccountSize * myRiskPct / 100.0;
const myLots = mySl > 0 ? myRiskAmount / (mySl * myPipValue) : 0.0;
const myRr = mySl > 0 ? myTp / mySl : 0.0;
const myGrossProfit = myRiskAmount * myRr;
const myBeWinrate = myRr > 0 ? 100.0 / (1.0 + myRr) : 0.0;

// Simple number formatter mimicking str.tostring(value, "#,###.00")
function myFormatThousands(myValue) {
	const myParts = myValue.toFixed(2).split('.');
	myParts[0] = myParts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
	return myParts.join('.');
}

function myFormatTwoDecimals(myValue) {
	return (Math.round(myValue * 100) / 100).toString();
}

paint_overlay('PositionSizeCalculator', { position: 'bottom_left' }, {
	rows: [
		{
			cells: [
				{ text: 'Position Size Calculator', color: 'white', background_color: '#2962FF', align: 'center' }
			]
		},
		{
			cells: [
				{ text: 'Account size', align: 'left' },
				{ text: myFormatThousands(myAccountSize) + ' USD', align: 'right' }
			]
		},
		{
			cells: [
				{ text: 'Pip size', align: 'left' },
				{ text: myPipSize.toString(), align: 'right' }
			]
		},
		{
			cells: [
				{ text: 'Pip value / 1.0 lot', align: 'left' },
				{ text: myFormatTwoDecimals(myPipValue) + ' USD', align: 'right' }
			]
		},
		{
			cells: [
				{ text: 'Custom inputs', color: 'white', background_color: 'gray' }
			]
		},
		{
			cells: [
				{ text: 'TP (pips)', align: 'left', background_color: 'rgba(255,255,0,0.15)' },
				{ text: myFormatTwoDecimals(myTp), align: 'right', background_color: 'rgba(255,255,0,0.15)' }
			]
		},
		{
			cells: [
				{ text: 'S/L (pips)', align: 'left', background_color: 'rgba(255,255,0,0.15)' },
				{ text: myFormatTwoDecimals(mySl), align: 'right', background_color: 'rgba(255,255,0,0.15)' }
			]
		},
		{
			cells: [
				{ text: 'Risk percent per trade', align: 'left', background_color: 'rgba(0,128,0,0.15)' },
				{ text: myFormatTwoDecimals(myRiskPct) + ' %', align: 'right', background_color: 'rgba(0,128,0,0.15)' }
			]
		},
		{
			cells: [
				{ text: 'Output', color: 'white', background_color: 'gray' }
			]
		},
		{
			cells: [
				{ text: 'Lots per position', align: 'left', background_color: 'rgba(0,128,128,0.2)' },
				{ text: myFormatTwoDecimals(myLots) + ' Lots', align: 'right', background_color: 'rgba(0,128,128,0.2)' }
			]
		},
		{
			cells: [
				{ text: 'Gross profit (TP) plus RR', align: 'left' },
				{ text: myFormatThousands(myGrossProfit) + ' USD  |  1 to ' + myFormatTwoDecimals(myRr) + ' RR', align: 'right', color: 'green' }
			]
		},
		{
			cells: [
				{ text: 'Risk / Entry (SL)', align: 'left' },
				{ text: myFormatThousands(myRiskAmount) + ' USD', align: 'right', color: 'red' }
			]
		},
		{
			cells: [
				{ text: 'Required / BE winrate', align: 'left' },
				{ text: myFormatTwoDecimals(myBeWinrate) + ' %', align: 'right' }
			]
		}
	]
});

// Dummy constant signal, only present to allow Visual Script usage.
// It carries no real trading meaning since this script is a calculator.
const myAlwaysTrueSignal = series_of(true);
register_signal(myAlwaysTrueSignal, 'Calculator Active');
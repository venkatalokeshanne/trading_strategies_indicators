describe_indicator('Mini Market Minds - Futures Contract Calculator', 'price');

// ================= RISK SETTINGS =================
const riskTab = input.tab('Risk Settings');
const myUsePercentage = riskTab.boolean('Use % of Account?', false);
const myAccountBalance = riskTab.number('Account Balance ($)', 50000.00, { min: 0.01 });
const myRiskPercent = riskTab.number('Risk Per Trade (%)', 1.00, { min: 0.01 });
const myFixedRisk = riskTab.number('Fixed Risk Amount ($)', 500.00, { min: 0.01 });
const mySlPoints = riskTab.number('Stop Loss (Points)', 20.00, { min: 0.01 });

// ================= COLOR SETTINGS =================
const colorTab = input.tab('Colors');
const myHeaderBg = colorTab.color('Header Background', 'rgb(53, 24, 78)');
const myHeaderText = colorTab.color('Header Text', 'rgb(235, 188, 75)');
const myColumnBg = colorTab.color('Column Header Background', 'rgb(197, 54, 137)');
const myColumnText = colorTab.color('Column Header Text', 'white');
const myValueBg = colorTab.color('Value Background', 'rgb(8, 8, 12)');
const myValueText = colorTab.color('Value Text', 'rgb(235, 188, 75)');
const myBorderColor = colorTab.color('Border Color', 'rgb(235, 188, 75)');

// ================= SYMBOL DETECTION =================
// syminfo.root equivalent: current.root (futures root symbol)
const mySymbolName = current.root || current.ticker;

// ================= FUTURES VALUE PER FULL POINT =================
const myPointValueMap = {
	MNQ: 2.00,
	NQ: 20.00,
	MES: 5.00,
	ES: 50.00,
	MYM: 0.50,
	YM: 5.00,
	MGC: 10.00,
	GC: 100.00
};

const myPointValue = myPointValueMap.hasOwnProperty(mySymbolName) ? myPointValueMap[mySymbolName] : null;

// ================= RISK AMOUNT =================
const myRiskAmount = myUsePercentage
	? myAccountBalance * myRiskPercent / 100
	: myFixedRisk;

// ================= CONTRACT CALCULATION =================
// Contracts = Risk / (Stop Loss x Value Per Point), always rounded down
const myRawContracts = (myPointValue !== null && mySlPoints > 0)
	? myRiskAmount / (mySlPoints * myPointValue)
	: null;

const myContractSize = myRawContracts !== null ? Math.floor(myRawContracts) : null;

// Actual risk after rounding down
const myActualRisk = myContractSize !== null
	? myContractSize * mySlPoints * myPointValue
	: null;

// Register a signal so this calculator's validity can be used in
// Scanners/Alerts/Strategy Tester. Since this script does not produce
// trading entry/exit logic (it is a position-size calculator only),
// the only meaningful binary signal is "a valid contract size was
// computed for the current symbol and settings".
const myValidContractSignal = series_of(myContractSize !== null && myContractSize > 0);
register_signal(myValidContractSignal, 'Valid Contract Size');

// Format numbers similarly to Pine's str.tostring with "#.##"
function myFormatNumber(myValue, myDecimals) {
	if (myValue === null || myValue === undefined || isNaN(myValue)) return 'N/A';
	return Number(myValue.toFixed(myDecimals)).toString();
}

const mySlPointsText = myFormatNumber(mySlPoints, 2);
const myContractSizeText = myContractSize !== null ? myFormatNumber(myContractSize, 0) : 'N/A';
const myActualRiskText = myActualRisk !== null ? `$${myFormatNumber(myActualRisk, 2)}` : 'N/A';

paint_overlay('MiniMarketMindsCalculator', { position: 'top_right' }, {
	rows: [{
		cells: [
			{ text: '', background_color: myHeaderBg },
			{ text: `${mySymbolName} FUTURES`, color: myHeaderText, background_color: myHeaderBg },
			{ text: '', background_color: myHeaderBg }
		]
	}, {
		cells: [
			{ text: 'SL (PTS)', color: myColumnText, background_color: myColumnBg },
			{ text: 'CONTRACTS', color: myColumnText, background_color: myColumnBg },
			{ text: 'RISK ($)', color: myColumnText, background_color: myColumnBg }
		]
	}, {
		cells: [
			{ text: mySlPointsText, color: myValueText, background_color: myValueBg },
			{ text: myContractSizeText, color: myValueText, background_color: myValueBg },
			{ text: myActualRiskText, color: myValueText, background_color: myValueBg }
		]
	}]
});
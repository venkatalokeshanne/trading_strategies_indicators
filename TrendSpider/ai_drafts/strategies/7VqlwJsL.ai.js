// EXPERIMENT: TrendSpider has no built-in strategy/backtest engine
// accessible from Custom JS indicators (no strategy.*, no
// strategy.closedtrades, no table.cell callbacks). This script
// reproduces the Pine logic by manually simulating one position at
// a time, bar by bar, computing the same win/loss/EV/Bayesian/CI
// stats, and shows them via paint_overlay(). Entry/exit price logic
// (SL/TP, RR) is reproduced exactly as in the Pine script. External
// signals cannot be "read" from other indicators either in Pine or
// here, so they are exposed as manual boolean toggle inputs, exactly
// like the original script did.
describe_indicator('Auto Logger Signal Tracker', 'lower');

// --- Inputs ---
const mainTab = input.tab('Main');
// Shortened title to satisfy platform's input title length limit.
const myBaseWinRate = mainTab.number('Bayesian Base WR Pct', 10.0, { min: 0, max: 100 }) / 100.0;
const myTargetRR = mainTab.number('Target RR Ratio', 19.0, { min: 0.01, max: 100 });

const signalsTab = input.tab('Signal Mapping');

// Note: input() titles have a length limit on this platform, so the
// long descriptive signal names have been shortened below.
const rowA = signalsTab.row();
const myS1Long = rowA.boolean('UAlgo Long', false);
const myS1Short = rowA.boolean('UAlgo Short', false);

const rowB = signalsTab.row();
const myS2Long = rowB.boolean('KhanSaab Long', false);
const myS2Short = rowB.boolean('KhanSaab Short', false);

const rowC = signalsTab.row();
const myS3Long = rowC.boolean('CRT HTF Long', false);
const myS3Short = rowC.boolean('CRT HTF Short', false);

const rowD = signalsTab.row();
const myS4Long = rowD.boolean('AlgoAlpha Trend Long', false);
const myS4Short = rowD.boolean('AlgoAlpha Trend Short', false);

const rowE = signalsTab.row();
const myS5Long = rowE.boolean('Sultan BO Long', false);
const myS5Short = rowE.boolean('Sultan BO Short', false);

const rowF = signalsTab.row();
const myS6Long = rowF.boolean('AlgoAlpha BO Long', false);
const myS6Short = rowF.boolean('AlgoAlpha BO Short', false);

// NOTE: since these are static (non-time-varying) booleans, the
// aggregated long/short signal is constant for the whole chart,
// identical to how it would behave in Pine with constant inputs.
const myLongSignalFlag = myS1Long || myS2Long || myS3Long || myS4Long || myS5Long || myS6Long;
const myShortSignalFlag = myS1Short || myS2Short || myS3Short || myS4Short || myS5Short || myS6Short;

const myCandleCount = close.length;
const myLongSignalSeries = series_of(myLongSignalFlag);
const myShortSignalSeries = series_of(myShortSignalFlag);

// --- Simulation state ---
let myPositionSize = 0; // 0 = flat, 1 = long, -1 = short
let myEntryPrice = 0;
let myEntryIndex = 0;
let mySL = 0;
let myTP = 0;
let myTotalTrades = 0;
let myWins = 0;
let myLosses = 0;
let myTotalWinAmount = 0;
let myTotalLossAmount = 0;
let myTotalDuration = 0;
let myEquity = 10000000;
let myPeakEquity = 10000000;
let myMaxDrawdown = 0;

const myEntryMarks = series_of(null);
const myExitMarks = series_of(null);
const mySLSeries = series_of(null);
const myTPSeries = series_of(null);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myClose = close[myIndex];
	const myHigh = high[myIndex];
	const myLow = low[myIndex];

	// check exits first (stop/limit), one position at a time
	if (myPositionSize === 1) {
		let myExitPrice = null;
		if (myLow <= mySL) {
			myExitPrice = mySL;
		}
		else if (myHigh >= myTP) {
			myExitPrice = myTP;
		}

		if (myExitPrice !== null) {
			const myPnl = (myExitPrice - myEntryPrice);
			myTotalTrades += 1;
			myTotalDuration += (myIndex - myEntryIndex);
			if (myPnl > 0) {
				myWins += 1;
				myTotalWinAmount += myPnl;
			}
			else {
				myLosses += 1;
				myTotalLossAmount += Math.abs(myPnl);
			}
			myEquity += myPnl;
			myPeakEquity = Math.max(myPeakEquity, myEquity);
			myMaxDrawdown = Math.max(myMaxDrawdown, myPeakEquity - myEquity);
			myExitMarks[myIndex] = myExitPrice;
			myPositionSize = 0;
		}
	}
	else if (myPositionSize === -1) {
		let myExitPrice = null;
		if (myHigh >= mySL) {
			myExitPrice = mySL;
		}
		else if (myLow <= myTP) {
			myExitPrice = myTP;
		}

		if (myExitPrice !== null) {
			const myPnl = (myEntryPrice - myExitPrice);
			myTotalTrades += 1;
			myTotalDuration += (myIndex - myEntryIndex);
			if (myPnl > 0) {
				myWins += 1;
				myTotalWinAmount += myPnl;
			}
			else {
				myLosses += 1;
				myTotalLossAmount += Math.abs(myPnl);
			}
			myEquity += myPnl;
			myPeakEquity = Math.max(myPeakEquity, myEquity);
			myMaxDrawdown = Math.max(myMaxDrawdown, myPeakEquity - myEquity);
			myExitMarks[myIndex] = myExitPrice;
			myPositionSize = 0;
		}
	}

	// check entries (only if flat), mirrors Pine's "strategy.position_size == 0"
	if (myPositionSize === 0) {
		if (myLongSignalFlag) {
			mySL = myLow * 0.99;
			myTP = myClose + (myClose - mySL) * myTargetRR;
			myEntryPrice = myClose;
			myEntryIndex = myIndex;
			myPositionSize = 1;
			myEntryMarks[myIndex] = myClose;
		}
		else if (myShortSignalFlag) {
			mySL = myHigh * 1.01;
			myTP = myClose - (mySL - myClose) * myTargetRR;
			myEntryPrice = myClose;
			myEntryIndex = myIndex;
			myPositionSize = -1;
			myEntryMarks[myIndex] = myClose;
		}
	}

	mySLSeries[myIndex] = myPositionSize !== 0 ? mySL : null;
	myTPSeries[myIndex] = myPositionSize !== 0 ? myTP : null;
}

// --- Statistics (computed once over full data set, as of "last bar") ---
const myWinRate = myTotalTrades > 0 ? myWins / myTotalTrades : 0.0;
const myAvgWin = myWins > 0 ? myTotalWinAmount / myWins : 0.0;
const myAvgLoss = myLosses > 0 ? myTotalLossAmount / myLosses : 0.0;
const myEV = (myWinRate * myAvgWin) - ((1.0 - myWinRate) * myAvgLoss);
const myPF = myTotalLossAmount > 0 ? myTotalWinAmount / myTotalLossAmount : null;
const myAvgDuration = myTotalTrades > 0 ? myTotalDuration / myTotalTrades : 0.0;

const myAlphaPrior = myBaseWinRate * 10.0;
const myBetaPrior = (1.0 - myBaseWinRate) * 10.0;
const myPosteriorWinRate = (myAlphaPrior + myWins) / (myAlphaPrior + myBetaPrior + myTotalTrades);

const myUtilityEV = myTotalTrades > 0
	? (Math.pow(myAvgWin, 0.88) * myWinRate) - (Math.pow(myAvgLoss, 0.88) * (1.0 - myWinRate))
	: 0.0;

const myZ = 1.96;
const myCIMargin = myTotalTrades > 0
	? myZ * Math.sqrt((myWinRate * (1 - myWinRate)) / myTotalTrades)
	: 0.0;

const myMaxDrawdownPercent = (myMaxDrawdown / 10000000) * 100;

// --- Register signals so this is usable in scanners/alerts/strategies ---
register_signal(myLongSignalSeries, 'Long Entry Signal');
register_signal(myShortSignalSeries, 'Short Entry Signal');

// --- Paint lines ---
paint(mySLSeries, { name: 'Stop Loss', color: 'red', style: 'ladder' });
paint(myTPSeries, { name: 'Take Profit', color: 'green', style: 'ladder' });
paint(myEntryMarks, { name: 'Entries', style: 'labels_below', color: 'blue' });
paint(myExitMarks, { name: 'Exits', style: 'labels_above', color: 'orange' });

// --- Stats overlay table ---
const myColorWinRate = 'lime';
const myColorLoss = 'red';
const myColorEV = myEV >= 0 ? 'lime' : 'red';
const myColorPF = 'yellow';
const myColorDuration = 'white';
const myColorBayes = 'aqua';
const myColorCI = 'gray';
const myColorUtility = 'orange';

paint_overlay('AutoLoggerStatsTable', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'Total Trades', color: 'white' }, { text: String(myTotalTrades), color: 'white' }] },
		{ cells: [{ text: 'Wins / Losses', color: 'white' }, { text: `${myWins} / ${myLosses}`, color: 'white' }] },
		{ cells: [{ text: 'Win Rate %', color: 'white' }, { text: `${(myWinRate * 100).toFixed(2)}%`, color: myColorWinRate }] },
		{ cells: [{ text: 'Avg Win', color: 'white' }, { text: myAvgWin.toFixed(0), color: myColorWinRate }] },
		{ cells: [{ text: 'Avg Loss', color: 'white' }, { text: myAvgLoss.toFixed(0), color: myColorLoss }] },
		{ cells: [{ text: 'Expected Value', color: 'white' }, { text: myEV.toFixed(0), color: myColorEV }] },
		{ cells: [{ text: 'Profit Factor', color: 'white' }, { text: myPF === null ? 'NA' : myPF.toFixed(2), color: myColorPF }] },
		{ cells: [{ text: 'Avg Duration Bars', color: 'white' }, { text: myAvgDuration.toFixed(2), color: myColorDuration }] },
		{ cells: [{ text: 'Bayesian Post WR', color: 'white' }, { text: `${(myPosteriorWinRate * 100).toFixed(2)}%`, color: myColorBayes }] },
		{ cells: [{ text: '95 Percent CI WR', color: 'white' }, { text: `+/- ${(myCIMargin * 100).toFixed(2)}%`, color: myColorCI }] },
		{ cells: [{ text: 'Utility Ux', color: 'white' }, { text: myUtilityEV.toFixed(2), color: myColorUtility }] },
		{ cells: [{ text: 'Max Drawdown', color: 'white' }, { text: `${myMaxDrawdownPercent.toFixed(2)}%`, color: myColorLoss }] }
	]
});
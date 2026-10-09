describe_indicator('Anh Manh Dep Trai Strategy', 'price');

// Inputs matching the original Pine Script inputs
const myGreenBars = input.number('So nen xanh', 3, { min: 1, max: 50 });
const myN = input.number('Nhap N', 5, { min: 1, max: 500 });
const myM = input.number('Nhap M', 1.0, { min: -10, max: 10, step: 0.01 });

// avgVal = sma((open + low) / 2, n), computed once outside any loop
const myAvgVal = sma(div(add(open, low), 2), myN);

const myStopLoss = series_of(null);
const myBuySignal = series_of(false);
const myExitSignal = series_of(false);

// Sequential state machine replicating the Pine Script logic bar by bar.
// NOTE: strategy.entry() fills are assumed to take effect starting the bar
// AFTER the signal bar (TradingView default order fill behavior), while
// strategy.exit() (stop order) is assumed to fill intrabar, same bar the
// stop level is crossed. This is the closest reproducible approximation
// of TradingView's strategy execution model within this scripting engine.
let myCountGreen = 0;
let myPosition = 0;
let myStopLossValue = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	myCountGreen = (open[myIndex] < close[myIndex]) ? myCountGreen + 1 : 0;

	let myBuy = false;
	let myExit = false;

	if (myCountGreen == myGreenBars && myPosition == 0) {
		myBuy = true;
		myStopLossValue = myAvgVal[myIndex];
	}

	if (myPosition > 0) {
		myStopLossValue = myStopLossValue * (1 + myM);

		if (low[myIndex] <= myStopLossValue) {
			myExit = true;
		}
	}

	myStopLoss[myIndex] = myStopLossValue;
	myBuySignal[myIndex] = myBuy;
	myExitSignal[myIndex] = myExit;

	if (myBuy) {
		myPosition = 1;
	}
	if (myExit) {
		myPosition = 0;
	}
}

// Register signals for scanners, alerts and strategy tester
register_signal(myBuySignal, 'Buy Signal');
register_signal(myExitSignal, 'Exit Buy Signal');

// Paint lines, reproducing plot(close) and plot(stopLoss, color=color.red)
paint(close, { name: 'Close', color: '#2962FF', thickness: 1 });
paint(myStopLoss, { name: 'Stop Loss', color: '#EF5350', thickness: 2 });
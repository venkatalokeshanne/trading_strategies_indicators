describe_indicator('9 EMA 20 EMA Retest Strategy', 'price');

// NOTE: Pine's time(timeframe.period, session, "Asia/Kolkata") pins the
// session filter to IST regardless of the chart's exchange timezone.
// The Custom JS API only exposes time_of() in the EXCHANGE timezone,
// so this is approximated using the exchange timezone's own clock.
// If your chart's exchange timezone is not IST, the session window
// will not line up exactly with the original Pine script.

const myFastLength = input.number('9 EMA Length', 9, { min: 1, max: 500 });
const mySlowLength = input.number('20 EMA Length', 20, { min: 1, max: 500 });
const myRiskReward = input.number('Risk Reward Ratio', 3.0, { min: 0.1, max: 50, step: 0.1 });
const mySessionStartHour = input.number('Session Start Hour', 9, { min: 0, max: 23 });
const mySessionStartMinute = input.number('Session Start Minute', 0, { min: 0, max: 59 });
const mySessionEndHour = input.number('Session End Hour', 16, { min: 0, max: 23 });
const mySessionEndMinute = input.number('Session End Minute', 0, { min: 0, max: 59 });

const myEma9 = ema(close, myFastLength);
const myEma20 = ema(close, mySlowLength);

paint(myEma9, { color: '#2962ff', thickness: 2, name: 'EMA9' });
paint(myEma20, { color: '#ef5350', thickness: 2, name: 'EMA20' });

const myBuySignal = series_of(null);
const mySellSignal = series_of(null);
const myBuyConditionSeries = series_of(false);
const mySellConditionSeries = series_of(false);

let myAllowBuy = false;
let myAllowSell = false;
let myPosition = 0; // 0 = flat, 1 = long, -1 = short
let myStopLoss = null;
let myTakeProfit = null;

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myBullCross = myEma9[myIndex] > myEma20[myIndex] && myEma9[myIndex - 1] <= myEma20[myIndex - 1];
	const myBearCross = myEma20[myIndex] > myEma9[myIndex] && myEma20[myIndex - 1] <= myEma9[myIndex - 1];

	if (myBullCross) {
		myAllowBuy = true;
		myAllowSell = false;
	}
	if (myBearCross) {
		myAllowSell = true;
		myAllowBuy = false;
	}

	const myBullTrend = myEma9[myIndex] > myEma20[myIndex];
	const myBearTrend = myEma20[myIndex] > myEma9[myIndex];

	const myBuyRetest = low[myIndex] <= myEma9[myIndex] || low[myIndex] <= myEma20[myIndex];
	const mySellRetest = high[myIndex] >= myEma9[myIndex] || high[myIndex] >= myEma20[myIndex];

	const myBullishCandle = close[myIndex] > open[myIndex];
	const myBearishCandle = close[myIndex] < open[myIndex];

	const myTimeInfo = time_of(time[myIndex]);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const mySessionStartMinutes = mySessionStartHour * 60 + mySessionStartMinute;
	const mySessionEndMinutes = mySessionEndHour * 60 + mySessionEndMinute;
	const myInSession = myMinutesOfDay >= mySessionStartMinutes && myMinutesOfDay <= mySessionEndMinutes;

	const myBuyCondition = myAllowBuy && myBullTrend && myBuyRetest && myBullishCandle && myInSession;
	const mySellCondition = myAllowSell && myBearTrend && mySellRetest && myBearishCandle && myInSession;

	myBuyConditionSeries[myIndex] = myBuyCondition;
	mySellConditionSeries[myIndex] = mySellCondition;

	// Manage open position (check stop/limit hit first, using this bar's range)
	if (myPosition === 1) {
		if (low[myIndex] <= myStopLoss || high[myIndex] >= myTakeProfit) {
			myPosition = 0;
			myStopLoss = null;
			myTakeProfit = null;
		}
	}
	else if (myPosition === -1) {
		if (high[myIndex] >= myStopLoss || low[myIndex] <= myTakeProfit) {
			myPosition = 0;
			myStopLoss = null;
			myTakeProfit = null;
		}
	}

	// New entries only when flat
	if (myPosition === 0 && myBuyCondition) {
		const myEntryPrice = close[myIndex];
		const myRisk = myEntryPrice - low[myIndex];
		myStopLoss = low[myIndex];
		myTakeProfit = myEntryPrice + (myRisk * myRiskReward);
		myPosition = 1;
		myBuySignal[myIndex] = low[myIndex];
	}
	else if (myPosition === 0 && mySellCondition) {
		const myEntryPrice = close[myIndex];
		const myRisk = high[myIndex] - myEntryPrice;
		myStopLoss = high[myIndex];
		myTakeProfit = myEntryPrice - (myRisk * myRiskReward);
		myPosition = -1;
		mySellSignal[myIndex] = high[myIndex];
	}
}

paint(myBuySignal, { style: 'labels_below', color: 'green', name: 'BuySignal' });
paint(mySellSignal, { style: 'labels_above', color: 'red', name: 'SellSignal' });

register_signal(myBuyConditionSeries, 'Buy Condition');
register_signal(mySellConditionSeries, 'Sell Condition');
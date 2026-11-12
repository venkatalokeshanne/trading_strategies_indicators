<code x-ref="code" class="hljs" data-clipboard-text>/*
	This is an example of a strategy which is fully coded in JS. This is the
	approach you take in case if you want to do things which our Visual Scripting
	does not support.

 	The overall structure is simple:

    1. compute all the indicators involved into the strategy
	2. customize functions which flag whether you should enter or exit at a given candle
    3. that's it

 	The strategy below is an example of an SMA cross strategy, accompanied with a Stop Loss of 1.5%
*/
describe_indicator('Example of a pure custom JS strategy');

//	customize these indicators. compute all the indicators involved in your strategy here
const longMA = sma(close, input.number('Long', 40));
const shortMA = sma(close, input.number('Short', 10));
const stopLossPercentage = input.number('SL%', 1.5);

let currentPosition = null;


//	customize this function. it should return true any time there should be 
//	an entry at a candle number "candleIndex". this function is not supposed
//	to check whether you're currently in a position or not. it's safe to assume
//	that you're not.
function shouldEnterAtCandle(candleIndex) {
	return shortMA[candleIndex - 1] < longMA[candleIndex - 1] &&
		shortMA[candleIndex] > longMA[candleIndex];
}

//	customize this function. it should return true any time there should be 
//	an exit at a candle number "candleIndex". this function is not supposed
//	to check whether you're currently in a position or not. it's safe to assume
//	that you are.
function shouldExitAtCandle(candleIndex) {
	const stopLossLevel = currentPosition.entryPrice * (100 - stopLossPercentage) / 100;
	const stopLossSignalsExit = close[candleIndex] < stopLossLevel;
	
	if (stopLossSignalsExit) {
		return 'SL';
	}

	const maCrossSignalsExit = shortMA[candleIndex - 1] > longMA[candleIndex - 1] &&
		shortMA[candleIndex] < longMA[candleIndex];
	
	return maCrossSignalsExit ? 'cross' : false;
}

//	you probably don't want to go further in the code with your customizations, 
//	unless you want to go really deep

const entrySignals = series_of(null);
const exitSignals = series_of(null);
const entryLabels = series_of(null);
const exitLabels = series_of(null);

//	this loop checks every candle and builds position-aware entry/exit signals
//	it does not allow entering at the same candle right after exiting.
//	you're not supposed to modify this loop unless you want to change things like
//	"can enter on exit candle" and such
for (let candleIndex = 0; candleIndex < close.length; candleIndex += 1) {
	const entryReason = shouldEnterAtCandle(candleIndex);


	if (!currentPosition && entryReason) {
		currentPosition = {
			entryCandleIndex: candleIndex,
			entryPrice: market.close[candleIndex]
		};

		entrySignals[candleIndex] = true;
		entryLabels[candleIndex] = 'Entry';
	}

	if (currentPosition) {
		const exitReason = shouldExitAtCandle(candleIndex);

		if (exitReason) {
			currentPosition = null;
			exitSignals[candleIndex] = true;
			exitLabels[candleIndex] = `Exit ${exitReason}`;		
		}
	}
}


register_signal(entrySignals, 'Entry');
register_signal(exitSignals, 'Exit');

paint(exitLabels, { color: '#8c29a8', backgroundColor: '#8c29a8', style: 'labels_above' });
paint(entryLabels, { color: 'blue', backgroundColor: 'blue', style: 'labels_below' });</code>
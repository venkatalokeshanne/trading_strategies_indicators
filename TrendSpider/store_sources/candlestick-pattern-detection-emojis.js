<code x-ref="code" class="hljs" data-clipboard-text>/*
This script identifies candlestick patterns defined by a Regular Expression.

The script defines its own tiny alphabet, where each character marks a particular case:

😘: candle which closes more than ATR above prev close
😚: candle which closes above the prev close
😡: candle which closes more than ATR below prev close
😤: candle which closes below prev close
😏: green candle which is none of the above 
😩: red candle which is none of the above 
*/
const MY_PATTERN = '😡😡😤{1,3}(😘|😚)+';
describe_indicator(`CandleStick Pattern Detection & Emojis ${MY_PATTERN}`);

const atrSeries = atr(14);

const candleLabel = candleIndex => {
	if (close[candleIndex] > close[candleIndex - 1] + atrSeries[candleIndex - 1]) {
		return '😘';
	}
	
	if (close[candleIndex] > close[candleIndex - 1]) {
		return '😚';
	}


	if (close[candleIndex] < close[candleIndex - 1] - atrSeries[candleIndex - 1]) {
		return '😡';
	}

	if (close[candleIndex] < close[candleIndex - 1]) {
		return '😤';
	}

	
	return close[candleIndex] > open[candleIndex]
		? '😏'
		: '😩';
};



const codesOfCandles = close.map((dummy, index) => candleLabel(index))
const codesAsString = codesOfCandles.join('');

const borderUp = series_of(null);
const borderDown = series_of(null);

for (const occurence of codesAsString.matchAll(MY_PATTERN)) {
	const thisPattern = occurence[0];

	//	these smilies take 2 bytes each
	const patternStartSymbols = occurence.index / 2;
	const patternLengthSymbols = thisPattern.length / 2;
	
	const patternEndIndex = patternStartSymbols + patternLengthSymbols;
	
	const hh = Math.max(...high.slice(patternStartSymbols, patternEndIndex));
	borderUp.splice(patternStartSymbols - 1, patternLengthSymbols + 2, ...[...Array(patternLengthSymbols + 2)].map(() => hh));

	const ll = Math.min(...low.slice(patternStartSymbols, patternEndIndex));
	borderDown.splice(patternStartSymbols - 1, patternLengthSymbols + 2, ...[...Array(patternLengthSymbols + 2)].map(() => ll));
}

paint(codesOfCandles, { style: 'labels_above', fontSize: 20 });

fill(
	paint(borderUp, { name: 'Up', color: 'blue' }),
	paint(borderDown, { name: 'Down', color: 'blue' }),
	'blue'
);
</code>
<code x-ref="code" class="hljs" data-clipboard-text>/*
This script identifies candlestick patterns defined by sequence of candle colors.
The sequence should be defined as a Regular Expression.

The script defins its own tiny alphabet, where each character marks a particular case:

J: candle which closes more than ATR above prev close
U: candle which closes above the prev close
F: candle which closes more than ATR below prev close
D: candle which closes below prev close
G: green candle which is none of the above 
R: red candle which is none of the above 

I.e., GGRG means "green candle, then green candle, then red candle,
then yet another green candle". G..R means "green, then any, then any, then red".
G{3,}R means "at least 3 green in a row and then 1 red".

FF.{,3}JJJ means "2 drops down, then up to 3 <whatever> candles, then 3 jumps up"
*/
const MY_PATTERN = 'FFD{1,3}(U|J){3}';
describe_indicator(`CandleStick Pattern Detection & Labeling ${MY_PATTERN}`);

const PATTERN_COLOR = 'violet';

const atrSeries = atr(14);

const candleLabel = candleIndex => {
	if (close[candleIndex] > close[candleIndex - 1] + atrSeries[candleIndex - 1]) {
		return 'J';
	}
	
	if (close[candleIndex] > close[candleIndex - 1]) {
		return 'U';
	}


	if (close[candleIndex] < close[candleIndex - 1] - atrSeries[candleIndex - 1]) {
		return 'F';
	}

	if (close[candleIndex] < close[candleIndex - 1]) {
		return 'D';
	}

	
	return close[candleIndex] > open[candleIndex]
		? 'G'
		: 'R';
};



const codesOfCandles = close.map((dummy, index) => candleLabel(index))
const codesAsString = codesOfCandles.join('');

const borderUp = series_of(null);
const borderDown = series_of(null);

for (const occurence of codesAsString.matchAll(MY_PATTERN)) {
	const thisPattern = occurence[0];
	
	const patternEndIndex = occurence.index + thisPattern.length;
	
	const hh = Math.max(...high.slice(occurence.index, patternEndIndex));
	borderUp.splice(occurence.index - 1, thisPattern.length + 2, ...[...Array(thisPattern.length + 2)].map(() => hh));

	const ll = Math.min(...low.slice(occurence.index, patternEndIndex));
	borderDown.splice(occurence.index - 1, thisPattern.length + 2, ...[...Array(thisPattern.length + 2)].map(() => ll));
}

paint(codesOfCandles, { style: 'labels_above' });

fill(
	paint(borderUp, { name: 'Up', color: 'blue' }),
	paint(borderDown, { name: 'Down', color: 'blue' }),
	'blue'
);</code>
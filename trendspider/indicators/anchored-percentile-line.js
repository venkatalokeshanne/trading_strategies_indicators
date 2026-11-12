<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Percentile Line Anchored', 'price', { shortName: 'Perc. L' })

const priceSource = input('Price source', 'ohlc4', constants.price_source_options);
const candleToAnchorTo = input_anchor();

if (!candleToAnchorTo) {
	throw Error('No suitable anchoring point found');
}

const price = prices[priceSource];
const jstat = library('jstat');


function anchoredPLine(fromIndex, percentileIndex) {
  const result = series_of(null);

  for (let candleIndex = fromIndex + 1; candleIndex < price.length; candleIndex += 1) {
    const pricesAccumulated = price.slice(fromIndex, candleIndex);

    const pricesWeigthedByVolume = pricesAccumulated.map((value, index) => value);
    const percentileValue = jstat.percentile(pricesWeigthedByVolume, percentileIndex / 100)

    result[candleIndex] = percentileValue;
  }

  return result;
}

const p0 = paint(anchoredPLine(candleToAnchorTo.candleIndex, 0), { color: 'blue' });
const p25 = paint(anchoredPLine(candleToAnchorTo.candleIndex, 25), { color: 'navy' });
const p50 = paint(anchoredPLine(candleToAnchorTo.candleIndex, 50), { color: 'black', thickness: 2 });
const p75 = paint(anchoredPLine(candleToAnchorTo.candleIndex, 75), { color: 'navy' });
const p100 = paint(anchoredPLine(candleToAnchorTo.candleIndex, 100), { color: 'blue' });

fill(p0, p25, 'skyblue');
fill(p25, p50, 'blue');
fill(p50, p75, 'blue');
fill(p75, p100, 'skyblue');</code>
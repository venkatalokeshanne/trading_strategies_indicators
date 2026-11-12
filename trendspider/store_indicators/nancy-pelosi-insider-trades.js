<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Nancy Pelosi Trade Tracker');

const binarySearch = library('binary-search-bounds');

const data = await request.congress_trading(current.ticker);
assert(!data.error, `Error fetching data: ${data.error}`);

const myBuySignals = series_of(null);
const myBuys = series_of(null);
const mySellSignals = series_of(null);
const mySells = series_of(null);

for (const report of data) {
    const candleIndex = binarySearch.ge(time, report.timestamp);
    if (candleIndex < 0) {
        continue;
    }
    
    // Filter for Nancy Pelosi's trades only
    if (report.representative !== "Nancy Pelosi") {
        continue;
    }
    
    if (report.transaction === 'purchase') {
        myBuys[candleIndex] = `Nancy Pelosi<br/>buy`;
        myBuySignals[candleIndex] = true;
    } else {
        mySells[candleIndex] = `Nancy Pelosi<br/>sell`;
        mySellSignals[candleIndex] = true;
    }
}

paint(myBuys, {
    style: 'labels_below',
    backgroundColor: 'green',
    color: 'white',
    verticalOffset: 20
});

paint(mySells, {
    style: 'labels_above',
    backgroundColor: 'red',
    color: 'white'
});

register_signal(myBuySignals, 'Pelosi Buys');
register_signal(mySellSignals, 'Pelosi Sells');</code>
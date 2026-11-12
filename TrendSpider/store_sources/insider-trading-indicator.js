<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Insider Trades On Chart');

// Call the function for the current ticker
await plotInsiderActions(constants.ticker);

// Function to plot insider actions and register signals
async function plotInsiderActions(ticker) {
    const trades = await request.insider_trading(ticker);
    
    const buys = trades.transactions.filter(item => item.transaction == 'buy');
    const sells = trades.transactions.filter(item => item.transaction == 'sell');
    const gifts = trades.transactions.filter(item => item.transaction == 'gift' || item.transaction == 'award');

    const buysLanded = land_points_onto_series(
        buys.map(item => item.timestamp),
        buys.map(() => ticker == constants.ticker ? 'buy' : `${ticker} buy`),
        time, 'ge'
    );

    const sellsLanded = land_points_onto_series(
        sells.map(item => item.timestamp),
        sells.map(() => ticker == constants.ticker ? 'sell' : `${ticker} sell`),
        time, 'ge'
    );

    const giftsLanded = land_points_onto_series(
        gifts.map(item => item.timestamp),
        gifts.map(() => ticker == constants.ticker ? 'gift' : `${ticker} gift`),
        time, 'ge'
    );

    paint(sellsLanded, { style: 'labels_above', color: 'red', backgroundBorderRadius: 4, backgroundColor: 'red' });
    paint(buysLanded, { style: 'labels_below', color: 'green', backgroundBorderRadius: 4, backgroundColor: 'green' });
    paint(giftsLanded, { style: 'labels_below', color: 'blue', backgroundBorderRadius: 4, backgroundColor: 'blue' });

    // Register signals for visual scripting
    const buySignals = buysLanded.map(label => label !== null);
    const sellSignals = sellsLanded.map(label => label !== null);
    const giftSignals = giftsLanded.map(label => label !== null);

    register_signal(buySignals, 'Buy Signal');
    register_signal(sellSignals, 'Sell Signal');
    register_signal(giftSignals, 'Gift Signal');
}

</code>
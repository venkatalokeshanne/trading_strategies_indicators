<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Pre-market range');
//    30 is the highest time frame which still has candles not overlapping with
//    the market session
const extHoursData = await request.history(constants.ticker, '30', { ext_session: true });
const preMarketRangeByDay = {};
//    first, we compute { high, low } of pre-market
//    per each day we have in our ext data session
for (let extHoursIndex = 0; extHoursIndex < extHoursData.time.length; extHoursIndex += 1) {
    const sessionAtCandle = session_of(
        extHoursData.time[extHoursIndex],
        constants.resolution,
        constants.ext_session_premarket
    );
    const dayOfCandle = sessionAtCandle.session;
    if (!preMarketRangeByDay[dayOfCandle]) {
        preMarketRangeByDay[dayOfCandle] = {
            high: extHoursData.high[extHoursIndex],
            low: extHoursData.low[extHoursIndex]
        };
    }
    else {
        preMarketRangeByDay[dayOfCandle].high = Math.max(preMarketRangeByDay[dayOfCandle].high, extHoursData.high[extHoursIndex]);
        preMarketRangeByDay[dayOfCandle].low = Math.min(preMarketRangeByDay[dayOfCandle].low, extHoursData.low[extHoursIndex]);
    }
}
const rangeHigh = series_of(null);
const rangeLow = series_of(null);
const lastSession = session_of(time[time.length - 1], constants.resolution);
//    now we assigning "pre-market high/low range" to each candle on the chart
for (let candleIndex = 0; candleIndex < time.length; candleIndex += 1) {
    const sessionAtCandle = session_of(time[candleIndex], constants.resolution);
    const isLastSession = sessionAtCandle.session == lastSession.session;
    const extHoursRange = preMarketRangeByDay[sessionAtCandle.session];
    if (isLastSession && extHoursRange) {
        rangeHigh[candleIndex] = extHoursRange.high;
        rangeLow[candleIndex] = extHoursRange.low;
    }
    if ( (rangeHigh[candleIndex] != rangeHigh[candleIndex - 1]) || rangeLow[candleIndex] != rangeLow[candleIndex - 1]) {
        rangeHigh[candleIndex - 1] = null;
        rangeLow[candleIndex - 1] = null;
    }
}
paint(rangeHigh, { style: 'ladder', color: 'black' });
paint(rangeLow, { style: 'ladder', color: 'black' });</code>
<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Dollar Index Emulator (DXY)', 'lower');

// Fetch historical data for all required currency pairs in parallel
const [eurusdData, usdjpyData, gbpusdData, usdcadData, usdsekData, usdchfData] = await Promise.all([
    request.history('^EURUSD', current.resolution),
    request.history('^USDJPY', current.resolution),
    request.history('^GBPUSD', current.resolution),
    request.history('^USDCAD', current.resolution),
    request.history('^USDSEK', current.resolution),
    request.history('^USDCHF', current.resolution)
]);

// Verify all data fetched successfully
assert(!eurusdData.error, 'Error fetching EURUSD data: ' + eurusdData.error);
assert(!usdjpyData.error, 'Error fetching USDJPY data: ' + usdjpyData.error);
assert(!gbpusdData.error, 'Error fetching GBPUSD data: ' + gbpusdData.error);
assert(!usdcadData.error, 'Error fetching USDCAD data: ' + usdcadData.error);
assert(!usdsekData.error, 'Error fetching USDSEK data: ' + usdsekData.error);
assert(!usdchfData.error, 'Error fetching USDCHF data: ' + usdchfData.error);

// Find the minimum common length among all datasets to ensure alignment
const myMinLength = Math.min(
    eurusdData.close.length,
    usdjpyData.close.length,
    gbpusdData.close.length,
    usdcadData.close.length,
    usdsekData.close.length,
    usdchfData.close.length
);

// Slice all series to the minimum common length
const eurusdSliced = eurusdData.close.slice(-myMinLength);
const usdjpySliced = usdjpyData.close.slice(-myMinLength);
const gbpusdSliced = gbpusdData.close.slice(-myMinLength);
const usdcadSliced = usdcadData.close.slice(-myMinLength);
const usdsekSliced = usdsekData.close.slice(-myMinLength);
const usdchfSliced = usdchfData.close.slice(-myMinLength);
const timeSliced = eurusdData.time.slice(-myMinLength);

// Calculate the formula for each candle on the source data
const myFormulaResult = for_every(
    eurusdSliced,
    usdjpySliced,
    gbpusdSliced,
    usdcadSliced,
    usdsekSliced,
    usdchfSliced,
    (_eurusd, _usdjpy, _gbpusd, _usdcad, _usdsek, _usdchf) => {
        if (_eurusd === null || _usdjpy === null || _gbpusd === null ||
            _usdcad === null || _usdsek === null || _usdchf === null) {
            return null;
        }
        
        return 50.14348112 *
            Math.pow(_eurusd, -0.576) *
            Math.pow(_usdjpy, 0.136) *
            Math.pow(_gbpusd, -0.119) *
            Math.pow(_usdcad, 0.091) *
            Math.pow(_usdsek, 0.042) *
            Math.pow(_usdchf, 0.036);
    }
);

// Land the computed formula result onto the current chart's timeframe
const formulaLanded = land_points_onto_series(timeSliced, myFormulaResult, time, 'ge');
const formulaInterpolated = interpolate_sparse_series(formulaLanded, 'constant');

paint(formulaInterpolated, { name: 'Currency Formula', color: 'blue' });</code>
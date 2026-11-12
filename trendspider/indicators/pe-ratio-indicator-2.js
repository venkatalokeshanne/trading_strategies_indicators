<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('P/E Ratio', 'lower');

const epsMathType = input('P/E Type', 'Trailing', ['Qtr', 'Trailing']);
const earnings = await request.earnings(constants.ticker);

if (!Array.isArray(earnings)) {
    return;
}

const pastEarnings = earnings.filter(record => !record.isFuture);
const epsSeries = pastEarnings.map(record => record.eps);
const trailingEpsSeries = sum(epsSeries, 4);
const values = epsMathType == 'Qtr' ? epsSeries : trailingEpsSeries;
const timestamps = pastEarnings.map(record => record.timestamp);

const epsLanded = land_points_onto_series(
    timestamps,
    values,
    time,
    'ge'
);

let epsInterpolated = interpolate_sparse_series(epsLanded, 'constant');

if (epsInterpolated[epsInterpolated.length - 1] == null) {
    epsInterpolated = horizontal_line(values[values.length - 1]);
}

const resultingLine = for_every(close, epsInterpolated, (c, eps) => c / eps);

paint(resultingLine, { name: 'PE Ratio', color: 'grey' });</code>
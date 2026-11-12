<code x-ref="code" class="hljs" data-clipboard-text>// This indicator was made by AI and has not been QA checked by the TrendSpider development team. The indicator is for informational purposes only.

describe_indicator('Sector, Industry, Market Cap, & Change Metrics (Horizontal Layout)');

// Input toggles for rows
const showMarketCap = input.boolean('Show Market Cap', true);
const showDailyChange = input.boolean('Show Daily Change%', true);
const showWTDChange = input.boolean('Show WTD Change%', true);
const showMTDChange = input.boolean('Show MTD Change%', true);
const showYTDChange = input.boolean('Show YTD Change%', true);

// Fetch all necessary data concurrently
const [fundamentals, dailyHistory, weeklyHistory, monthlyHistory, yearlyHistory] = await Promise.all([
    request.fundamental(current.ticker, ['market_cap']),
    request.history(current.ticker, 'D'),
    request.history(current.ticker, 'W'),
    request.history(current.ticker, 'M'),
    request.history(current.ticker, 'Y')
]);

// Validate data fetching
[
    { data: fundamentals, name: 'fundamentals' },
    { data: dailyHistory, name: 'dailyHistory' },
    { data: weeklyHistory, name: 'weeklyHistory' },
    { data: monthlyHistory, name: 'monthlyHistory' },
    { data: yearlyHistory, name: 'yearlyHistory' }
].forEach(({ data, name }) => {
    assert(!data.error, `Error fetching ${name}: ${data.error}`);
});

// Format Market Cap
const marketCap = fundamentals.market_cap[0]?.value
    ? `$${Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(fundamentals.market_cap[0].value)}`
    : 'N/A';

// Calculate percentage changes
function calculateChange(currentClose, periodOpen) {
    return periodOpen ? ((currentClose - periodOpen) / periodOpen * 100).toFixed(2) : 'N/A';
}

// Extract opening prices for respective periods
const dailyOpen = dailyHistory.open[dailyHistory.open.length - 1];
const weeklyOpen = weeklyHistory.open[weeklyHistory.open.length - 1];
const monthlyOpen = monthlyHistory.open[monthlyHistory.open.length - 1];
const yearlyOpen = yearlyHistory.open[yearlyHistory.open.length - 1];

// Extract the latest close price
const latestClose = dailyHistory.close[dailyHistory.close.length - 1];

// Calculate changes based on opening prices
const dailyChange = calculateChange(latestClose, dailyOpen);
const wtdChange = calculateChange(latestClose, weeklyOpen);
const mtdChange = calculateChange(latestClose, monthlyOpen);
const ytdChange = calculateChange(latestClose, yearlyOpen);

// Define cell styling
const titleCell = (text) => ({ text, fontWeight: 'bold', color: 'white', background: 'var(--background-color-highlight)', padding: '5px 10px' });
const valueCell = (text, color) => ({ text, color, padding: '5px 10px' });

// Create a single horizontal row for all metrics
const rows = [
    {
        cells: [
            titleCell('Sector / Industry'),
            valueCell(`${current.sector} / ${current.industry}`, 'var(--text-color)'),
            showMarketCap ? titleCell('Market Cap') : null,
            showMarketCap ? valueCell(marketCap, 'var(--text-color)') : null,
            showDailyChange ? titleCell('Day%') : null,
            showDailyChange ? valueCell(`${dailyChange}%`, dailyChange > 0 ? 'green' : dailyChange < 0 ? 'red' : 'var(--text-color)') : null,
            showWTDChange ? titleCell('WTD%') : null,
            showWTDChange ? valueCell(`${wtdChange}%`, wtdChange > 0 ? 'green' : wtdChange < 0 ? 'red' : 'var(--text-color)') : null,
            showMTDChange ? titleCell('MTD%') : null,
            showMTDChange ? valueCell(`${mtdChange}%`, mtdChange > 0 ? 'green' : mtdChange < 0 ? 'red' : 'var(--text-color)') : null,
            showYTDChange ? titleCell('YTD%') : null,
            showYTDChange ? valueCell(`${ytdChange}%`, ytdChange > 0 ? 'green' : ytdChange < 0 ? 'red' : 'var(--text-color)') : null
        ].filter(Boolean) // Remove null values from the row
    }
];

// Paint the overlay with the dynamically built rows
paint_overlay('Table', { position: 'top_right', order: 'above_all' }, {
    fontSize: 12,
    border: '1px solid var(--border-color)',
    background: 'var(--background-color)',
    rows
});
</code>
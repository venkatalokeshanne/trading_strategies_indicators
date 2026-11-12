<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Fundamentals Strip');

// Define customizable settings using input functions
const backgroundColor = input.color('Background Color', '#000000'); // Default black background
const backgroundOpacity = input.number('Background Opacity', 0.3, { min: 0, max: 1, step: 0.1 }); // Default opacity
const fontSize = input.number('Font Size', 13, { min: 8, max: 20, step: 1 }); // Default font size
const beatTextColor = input.color('Beat Text Color', '#2ecc53'); // Default green for positive changes
const missTextColor = input.color('Miss Text Color', '#ff0000'); // Default red for negative changes

const moment = library('moment-timezone');

const [weeklyHistory, fundamentals, earnings, insider] = await Promise.all([
    request.history(current.ticker, 'W'),
    request.fundamental(current.ticker, [
        'revenue',
        'market_cap',
        'cash_cash_equivalents',
        'long_term_debt',
        'gross_profit',
        'operating_income_loss',
        'net_income',
        'dividends_paid',
        'cash_from_repurchase_equity',
        'free_cash_flow',
        'enterprise_value',
        'debt_ratio',
        'current_ratio',
        'ps_ratio_ttm',
        'pe_ratio_ttm',
        'price_to_book_value'
    ], 20),
    request.earnings(current.ticker, { filters: [{ field: 'timestamp', filter: 'greater', value: 0 }] }),
    request.insider_trading(current.ticker)
]);

assert(!weeklyHistory.error, `Error fetching W data: ${weeklyHistory.error}`);
assert(!fundamentals.error, `Error fetching fundamentals: ${fundamentals.error}`);
assert(!earnings.error, `Error fetching earnings: ${earnings.error}`);
assert(!insider.error, `Error fetching insider_trading: ${insider.error}`);

const formatLargeNumber = (value, decimals = 0) => isNaN(value) ? '—' : Intl.NumberFormat('en-US', { notation: "compact", maximumFractionDigits: decimals }).format(value);
const formatRatio = (value) => isNaN(value) ? '—' : value.toFixed(2);
const currentFundamental = metricId => fundamentals[metricId][0] ? fundamentals[metricId][0].value : undefined;
const cashValue = currentFundamental('cash_cash_equivalents') ? `$${formatLargeNumber(currentFundamental('cash_cash_equivalents'), 1)}` : '—';
const longTermDebtValue = currentFundamental('long_term_debt') ? `$${formatLargeNumber(currentFundamental('long_term_debt'), 1)}` : '—';

// Income Statement (YoY)
const trailingFourQuartersRevenue = fundamentals.revenue.slice(0, 4).reduce((sum, record) => sum + record.value, 0);
const previousFourQuartersRevenue = fundamentals.revenue.slice(4, 8).reduce((sum, record) => sum + record.value, 0);
const revenueYoYChange = previousFourQuartersRevenue ? ((trailingFourQuartersRevenue - previousFourQuartersRevenue) / previousFourQuartersRevenue * 100).toFixed(1) : '—';
const revenueBaseValue = trailingFourQuartersRevenue ? `$${formatLargeNumber(trailingFourQuartersRevenue, 1)}` : '—';
const revenueChangeValue = revenueYoYChange !== '—' ? `${revenueYoYChange}% YoY` : '';

const trailingFourQuartersGrossProfit = fundamentals.gross_profit.slice(0, 4).reduce((sum, record) => sum + record.value, 0);
const previousFourQuartersGrossProfit = fundamentals.gross_profit.slice(4, 8).reduce((sum, record) => sum + record.value, 0);
const trailingGrossMargin = trailingFourQuartersRevenue ? (trailingFourQuartersGrossProfit / trailingFourQuartersRevenue * 100).toFixed(1) : '—';
const previousGrossMargin = previousFourQuartersRevenue ? (previousFourQuartersGrossProfit / previousFourQuartersRevenue * 100).toFixed(1) : '—';
const grossMarginYoYChange = previousGrossMargin !== '—' ? ((trailingGrossMargin - previousGrossMargin) / previousGrossMargin * 100).toFixed(1) : '—';
const grossMarginBaseValue = trailingGrossMargin !== '—' ? `${trailingGrossMargin}%` : '—';
const grossMarginChangeValue = grossMarginYoYChange !== '—' ? `${grossMarginYoYChange}% YoY` : '';

const trailingFourQuartersOperatingIncome = fundamentals.operating_income_loss.slice(0, 4).reduce((sum, record) => sum + record.value, 0);
const previousFourQuartersOperatingIncome = fundamentals.operating_income_loss.slice(4, 8).reduce((sum, record) => sum + record.value, 0);
const operatingIncomeYoYChange = previousFourQuartersOperatingIncome ? ((trailingFourQuartersOperatingIncome - previousFourQuartersOperatingIncome) / previousFourQuartersOperatingIncome * 100).toFixed(1) : '—';
const operatingIncomeBaseValue = trailingFourQuartersOperatingIncome !== undefined ? `$${formatLargeNumber(trailingFourQuartersOperatingIncome, 1)}` : '—';
const operatingIncomeChangeValue = operatingIncomeYoYChange !== '—' ? `${operatingIncomeYoYChange}% YoY` : '';

const trailingFourQuartersNetIncome = fundamentals.net_income.slice(0, 4).reduce((sum, record) => sum + record.value, 0);
const previousFourQuartersNetIncome = fundamentals.net_income.slice(4, 8).reduce((sum, record) => sum + record.value, 0);
const netIncomeYoYChange = previousFourQuartersNetIncome ? ((trailingFourQuartersNetIncome - previousFourQuartersNetIncome) / previousFourQuartersNetIncome * 100).toFixed(1) : '—';
const netIncomeBaseValue = trailingFourQuartersNetIncome !== undefined ? `$${formatLargeNumber(trailingFourQuartersNetIncome, 1)}` : '—';
const netIncomeChangeValue = netIncomeYoYChange !== '—' ? `${netIncomeYoYChange}% YoY` : '';

// Balance Sheet (QoQ)
const latestQuarterDebtRatio = fundamentals.debt_ratio[0]?.value || 0;
const previousQuarterDebtRatio = fundamentals.debt_ratio[1]?.value || 0;
const debtRatioQoQChange = previousQuarterDebtRatio ? ((latestQuarterDebtRatio - previousQuarterDebtRatio) / previousQuarterDebtRatio * 100).toFixed(1) : '—';
const debtRatioBaseValue = latestQuarterDebtRatio ? formatRatio(latestQuarterDebtRatio) : '—';
const debtRatioChangeValue = debtRatioQoQChange !== '—' ? `${debtRatioQoQChange}% QoQ` : '';

const latestQuarterCurrentRatio = fundamentals.current_ratio[0]?.value || 0;
const previousQuarterCurrentRatio = fundamentals.current_ratio[1]?.value || 0;
const currentRatioQoQChange = previousQuarterCurrentRatio ? ((latestQuarterCurrentRatio - previousQuarterCurrentRatio) / previousQuarterCurrentRatio * 100).toFixed(1) : '—';
const currentRatioBaseValue = latestQuarterCurrentRatio ? formatRatio(latestQuarterCurrentRatio) : '—';
const currentRatioChangeValue = currentRatioQoQChange !== '—' ? `${currentRatioQoQChange}% QoQ` : '';

const latestQuarterCash = fundamentals.cash_cash_equivalents[0]?.value || 0;
const previousQuarterCash = fundamentals.cash_cash_equivalents[1]?.value || 0;
const cashQoQChange = previousQuarterCash ? ((latestQuarterCash - previousQuarterCash) / previousQuarterCash * 100).toFixed(1) : '—';
const cashBaseValue = `$${formatLargeNumber(latestQuarterCash, 1)}`;
const cashChangeValue = cashQoQChange !== '—' ? `${cashQoQChange}% QoQ` : '';

const latestQuarterLongTermDebt = fundamentals.long_term_debt[0]?.value || 0;
const previousQuarterLongTermDebt = fundamentals.long_term_debt[1]?.value || 0;
const longTermDebtQoQChange = previousQuarterLongTermDebt ? ((latestQuarterLongTermDebt - previousQuarterLongTermDebt) / previousQuarterLongTermDebt * 100).toFixed(1) : '—';
const longTermDebtBaseValue = `$${formatLargeNumber(latestQuarterLongTermDebt, 1)}`;
const longTermDebtChangeValue = longTermDebtQoQChange !== '—' ? `${longTermDebtQoQChange}% QoQ` : '';

// Cash Flow (YoY on TTM)
const trailingFourQuartersOperatingActivities = fundamentals.dividends_paid.slice(0, 4).reduce((sum, record) => sum + record.value, 0);
const previousFourQuartersOperatingActivities = fundamentals.dividends_paid.slice(4, 8).reduce((sum, record) => sum + record.value, 0);
const operatingActivitiesYoYChange = previousFourQuartersOperatingActivities ? ((trailingFourQuartersOperatingActivities - previousFourQuartersOperatingActivities) / previousFourQuartersOperatingActivities * 100).toFixed(1) : '—';
const operatingActivitiesBaseValue = trailingFourQuartersOperatingActivities !== undefined ? `$${formatLargeNumber(trailingFourQuartersOperatingActivities, 1)}` : '—';
const operatingActivitiesChangeValue = operatingActivitiesYoYChange !== '—' ? `${operatingActivitiesYoYChange}% YoY` : '';

const trailingFourQuartersEquityRepurchase = fundamentals.cash_from_repurchase_equity.slice(0, 4).reduce((sum, record) => sum + record.value, 0);
const previousFourQuartersEquityRepurchase = fundamentals.cash_from_repurchase_equity.slice(4, 8).reduce((sum, record) => sum + record.value, 0);
const equityRepurchaseYoYChange = previousFourQuartersEquityRepurchase ? ((trailingFourQuartersEquityRepurchase - previousFourQuartersEquityRepurchase) / previousFourQuartersEquityRepurchase * 100).toFixed(1) : '—';
const equityRepurchaseBaseValue = trailingFourQuartersEquityRepurchase !== undefined ? `$${formatLargeNumber(trailingFourQuartersEquityRepurchase, 1)}` : '—';
const equityRepurchaseChangeValue = equityRepurchaseYoYChange !== '—' ? `${equityRepurchaseYoYChange}% YoY` : '';

// Free Cash Flow (YoY on TTM)
const trailingFourQuartersFCF = fundamentals.free_cash_flow.slice(0, 4).reduce((sum, record) => sum + record.value, 0);
const previousFourQuartersFCF = fundamentals.free_cash_flow.slice(4, 8).reduce((sum, record) => sum + record.value, 0);
const fcfYoYChange = previousFourQuartersFCF ? ((trailingFourQuartersFCF - previousFourQuartersFCF) / previousFourQuartersFCF * 100).toFixed(1) : '—';
const fcfBaseValue = trailingFourQuartersFCF !== undefined ? `$${formatLargeNumber(trailingFourQuartersFCF, 1)}` : '—';
const fcfChangeValue = fcfYoYChange !== '—' ? `${fcfYoYChange}% YoY` : '';

const headCell = text => ({ text: `${text}`, fontWeight: 'bold', color: 'var(--text-color)', padding: '1px 5px' });
const valueCell = text => ({ text: `${text}`, color: 'var(--text-color)', padding: '3px 7px' });
const leftTitleCell = text => ({ text: `${text}`, fontWeight: 'bold', color: 'var(--text-color)', padding: '1px 7px', width: '45%' });
const valueCellStyle = (text, color = 'var(--text-color)') => ({ text: `${text}`, color, textAlign: 'right', padding: '1px 5px', width: '15%' });
const changeCellStyle = (text, color) => ({ text: `${text}`, color: color || 'var(--text-color)', fontSize: 10, textAlign: 'right', padding: '1px 5px', width: '40%' });

const SEPARATOR = { cells: [{ text: "", colspan: 3, borderBottom: '1px solid var(--border-color)' }] };

const marketCap = `$${formatLargeNumber(currentFundamental('market_cap'))}`;
const enterpriseValue = `$${formatLargeNumber(currentFundamental('enterprise_value'))}`;

// Add definitions for psRatio, peRatio, and pbRatio
const psRatio = currentFundamental('ps_ratio_ttm') ? formatRatio(currentFundamental('ps_ratio_ttm')) : '—';
const peRatio = currentFundamental('pe_ratio_ttm') ? formatRatio(currentFundamental('pe_ratio_ttm')) : '—';
const pbRatio = currentFundamental('price_to_book_value') ? formatRatio(currentFundamental('price_to_book_value')) : '—';

const nextEarnings = earnings.find(record => record.isFuture);
const DAYS_IN_SECONDS = 24 * 60 * 60;
const daysUntilNextEarnings = Math.floor((nextEarnings.timestamp - time[time.length - 1]) / DAYS_IN_SECONDS);

// Define titleValueRow with values matching indicator text style
const titleValueRow = (title, value) => ({
    cells: [leftTitleCell(title), { text: '', width: '25%' }, valueCellStyle(value)]
});

paint_overlay('Table', { position: 'bottom_right', offset_x: -65, offset_y: -175, order: 'above_all' }, {
    fontSize: fontSize,
    border: '0px solid var(--border-color)',
    background: `rgba(${parseInt(backgroundColor.slice(1, 3), 16)}, ${parseInt(backgroundColor.slice(3, 5), 16)}, ${parseInt(backgroundColor.slice(5, 7), 16)}, ${backgroundOpacity})`,
    width: '250px',
    rows: [{
        cells: [{ colspan: 3, text: `${current.ticker}`, color: 'var(--text-color)', padding: '3px 7px' }]
    }, {
        cells: [{
            colspan: 3,
            table: {
                width: '100%',
                rows: [
                    { cells: [{ ...valueCell(`Next earnings: ${moment(nextEarnings.timestamp * 1e3).format('DD-MM-YYYY')} (in ${daysUntilNextEarnings} days)`), colspan: 3 }] },
                    SEPARATOR,
                    titleValueRow("Mkt Cap", marketCap),
                    titleValueRow("EV", enterpriseValue),
                    titleValueRow("P/S Ratio", psRatio),
                    titleValueRow("P/E Ratio", peRatio),
                    titleValueRow("P/B Ratio", pbRatio),
                    SEPARATOR,
                    { cells: [{ text: "Income Statement:", fontSize: 13, fontWeight: 'bold', color: 'var(--text-color)', padding: '2px 7px', colspan: 3 }] },
                    { cells: [{ text: "", padding: '2px', colspan: 3 }] },
                    { cells: [leftTitleCell("Revenue"), valueCellStyle(revenueBaseValue), changeCellStyle(revenueChangeValue, revenueYoYChange > 0 ? beatTextColor : missTextColor)] },
                    { cells: [leftTitleCell("Gross Margin"), valueCellStyle(grossMarginBaseValue), changeCellStyle(grossMarginChangeValue, grossMarginYoYChange > 0 ? beatTextColor : missTextColor)] },
                    { cells: [leftTitleCell("Op. Income"), valueCellStyle(operatingIncomeBaseValue), changeCellStyle(operatingIncomeChangeValue, operatingIncomeYoYChange > 0 ? beatTextColor : missTextColor)] },
                    { cells: [leftTitleCell("Net Income"), valueCellStyle(netIncomeBaseValue), changeCellStyle(netIncomeChangeValue, netIncomeYoYChange > 0 ? beatTextColor : missTextColor)] },
                    SEPARATOR,
                    { cells: [{ text: "Balance Sheet:", fontSize: 13, fontWeight: 'bold', color: 'var(--text-color)', padding: '2px 7px', colspan: 3 }] },
                    { cells: [{ text: "", padding: '2px', colspan: 3 }] },
                    { cells: [leftTitleCell("Cash"), valueCellStyle(cashBaseValue), changeCellStyle(cashChangeValue, cashQoQChange > 0 ? beatTextColor : missTextColor)] },
                    { cells: [leftTitleCell("LT Debt"), valueCellStyle(longTermDebtBaseValue), changeCellStyle(longTermDebtChangeValue, longTermDebtQoQChange > 0 ? beatTextColor : missTextColor)] },
                    { cells: [leftTitleCell("Debt Ratio"), valueCellStyle(debtRatioBaseValue), changeCellStyle(debtRatioChangeValue, debtRatioQoQChange > 0 ? beatTextColor : missTextColor)] },
                    { cells: [leftTitleCell("Current Ratio"), valueCellStyle(currentRatioBaseValue), changeCellStyle(currentRatioChangeValue, currentRatioQoQChange > 0 ? beatTextColor : missTextColor)] },
                    SEPARATOR,
                    { cells: [{ text: "Cash Flow Statement:", fontSize: 13, fontWeight: 'bold', color: 'var(--text-color)', padding: '1px 7px', colspan: 3 }] },
                    { cells: [{ text: "", padding: '2px', colspan: 3 }] },
                    { cells: [leftTitleCell("FCF"), valueCellStyle(fcfBaseValue), changeCellStyle(fcfChangeValue, fcfYoYChange > 0 ? beatTextColor : missTextColor)] },
                    { cells: [leftTitleCell("Dividends Paid"), valueCellStyle(operatingActivitiesBaseValue), changeCellStyle(operatingActivitiesChangeValue, operatingActivitiesYoYChange > 0 ? beatTextColor : missTextColor)] },
                    { cells: [leftTitleCell("Buybacks"), valueCellStyle(equityRepurchaseBaseValue), changeCellStyle(equityRepurchaseChangeValue, equityRepurchaseYoYChange > 0 ? beatTextColor : missTextColor)] },
                    SEPARATOR
                ]
            }
        }]
    }]
});</code>
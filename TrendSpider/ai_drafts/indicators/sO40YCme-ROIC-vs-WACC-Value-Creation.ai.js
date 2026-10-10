describe_indicator('ROIC vs WACC (Value Creation)', 'lower', { decimals: 2 });

// ============================================================================
// INPUTS
// ============================================================================
const mainTab = input.tab('General Settings');
const myPeriod = mainTab.select('Financial Period', 'FY', ['FY', 'FQ', 'TTM']);
const myMode = mainTab.select('WACC Mode', 'Estimated', ['Estimated', 'Manual']);
const myManualWacc = mainTab.number('Manual WACC (%)', 8.0, { min: 0, max: 100, step: 0.5 });

const waccTab = input.tab('Estimated WACC Parameters (CAPM)');
const myRfTicker = waccTab.symbol('Risk-Free Rate Ticker', 'US10Y');
const myBenchTicker = waccTab.symbol('Market Benchmark', 'SPY');
const myErp = waccTab.number('Equity Risk Premium (%)', 5.5, { min: 0, max: 100, step: 0.1 });
const myBetaLen = waccTab.number('Beta Lookback (Bars)', 252, { min: 5, max: 1000 });

const taxTab = input.tab('Tax Assumption');
// NOTE: "income_tax" is not a valid metric id in request.fundamental() and
// caused an "unknown_metric" error. There is no documented metric id for
// income tax expense available in this API, so instead of fetching it we
// let the user set an assumed flat effective tax rate used for NOPAT and
// cost-of-debt tax shield calculations. This is an approximation.
const myAssumedTaxRatePct = taxTab.number('Assumed Effective Tax Rate (%)', 21, { min: 0, max: 60, step: 0.5 });

// ============================================================================
// FUNDAMENTAL DATA
// NOTE: TrendSpider's request.fundamental() has no "roic" metric id, and the
// previously used "income_tax" metric id was invalid ("unknown_metric"
// error). It has been removed; a user-configurable flat tax rate assumption
// is used instead (see "Tax Assumption" tab).
// ROIC is approximated here as:
//   NOPAT / Invested Capital
// where NOPAT ~= Net Income + Interest Expense * (1 - Assumed Tax Rate)
// and Invested Capital ~= Total Debt + Market Cap (used as an equity proxy,
// since book equity is not available among the metrics used here).
// This is an approximation and may not match a "textbook" ROIC figure.
// ============================================================================
const myQuarters = myPeriod === 'FQ' ? 8 : 20;

const myFundamentalData = await request.fundamental(current.ticker, [
	'total_debt',
	'interest_expense',
	'net_income',
	'total_shares_outstanding'
], myQuarters);
assert(!myFundamentalData.error, `Error fetching fundamentals: "${myFundamentalData.error}"`);

function myLandFundamental(myRecords) {
	if (!myRecords || myRecords.length === 0) {
		return series_of(0);
	}
	// records come most-recent-first; reverse to ascending for landing
	const myAsc = myRecords.slice().reverse();
	const myTimes = myAsc.map(_r => _r.reportdate);
	const myValues = myAsc.map(_r => _r.value);
	const myLanded = land_points_onto_series(myTimes, myValues, time, 'ge');
	return interpolate_sparse_series(myLanded, 'constant');
}

const myTotDebtRaw = myLandFundamental(myFundamentalData.total_debt);
const myIntExpRaw = myLandFundamental(myFundamentalData.interest_expense);
const myNetIncRaw = myLandFundamental(myFundamentalData.net_income);
const mySharesRaw = myLandFundamental(myFundamentalData.total_shares_outstanding);

// ============================================================================
// RISK FREE RATE & BENCHMARK DATA (FOR CAPM)
// NOTE: assuming the risk-free "ticker" (e.g. US10Y) returns a yield value in
// its close series.
// ============================================================================
const [myRfHistory, myBenchHistory] = await Promise.all([
	request.history(myRfTicker, current.resolution),
	request.history(myBenchTicker, current.resolution)
]);
assert(!myRfHistory.error, `Error fetching risk-free data: "${myRfHistory.error}"`);
assert(!myBenchHistory.error, `Error fetching benchmark data: "${myBenchHistory.error}"`);

const myRfLanded = land_points_onto_series(myRfHistory.time, myRfHistory.close, time, 'le');
const myRfRate = interpolate_sparse_series(myRfLanded, 'constant');

const myBenchReturnRaw = div(sub(myBenchHistory.close, shift(myBenchHistory.close, 1)), shift(myBenchHistory.close, 1));
const myBenchReturnLanded = land_points_onto_series(myBenchHistory.time, myBenchReturnRaw, time, 'le');
const myBenchReturn = interpolate_sparse_series(myBenchReturnLanded, 'constant');

const mySymReturn = div(sub(close, shift(close, 1)), shift(close, 1));

// ============================================================================
// BETA CALCULATION
// ============================================================================
const myCorr = correlation(mySymReturn, myBenchReturn, myBetaLen);
const myStdevSym = stdev(mySymReturn, myBetaLen);
const myStdevBench = stdev(myBenchReturn, myBetaLen);

const myBeta = for_every(myStdevBench, myStdevSym, myCorr, (_sb, _ss, _c) => {
	if (_sb > 0 && _c !== null && !isNaN(_c)) {
		return _c * (_ss / _sb);
	}
	return 1.0;
});

const myKe = add(myRfRate, mult(myBeta, myErp));

// ============================================================================
// COST OF DEBT & TAX RATE
// ============================================================================
const myIntExp = for_every(myIntExpRaw, _v => Math.abs(_v || 0));
const myTotDebt = for_every(myTotDebtRaw, _v => Math.max(_v || 0, 0));
const myKd = for_every(myIntExp, myTotDebt, (_ie, _td) => _td > 0 ? (_ie / _td) * 100 : 0.0);

const myNetInc = for_every(myNetIncRaw, _v => _v || 0);
// Flat assumed tax rate (user configurable), since there is no valid
// income tax expense metric id available in request.fundamental().
const myTaxRate = series_of(myAssumedTaxRatePct / 100);

// ============================================================================
// CAPITAL WEIGHTS & WACC
// ============================================================================
const mySharesOut = for_every(mySharesRaw, _v => _v || 0);
const myMarketCap = mult(mySharesOut, close);
const myV = add(myMarketCap, myTotDebt);
const myWe = for_every(myV, myMarketCap, (_v, _mc) => _v > 0 ? (_mc / _v) : 1.0);
const myWd = for_every(myV, myTotDebt, (_v, _td) => _v > 0 ? (_td / _v) : 0.0);

const myEstWacc = for_every(myWe, myKe, myWd, myKd, myTaxRate, (_we, _ke, _wd, _kd, _tr) => (_we * _ke) + (_wd * _kd * (1 - _tr)));
const myWacc = myMode === 'Estimated' ? myEstWacc : series_of(myManualWacc);

// ============================================================================
// APPROXIMATED ROIC
// NOPAT = Net Income + Interest Expense * (1 - Assumed Tax Rate)
// Invested Capital = Total Debt + Market Cap (equity proxy)
// ROIC% = NOPAT / Invested Capital * 100
// ============================================================================
const myNopat = for_every(myNetInc, myIntExp, myTaxRate, (_ni, _ie, _tr) => _ni + (_ie * (1 - _tr)));
const myInvestedCapital = add(myTotDebt, myMarketCap);
const myRoic = for_every(myNopat, myInvestedCapital, (_nopat, _ic) => _ic > 0 ? (_nopat / _ic) * 100 : 0);

// ============================================================================
// SPREAD & SIGNALS
// ============================================================================
const mySpread = sub(myRoic, myWacc);
const myIsCreatingValue = for_every(mySpread, _s => _s > 0);
const mySpreadColor = for_every(mySpread, _s => _s > 0 ? '#00897B' : '#E53935');

paint(mySpread, { name: 'Economic Spread', style: 'column', color: mySpreadColor });
paint(myRoic, { name: 'ROIC', color: '#2962FF', thickness: 2 });
paint(myWacc, { name: 'WACC', color: '#FF9800', thickness: 2 });
paint(horizontal_line(0), { name: 'Zero Line', color: 'gray', style: 'dotted' });

register_signal(myIsCreatingValue, 'ROIC Greater Than WACC (Value Creation)');
register_signal(for_every(mySpread, _s => _s <= 0), 'WACC Greater Than Or Equal ROIC (Value Destruction)');
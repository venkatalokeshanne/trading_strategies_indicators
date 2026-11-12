<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('ALMA Channels with Signals');

// Input parameters
// The input names have been shortened to comply with the system's length restrictions
const scl_t = input.number('Short Length', 14, { min: 1, max: 500 });
const mcl_t = input.number('Medium Length', 30, { min: 1, max: 500 });
const lcl_t = input.number('Long Length', 60, { min: 1, max: 500 });
const scm = input.number('Short Multiplier', 2.0, { min: 0.1, max: 10 });
const mcm = input.number('Medium Multiplier', 4.0, { min: 0.1, max: 10 });
const lcm = input.number('Long Multiplier', 8.0, { min: 0.1, max: 10 });

// Allows the user to select which price series to use as the source for calculations
const priceSource = input.select('Source', 'close', constants.price_source_options);

const src = market[priceSource];

// Calculate half lengths for offset positioning
const scl = Math.floor(scl_t / 2);
const mcl = Math.floor(mcl_t / 2);
const lcl = Math.floor(lcl_t / 2);

// Calculate ALMA for each cycle
const ma_scl = alma(src, scl, 0.85, 6);
const ma_mcl = alma(src, mcl, 0.85, 6);
const ma_lcl = alma(src, lcl, 0.85, 6);

// Calculate ATR offsets
// The mult() function requires the first argument to be a series, so we swap the order
const scm_off = mult(atr(high, low, close, scl), scm);
const mcm_off = mult(atr(high, low, close, mcl), mcm);
const lcm_off = mult(atr(high, low, close, lcl), lcm);

// Calculate band positions
const scl_2 = Math.floor(scl / 2);
const mcl_2 = Math.floor(mcl / 2);
const lcl_2 = Math.floor(lcl / 2);

// Shift ALMA and calculate bands
const ma_scl_shifted = shift(ma_scl, scl_2);
const ma_mcl_shifted = shift(ma_mcl, mcl_2);
const ma_lcl_shifted = shift(ma_lcl, lcl_2);

// Short cycle bands
const sct = add(ma_scl_shifted, scm_off);
const scb = sub(ma_scl_shifted, scm_off);

// Medium cycle bands
const mct = add(ma_mcl_shifted, mcm_off);
const mcb = sub(ma_mcl_shifted, mcm_off);

// Long cycle bands
const lct = add(ma_lcl_shifted, lcm_off);
const lcb = sub(ma_lcl_shifted, lcm_off);

// Paint the bands
const sct_line = paint(sct, { color: '#306e43', name: 'ShortCycleBandTop' });
const scb_line = paint(scb, { color: '#306e43', name: 'ShortCycleBandBottom' });
paint(for_every(sct, scb, (t, b) => (t + b) / 2), { color: 'green', name: 'ShortCycleMedian', style: 'line' });

const mct_line = paint(mct, { color: '#3e56a7', name: 'MediumCycleBandTop' });
const mcb_line = paint(mcb, { color: '#3e56a7', name: 'MediumCycleBandBottom' });
paint(for_every(mct, mcb, (t, b) => (t + b) / 2), { color: 'blue', name: 'MediumCycleMedian', style: 'line' });

const lct_line = paint(lct, { color: '#940e0e', name: 'LongCycleBandTop' });
const lcb_line = paint(lcb, { color: '#940e0e', name: 'LongCycleBandBottom' });
paint(for_every(lct, lcb, (t, b) => (t + b) / 2), { color: 'red', name: 'LongCycleMedian', style: 'line' });

// Fill between bands
fill(sct_line, scb_line, 'green', 0.1);
fill(mct_line, mcb_line, 'blue', 0.1);
fill(lct_line, lcb_line, 'red', 0.1);

// Calculate signal conditions
const shortTriangleBottom = for_every(low, scb, mcb, lcb, (_low, _scb, _mcb, _lcb) => 
    _low < _scb && _low < _mcb && _low > _lcb && _scb > _mcb ? _low : null);

const mediumTriangleBottom = for_every(low, scb, mcb, lcb, (_low, _scb, _mcb, _lcb) => 
    _low < _scb && _low < _mcb && _low > _lcb && _scb < _mcb ? _low : null);

const longTriangleBottom = for_every(low, lcb, scb, mcb, (_low, _lcb, _scb, _mcb) => 
    _low < _lcb && _low < _scb && _low < _mcb ? _low : null);

const shortTriangleTop = for_every(high, sct, mct, lct, (_high, _sct, _mct, _lct) => 
    _high > _sct && _high > _mct && _high < _lct && _sct < _mct ? _high : null);

const mediumTriangleTop = for_every(high, sct, mct, lct, (_high, _sct, _mct, _lct) => 
    _high > _sct && _high > _mct && _high < _lct && _sct > _mct ? _high : null);

const longTriangleTop = for_every(high, lct, sct, mct, (_high, _lct, _sct, _mct) => 
    _high > _lct && _high > _sct && _high > _mct ? _high : null);

// Convert signals to arrow icons
const shortArrowBottom = shortTriangleBottom.map(value => value !== null ? constants.icons.arrow_up : null);
const mediumArrowBottom = mediumTriangleBottom.map(value => value !== null ? constants.icons.arrow_up : null);
const longArrowBottom = longTriangleBottom.map(value => value !== null ? constants.icons.arrow_up : null);

const shortArrowTop = shortTriangleTop.map(value => value !== null ? constants.icons.arrow_down : null);
const mediumArrowTop = mediumTriangleTop.map(value => value !== null ? constants.icons.arrow_down : null);
const longArrowTop = longTriangleTop.map(value => value !== null ? constants.icons.arrow_down : null);

// Paint signals as arrows
paint(shortArrowBottom, { style: 'labels_below', color: 'green', name: 'Short Triangle Bottom',fontSize: 20 });
paint(mediumArrowBottom, { style: 'labels_below', color: 'green', name: 'Medium Triangle Bottom',fontSize: 20 });
paint(longArrowBottom, { style: 'labels_below', color: 'green', name: 'Long Triangle Bottom',fontSize: 20 });

paint(shortArrowTop, { style: 'labels_above', color: 'red', name: 'Short Triangle Top',fontSize: 20 });
paint(mediumArrowTop, { style: 'labels_above', color: 'red', name: 'Medium Triangle Top',fontSize: 20 });
paint(longArrowTop, { style: 'labels_above', color: 'red', name: 'Long Triangle Top',fontSize: 20 });
</code>
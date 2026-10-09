describe_indicator('SMA 50 100 150 200 SSMA 360', 'price');

// Visibility toggles for each line
const myTab = input.tab('Lines');

const myShow50 = myTab.boolean('Show SMA 50', true);
const myShow100 = myTab.boolean('Show SMA 100', true);
const myShow150 = myTab.boolean('Show SMA 150', true);
const myShow200 = myTab.boolean('Show SMA 200', true);
const myShow360 = myTab.boolean('Show SSMA 360', true);

const mySma50 = sma(close, 50);
const mySma100 = sma(close, 100);
const mySma150 = sma(close, 150);
const mySma200 = sma(close, 200);

// Smoothed SMA 360: SMA of SMA, exactly as the Pine script does
const mySsma360 = sma(sma(close, 360), 360);

paint(myShow50 ? mySma50 : constants.empty_series, { name: 'SMA50', color: 'blue', thickness: 1 });
paint(myShow100 ? mySma100 : constants.empty_series, { name: 'SMA100', color: 'orange', thickness: 2 });
paint(myShow150 ? mySma150 : constants.empty_series, { name: 'SMA150', color: 'green', thickness: 3 });
paint(myShow200 ? mySma200 : constants.empty_series, { name: 'SMA200', color: 'red', thickness: 4 });
paint(myShow360 ? mySsma360 : constants.empty_series, { name: 'SSMA360', color: 'purple', thickness: 5 });

// Scanning and strategy signals: price crossing above/below each moving average
const myCrossAbove50 = for_every(close, open, mySma50, (_c, _o, _m) => _c > _m && _o <= _m);
const myCrossBelow50 = for_every(close, open, mySma50, (_c, _o, _m) => _c < _m && _o >= _m);
register_signal(myCrossAbove50, 'Cross Above SMA50');
register_signal(myCrossBelow50, 'Cross Below SMA50');

const myCrossAbove100 = for_every(close, open, mySma100, (_c, _o, _m) => _c > _m && _o <= _m);
const myCrossBelow100 = for_every(close, open, mySma100, (_c, _o, _m) => _c < _m && _o >= _m);
register_signal(myCrossAbove100, 'Cross Above SMA100');
register_signal(myCrossBelow100, 'Cross Below SMA100');

const myCrossAbove150 = for_every(close, open, mySma150, (_c, _o, _m) => _c > _m && _o <= _m);
const myCrossBelow150 = for_every(close, open, mySma150, (_c, _o, _m) => _c < _m && _o >= _m);
register_signal(myCrossAbove150, 'Cross Above SMA150');
register_signal(myCrossBelow150, 'Cross Below SMA150');

const myCrossAbove200 = for_every(close, open, mySma200, (_c, _o, _m) => _c > _m && _o <= _m);
const myCrossBelow200 = for_every(close, open, mySma200, (_c, _o, _m) => _c < _m && _o >= _m);
register_signal(myCrossAbove200, 'Cross Above SMA200');
register_signal(myCrossBelow200, 'Cross Below SMA200');

const myCrossAbove360 = for_every(close, open, mySsma360, (_c, _o, _m) => _c > _m && _o <= _m);
const myCrossBelow360 = for_every(close, open, mySsma360, (_c, _o, _m) => _c < _m && _o >= _m);
register_signal(myCrossAbove360, 'Cross Above SSMA360');
register_signal(myCrossBelow360, 'Cross Below SSMA360');
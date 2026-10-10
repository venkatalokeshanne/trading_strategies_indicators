describe_indicator('VizorDesk Masa Pusulasi - Akis Emilim Rejim', 'lower');

// ─── Inputs ───
const mainTab = input.tab('Ayarlar');
const lenAvg = mainTab.number('Ortalama Pencere (hacim/ATR)', 20, { min: 5, max: 200 });
const lenFlow = mainTab.number('Akis Yumusatma', 8, { min: 1, max: 100 });
const row1 = mainTab.row();
const myAbsVolMult = row1.number('Emilim - Hacim esigi (x ort)', 1.6, { min: 1.0, max: 10, step: 0.1 });
const myAbsRngMult = row1.number('Emilim - Menzil esigi (x ATR)', 0.7, { min: 0.1, max: 5, step: 0.1 });
const mySweepLook = mainTab.number('Sweep Lookback', 20, { min: 5, max: 200 });

const togglesTab = input.tab('Gosterim');
const myShowAbsorb = togglesTab.boolean('Emilim isaretleri', true);
const myShowSweep = togglesTab.boolean('Sweep isaretleri', true);
const myShowHUD = togglesTab.boolean('HUD paneli', true);
const myHudPos = togglesTab.select('HUD Konumu', 'bottom_right', ['top_right', 'bottom_right', 'top_left', 'bottom_left']);

// ─── Akis: proxy bar-delta ───
const myRng = sub(high, low);
const myBuyVol = for_every(myRng, volume, close, low, (_r, _v, _c, _l) => _r > 0 ? _v * (_c - _l) / _r : _v * 0.5);
const mySellVol = for_every(myRng, volume, high, close, (_r, _v, _h, _c) => _r > 0 ? _v * (_h - _c) / _r : _v * 0.5);
const myDelta = sub(myBuyVol, mySellVol);
const myVolAvg = sma(volume, lenAvg);
const myDeltaN = for_every(myVolAvg, myDelta, (_va, _d) => _va > 0 ? 100.0 * _d / _va : 0.0);
const myFlow = ema(myDeltaN, lenFlow);

// ─── Rejim: oynaklik sikisma / genisleme ───
const myAtrVal = atr(high, low, close, lenAvg);
const myAtrBase = sma(myAtrVal, lenAvg * 3);
const myRegime = for_every(myAtrBase, myAtrVal, (_base, _atr) => _base > 0 ? _atr / _base : 1.0);
const myIsExp = for_every(myRegime, _r => _r > 1.10);
const myIsComp = for_every(myRegime, _r => _r < 0.90);

// ─── Emilim: yuksek hacim + kucuk menzil + guclu tek-yon akis ───
const myVolHot = for_every(volume, myVolAvg, (_v, _va) => _v > myAbsVolMult * _va);
const myRngSmall = for_every(myRng, myAtrVal, (_r, _atr) => _r < myAbsRngMult * _atr);
const myStrong = for_every(myDeltaN, _d => Math.abs(_d) > 40.0);
const myAbsorb = for_every(myVolHot, myRngSmall, myStrong, (_vh, _rs, _st) => myShowAbsorb && _vh && _rs && _st);
const myAbsorbBuySide = for_every(myAbsorb, myDelta, (_a, _d) => _a && _d > 0);
const myAbsorbSellSide = for_every(myAbsorb, myDelta, (_a, _d) => _a && _d < 0);

// ─── Sweep: likidite supurme ───
// Pine's [1] offset means "previous bar's" highest/lowest; we shift forward by 1
const myHHPrev = shift(highest(high, mySweepLook), 1);
const myLLPrev = shift(lowest(low, mySweepLook), 1);
const mySweepUp = for_every(high, close, myHHPrev, (_h, _c, _hh) => myShowSweep && _hh !== null && _h > _hh && _c < _hh);
const mySweepDn = for_every(low, close, myLLPrev, (_l, _c, _ll) => myShowSweep && _ll !== null && _l < _ll && _c > _ll);

// ─── Paint main oscillator ───
const myDeltaColor = for_every(myDeltaN, _d => _d >= 0 ? '#00FF66' : '#FF3355');
paint(myDeltaN, { name: 'Akis Delta', style: 'column', color: myDeltaColor });
paint(myFlow, { name: 'Akis Yumusak', style: 'line', color: '#7DD3FC', thickness: 2 });
paint(horizontal_line(0), { name: 'Sifir', color: 'gray', style: 'dotted' });

// ─── Absorb / Sweep markers ───
const myAbsorbBuyMarks = for_every(myAbsorbBuySide, myDeltaN, (_a, _d) => _a ? _d : null);
const myAbsorbSellMarks = for_every(myAbsorbSellSide, myDeltaN, (_a, _d) => _a ? _d : null);
const mySweepUpMarks = for_every(mySweepUp, myDeltaN, (_s, _d) => _s ? _d : null);
const mySweepDnMarks = for_every(mySweepDn, myDeltaN, (_s, _d) => _s ? _d : null);

paint(myAbsorbBuyMarks, { name: 'Emilim Alim', style: 'labels_above', color: '#FFB020' });
paint(myAbsorbSellMarks, { name: 'Emilim Satim', style: 'labels_below', color: '#FFB020' });
paint(mySweepUpMarks, { name: 'Sweep Ust', style: 'labels_above', color: '#FF3355' });
paint(mySweepDnMarks, { name: 'Sweep Alt', style: 'labels_below', color: '#00FF66' });

// ─── HUD overlay ───
const myLastIndex = close.length - 1;
const myFlowLast = myFlow[myLastIndex];
const myRegimeLast = myRegime[myLastIndex];
const myVolAvgLast = myVolAvg[myLastIndex];
const myVolumeLast = volume[myLastIndex];
const myAbsorbBuyLast = myAbsorbBuySide[myLastIndex];
const myAbsorbSellLast = myAbsorbSellSide[myLastIndex];
const myAbsorbLast = myAbsorb[myLastIndex];
const myIsExpLast = myIsExp[myLastIndex];
const myIsCompLast = myIsComp[myLastIndex];

const myFlowRounded = Math.round(myFlowLast);
const myFlowStr = (myFlowRounded >= 0 ? '+' : '') + String(myFlowRounded);
const myKatRatio = myVolAvgLast > 0 ? myVolumeLast / myVolAvgLast : 0.0;
const myKatStr = myKatRatio.toFixed(1) + 'x';
const myRejStr = myRegimeLast.toFixed(2) + 'x';

const myAkisTxt = myFlowLast > 20 ? 'ALICI' : myFlowLast < -20 ? 'SATICI' : 'DENGE';
const myKatTxt = myVolumeLast > 1.2 * myVolAvgLast ? 'GERCEK' : 'DUSUK';
const myEmilTxt = myAbsorbBuyLast ? 'ALIM emiliyor' : myAbsorbSellLast ? 'SATIM emiliyor' : 'yok';
const myRejTxt = myIsExpLast ? 'GENISLEME' : myIsCompLast ? 'SIKISMA' : 'NORMAL';

const myAkisVal = myFlowStr + '  ' + myAkisTxt;
const myKatVal = myKatStr + '  ' + myKatTxt;
const myRejVal = myRejStr + '  ' + myRejTxt;

const myAkisCol = myFlowLast > 20 ? '#00FF66' : myFlowLast < -20 ? '#FF3355' : 'white';
const myKatCol = myVolumeLast > 1.2 * myVolAvgLast ? '#00FF66' : 'gray';
const myEmilCol = myAbsorbLast ? '#FFB020' : 'gray';
const myRejCol = myIsExpLast ? '#A78BFA' : myIsCompLast ? '#7DD3FC' : 'white';

paint_overlay('VizorDeskHUD', { position: myHudPos }, {
	rows: myShowHUD ? [
		{ cells: [{ text: 'VIZORDESK', color: '#00FF66' }, { text: 'Masa Pusulasi', color: 'white' }] },
		{ cells: [{ text: 'AKIS', color: '#8593A2' }, { text: myAkisVal, color: myAkisCol }] },
		{ cells: [{ text: 'KATILIM', color: '#8593A2' }, { text: myKatVal, color: myKatCol }] },
		{ cells: [{ text: 'EMILIM', color: '#8593A2' }, { text: myEmilTxt, color: myEmilCol }] },
		{ cells: [{ text: 'REJIM', color: '#8593A2' }, { text: myRejVal, color: myRejCol }] },
		{ cells: [{ text: 'vizordesk.com', color: 'gray' }, { text: 'sinyal degil, gozlem', color: 'gray' }] }
	] : []
});

// ─── Signals for scanners/alerts/strategies ───
register_signal(myAbsorb, 'Emilim Tespit');
register_signal(myAbsorbBuySide, 'Emilim Alim Tarafi');
register_signal(myAbsorbSellSide, 'Emilim Satim Tarafi');
register_signal(mySweepUp, 'Sweep Ust Likidite');
register_signal(mySweepDn, 'Sweep Alt Likidite');
register_signal(for_every(mySweepUp, mySweepDn, (_u, _d) => _u || _d), 'Likidite Sweep');
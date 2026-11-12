<code x-ref="code" class="hljs" data-clipboard-text>const countries = {
  "Australia": "AUS",
  "Canada": "CAN",
  "China": "CHN",
  "European Union": "EUU",
  "Japan": "JPN",
  "Mexico": "MEX",
  "United Kingdom": "GBR",
  "United States": "USA",
  "World": "WLD"
};
const validIndicatorIds = ["BM.GSR.INSF.ZS","BX.GSR.INSF.ZS","BG.GSR.NFSV.GD.ZS","FS.AST.PRVT.GD.ZS","IC.CUS.DURS.EX","IC.ELC.DURS","IC.ELC.OUTG.ZS","IC.FRM.BNKS.ZS","IC.FRM.BRIB.ZS","IC.FRM.BKWC.ZS","IC.FRM.CMPU.ZS","IC.FRM.CORR.ZS","IC.FRM.DURS","IC.FRM.FEMM.ZS","IC.FRM.FEMO.ZS","IC.FRM.FREG.ZS","IC.FRM.OUTG.ZS","IC.FRM.METG.ZS","IC.GOV.DURS.ZS","IC.FRM.TRNG.ZS","IC.TAX.GIFT.ZS","IC.TAX.METG","LP.IMP.DURS.MD","LP.EXP.DURS.MD","LP.LPI.CUST.XQ","LP.LPI.INFR.XQ","LP.LPI.LOGS.XQ","LP.LPI.ITRN.XQ","LP.LPI.TIME.XQ","ST.INT.ARVL","LP.LPI.TRAC.XQ","LP.LPI.OVRL.XQ","ST.INT.DPRT","ST.INT.TRNX.CD","ST.INT.RCPT.CD","ST.INT.RCPT.XP.ZS","ST.INT.TVLX.CD","ST.INT.XPND.MP.ZS","ST.INT.XPND.CD","ST.INT.TRNR.CD","ST.INT.TVLR.CD","TG.VAL.TOTL.GD.ZS","TM.TAX.MANF.BC.ZS","TM.QTY.MRCH.XD.WD","TM.TAX.MANF.SM.AR.ZS","TM.TAX.MANF.BR.ZS","TM.TAX.MANF.WM.AR.ZS","TM.TAX.MRCH.BC.ZS","TM.TAX.MRCH.BR.ZS","TM.TAX.MANF.WM.FN.ZS","TM.TAX.MRCH.SM.AR.ZS","TM.TAX.MRCH.SM.FN.ZS","TM.TAX.MRCH.WM.AR.ZS","TM.TAX.MRCH.WM.FN.ZS","TM.TAX.MANF.SM.FN.ZS","TM.TAX.TCOM.BC.ZS","TM.TAX.TCOM.BR.ZS","TM.TAX.TCOM.SM.AR.ZS","TM.TAX.TCOM.SM.FN.ZS","TM.TAX.TCOM.WM.AR.ZS","TM.TAX.TCOM.WM.FN.ZS","TM.VAL.FUEL.ZS.UN","TM.UVI.MRCH.XD.WD","TM.VAL.FOOD.ZS.UN","TM.VAL.ICTG.ZS.UN","TM.VAL.AGRI.ZS.UN","TM.VAL.MANF.ZS.UN","TM.VAL.INSF.ZS.WT","TM.VAL.MMTL.ZS.UN","TM.VAL.MRCH.CD.WT","TM.VAL.MRCH.AL.ZS","TM.VAL.MRCH.HI.ZS","TM.VAL.MRCH.R1.ZS","TM.VAL.MRCH.OR.ZS","TM.VAL.MRCH.R3.ZS","TM.VAL.MRCH.R4.ZS","TM.VAL.MRCH.R2.ZS","TM.VAL.MRCH.R6.ZS","TM.VAL.MRCH.R5.ZS","TM.VAL.MRCH.WL.CD","TM.VAL.MRCH.RS.ZS","TM.VAL.OTHR.ZS.WT","TM.VAL.SERV.CD.WT","TM.VAL.TRAN.ZS.WT","TM.VAL.MRCH.XD.WD","TT.PRI.MRCH.XD.WD","TM.VAL.TRVL.ZS.WT","TX.MNF.TECH.ZS.UN","TX.VAL.AGRI.ZS.UN","TX.QTY.MRCH.XD.WD","TX.UVI.MRCH.XD.WD","TX.VAL.FUEL.ZS.UN","TX.VAL.FOOD.ZS.UN","TX.VAL.ICTG.ZS.UN","TX.VAL.MANF.ZS.UN","TX.VAL.MMTL.ZS.UN","TX.VAL.INSF.ZS.WT","TX.VAL.MRCH.HI.ZS","TX.VAL.MRCH.AL.ZS","TX.VAL.MRCH.CD.WT","TX.VAL.MRCH.R1.ZS","TX.VAL.MRCH.OR.ZS","TX.VAL.MRCH.R2.ZS","TX.VAL.MRCH.R4.ZS","TX.VAL.MRCH.R5.ZS","TX.VAL.MRCH.R6.ZS","TX.VAL.MRCH.RS.ZS","TX.VAL.MRCH.WL.CD","TX.VAL.MRCH.XD.WD","TX.VAL.MRCH.R3.ZS","TX.VAL.OTHR.ZS.WT","TX.VAL.TECH.MF.ZS","TX.VAL.SERV.CD.WT","TX.VAL.TECH.CD","TX.VAL.TRAN.ZS.WT","TX.VAL.TRVL.ZS.WT"];
const data = await request.http(`https://api.worldbank.org/v2/topic/12/indicator?per_page=1000&format=json`);
const currentTopicIndicators = data[1].filter(indicator => validIndicatorIds.includes(indicator.id));
const indicatorTitles = currentTopicIndicators.map(indicator => indicator.name);
const currentIndicatorTitle = input.select('Indicator', indicatorTitles[0], indicatorTitles);
const currentIndicator = currentTopicIndicators.find(indicator => indicator.name == currentIndicatorTitle);
const indicatorId = currentIndicator.id;
const indicatorNote = (str => str.length > 80 ? str.slice(0, 80 - 3) + '...' : str)(currentIndicator.sourceNote);
describe_indicator(`World Bank Indicators - Private Sector`, 'lower', { citation: indicatorNote, shortName: `WBI Private Sector` });
const country = input.select('Country', 'United States', Object.keys(countries));
const indicatorData = await request.http(`https://api.worldbank.org/v2/country/${countries[country]}/indicator/${indicatorId}?format=json&per_page=20000`);
assert(indicatorData[1] && indicatorData[1].some(d => d.value !== null && d.value !== ''), `The selected indicator doesn't return any data for "${country}".`);
const indicatorTimestamps = indicatorData[1].map(record => {
  const year = parseInt(record.date);
  const milliseconds = Date.UTC(year, 0, 1);
  return milliseconds / 1000;
}).reverse();
const indicatorValues = indicatorData[1].map(record => +record.value || null).reverse();
const lastIndexWithValue = indicatorValues.reduce((a, v, i) => a = v !== null ? i : a, 0);
const isLastValueOlderThanCandles = indicatorTimestamps[lastIndexWithValue] < time[0];
if (isLastValueOlderThanCandles) {
  indicatorTimestamps.push(time[0]);
  indicatorValues.push(indicatorValues[lastIndexWithValue]);
}
const indicatorLine = interpolate_sparse_series(land_points_onto_series(indicatorTimestamps, interpolate_sparse_series(indicatorValues), time, 'ge'), 'constant');
paint(indicatorLine, 'Line', '#469e48');</code>
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
const validIndicatorIds = ["BM.GSR.GNFS.CD","BM.GSR.CMCP.ZS","BM.GSR.MRCH.CD","BM.GSR.TOTL.CD","BM.GSR.NFSV.CD","BM.GSR.INSF.ZS","BG.GSR.NFSV.GD.ZS","BN.GSR.GNFS.CD","BM.GSR.TRVL.ZS","BM.GSR.TRAN.ZS","BN.GSR.MRCH.CD","BX.GSR.CCIS.CD","BX.GSR.CCIS.ZS","BX.GSR.CMCP.ZS","BX.GSR.GNFS.CD","BX.GSR.NFSV.CD","BX.GSR.INSF.ZS","BX.GSR.TOTL.CD","BX.GSR.MRCH.CD","BX.GSR.TRAN.ZS","BX.GSR.TRVL.ZS","EG.IMP.CONS.ZS","GC.TAX.IMPT.ZS","IC.CUS.DURS.EX","LP.EXP.DURS.MD","LP.LPI.CUST.XQ","LP.LPI.ITRN.XQ","LP.LPI.INFR.XQ","LP.LPI.LOGS.XQ","LP.IMP.DURS.MD","LP.LPI.OVRL.XQ","LP.LPI.TIME.XQ","MS.MIL.MPRT.KD","LP.LPI.TRAC.XQ","NE.EXP.GNFS.CD","NE.EXP.GNFS.KD","MS.MIL.XPRT.KD","NE.EXP.GNFS.KD.ZG","NE.EXP.GNFS.ZS","NE.IMP.GNFS.KD","NE.IMP.GNFS.CD","NE.IMP.GNFS.KD.ZG","NE.RSB.GNFS.ZS","NE.IMP.GNFS.ZS","NE.RSB.GNFS.CD","NE.TRD.GNFS.ZS","ST.INT.ARVL","ST.INT.DPRT","NY.EXP.CAPM.KN","ST.INT.RCPT.CD","ST.INT.TRNR.CD","ST.INT.RCPT.XP.ZS","ST.INT.TRNX.CD","ST.INT.TVLX.CD","ST.INT.XPND.CD","ST.INT.TVLR.CD","ST.INT.XPND.MP.ZS","TG.VAL.TOTL.GD.ZS","TM.TAX.MANF.BC.ZS","TM.QTY.MRCH.XD.WD","TM.TAX.MANF.BR.ZS","TM.TAX.MANF.SM.AR.ZS","TM.TAX.MANF.SM.FN.ZS","TM.TAX.MANF.WM.FN.ZS","TM.TAX.MRCH.BC.ZS","TM.TAX.MANF.WM.AR.ZS","TM.TAX.MRCH.BR.ZS","TM.TAX.MRCH.SM.AR.ZS","TM.TAX.MRCH.WM.AR.ZS","TM.TAX.MRCH.SM.FN.ZS","TM.TAX.TCOM.BC.ZS","TM.TAX.TCOM.BR.ZS","TM.TAX.TCOM.SM.AR.ZS","TM.TAX.TCOM.SM.FN.ZS","TM.TAX.MRCH.WM.FN.ZS","TM.TAX.TCOM.WM.AR.ZS","TM.VAL.AGRI.ZS.UN","TM.UVI.MRCH.XD.WD","TM.TAX.TCOM.WM.FN.ZS","TM.VAL.FOOD.ZS.UN","TM.VAL.ICTG.ZS.UN","TM.VAL.FUEL.ZS.UN","TM.VAL.INSF.ZS.WT","TM.VAL.MMTL.ZS.UN","TM.VAL.MANF.ZS.UN","TM.VAL.MRCH.AL.ZS","TM.VAL.MRCH.CD.WT","TM.VAL.MRCH.HI.ZS","TM.VAL.MRCH.OR.ZS","TM.VAL.MRCH.R1.ZS","TM.VAL.MRCH.R2.ZS","TM.VAL.MRCH.R3.ZS","TM.VAL.MRCH.R5.ZS","TM.VAL.MRCH.R6.ZS","TM.VAL.MRCH.R4.ZS","TM.VAL.MRCH.RS.ZS","TM.VAL.MRCH.XD.WD","TM.VAL.OTHR.ZS.WT","TM.VAL.MRCH.WL.CD","TM.VAL.SERV.CD.WT","TM.VAL.TRVL.ZS.WT","TT.PRI.MRCH.XD.WD","TX.MNF.TECH.ZS.UN","TX.QTY.MRCH.XD.WD","TM.VAL.TRAN.ZS.WT","TX.UVI.MRCH.XD.WD","TX.VAL.AGRI.ZS.UN","TX.VAL.FUEL.ZS.UN","TX.VAL.ICTG.ZS.UN","TX.VAL.MMTL.ZS.UN","TX.VAL.MANF.ZS.UN","TX.VAL.FOOD.ZS.UN","TX.VAL.MRCH.AL.ZS","TX.VAL.MRCH.HI.ZS","TX.VAL.MRCH.CD.WT","TX.VAL.MRCH.OR.ZS","TX.VAL.MRCH.R2.ZS","TX.VAL.MRCH.R3.ZS","TX.VAL.MRCH.R1.ZS","TX.VAL.MRCH.R4.ZS","TX.VAL.MRCH.R6.ZS","TX.VAL.MRCH.RS.ZS","TX.VAL.MRCH.R5.ZS","TX.VAL.MRCH.WL.CD","TX.VAL.INSF.ZS.WT","TX.VAL.MRCH.XD.WD","TX.VAL.OTHR.ZS.WT","TX.VAL.TECH.CD","TX.VAL.SERV.CD.WT","TX.VAL.TECH.MF.ZS","TX.VAL.TRAN.ZS.WT","TX.VAL.TRVL.ZS.WT"];
const data = await request.http(`https://api.worldbank.org/v2/topic/21/indicator?per_page=1000&format=json`);
const currentTopicIndicators = data[1].filter(indicator => validIndicatorIds.includes(indicator.id));
const indicatorTitles = currentTopicIndicators.map(indicator => indicator.name);
const currentIndicatorTitle = input.select('Indicator', indicatorTitles[0], indicatorTitles);
const currentIndicator = currentTopicIndicators.find(indicator => indicator.name == currentIndicatorTitle);
const indicatorId = currentIndicator.id;
const indicatorNote = (str => str.length > 80 ? str.slice(0, 80 - 3) + '...' : str)(currentIndicator.sourceNote);
describe_indicator(`World Bank Indicators - Trade`, 'lower', { citation: indicatorNote, shortName: `WBI Trade` });
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
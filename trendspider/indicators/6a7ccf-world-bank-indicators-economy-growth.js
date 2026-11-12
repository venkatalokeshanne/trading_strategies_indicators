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
const validIndicatorIds = ["BG.GSR.NFSV.GD.ZS","BM.GSR.CMCP.ZS","BM.GSR.GNFS.CD","BM.GSR.FCTY.CD","BM.GSR.INSF.ZS","BM.GSR.MRCH.CD","BM.GSR.ROYL.CD","BM.GSR.NFSV.CD","BM.GSR.TRAN.ZS","BM.GSR.TOTL.CD","BM.KLT.DINV.CD.WD","BM.KLT.DINV.WD.GD.ZS","BM.GSR.TRVL.ZS","BM.TRF.PRVT.CD","BM.TRF.PWKR.CD.DT","BN.CAB.XOKA.CD","BN.CAB.XOKA.GD.ZS","BN.GSR.FCTY.CD","BN.FIN.TOTL.CD","BN.GSR.GNFS.CD","BN.GSR.MRCH.CD","BN.KAC.EOMS.CD","BN.KLT.DINV.CD","BN.KLT.PTXL.CD","BN.RES.INCL.CD","BN.TRF.CURR.CD","BX.GSR.CCIS.CD","BX.GSR.CCIS.ZS","BX.GSR.FCTY.CD","BX.GSR.GNFS.CD","BX.GSR.CMCP.ZS","BX.GSR.INSF.ZS","BX.GSR.MRCH.CD","BX.GSR.ROYL.CD","BX.GSR.TOTL.CD","BX.GSR.NFSV.CD","BX.GSR.TRAN.ZS","BX.GSR.TRVL.ZS","BX.PEF.TOTL.CD.WD","BX.KLT.DINV.WD.GD.ZS","BX.KLT.DINV.CD.WD","BX.TRF.CURR.CD","BX.TRF.PWKR.DT.GD.ZS","BX.TRF.PWKR.CD.DT","FI.RES.XGLD.CD","FI.RES.TOTL.CD","GC.XPN.TOTL.GD.ZS","GC.DOD.TOTL.GD.ZS","FP.CPI.TOTL.ZG","NE.CON.GOVT.KD","NE.CON.GOVT.CD","NE.CON.GOVT.KD.ZG","NE.CON.GOVT.CN","GC.REV.XGRT.GD.ZS","NE.CON.GOVT.KN","BN.TRF.KOGT.CD","NE.CON.GOVT.ZS","NE.CON.PRVT.CN","NE.CON.PRVT.CD","NE.CON.PRVT.KD","NE.CON.PRVT.KD.ZG","NE.CON.PRVT.KN","NE.CON.PRVT.CN.AD","NE.CON.PRVT.PC.KD.ZG","NE.CON.PRVT.PC.KD","NE.CON.PRVT.ZS","NE.CON.PRVT.PP.KD","NE.CON.PRVT.PP.CD","NE.CON.TOTL.CD","NE.CON.TOTL.CN","NE.CON.TOTL.KN","NE.CON.TOTL.KD","NE.CON.TOTL.ZS","NE.DAB.DEFL.ZS","NE.CON.TOTL.KD.ZG","NE.DAB.TOTL.CN","NE.DAB.TOTL.KN","NE.DAB.TOTL.CD","NE.DAB.TOTL.ZS","NE.DAB.TOTL.KD","NE.EXP.GNFS.CD","NE.EXP.GNFS.KD","NE.EXP.GNFS.CN","NE.EXP.GNFS.KD.ZG","NE.GDI.FTOT.CD","NE.GDI.FTOT.CN","NE.GDI.FTOT.KD","NE.EXP.GNFS.KN","NE.GDI.FTOT.KD.ZG","NE.GDI.FTOT.ZS","NE.GDI.FTOT.KN","NE.EXP.GNFS.ZS","NE.GDI.STKB.KN","NE.GDI.STKB.CD","NE.GDI.STKB.CN","NE.GDI.TOTL.CN","NE.GDI.TOTL.CD","NE.GDI.TOTL.KN","NE.GDI.TOTL.KD","NE.GDI.TOTL.KD.ZG","NE.IMP.GNFS.CD","NE.GDI.TOTL.ZS","NE.IMP.GNFS.KN","NE.IMP.GNFS.CN","NE.IMP.GNFS.KD","NE.RSB.GNFS.CD","NE.IMP.GNFS.KD.ZG","NV.AGR.EMPL.KD","NE.IMP.GNFS.ZS","NE.RSB.GNFS.KN","NE.RSB.GNFS.CN","NV.AGR.TOTL.CD","NV.AGR.TOTL.KD","NE.TRD.GNFS.ZS","NV.AGR.TOTL.CN","NE.RSB.GNFS.ZS","NV.IND.MANF.CD","NV.IND.MANF.ZS","NV.AGR.TOTL.ZS","NV.IND.EMPL.KD","NV.IND.MANF.KD","NV.IND.MANF.CN","NV.IND.TOTL.CD","NV.IND.TOTL.CN","NV.IND.TOTL.KD","NV.IND.TOTL.ZS","NV.MNF.CHEM.ZS.UN","NV.MNF.MTRN.ZS.UN","NV.MNF.TECH.ZS.UN","NV.MNF.FBTO.ZS.UN","NV.SRV.EMPL.KD","NV.MNF.OTHR.ZS.UN","NV.MNF.TXTL.ZS.UN","NV.SRV.TOTL.CN","NV.SRV.TOTL.KD","NV.SRV.TOTL.ZS","NV.SRV.TOTL.CD","NY.ADJ.AEDU.CD","NY.ADJ.DCO2.GN.ZS","NY.ADJ.DFOR.CD","NY.ADJ.DCO2.CD","NY.ADJ.DFOR.GN.ZS","NY.ADJ.DMIN.CD","NY.ADJ.DKAP.CD","NY.ADJ.AEDU.GN.ZS","NY.ADJ.DKAP.GN.ZS","NY.ADJ.DRES.GN.ZS","NY.ADJ.DNGY.GN.ZS","NY.ADJ.NNAT.CD","NY.ADJ.DPEM.CD","NY.ADJ.DNGY.CD","NY.ADJ.DMIN.GN.ZS","NY.ADJ.DPEM.GN.ZS","NY.ADJ.ICTR.GN.ZS","NY.ADJ.NNTY.KD","NY.ADJ.NNAT.GN.ZS","NY.ADJ.NNTY.CD","NY.ADJ.NNTY.KD.ZG","NY.ADJ.NNTY.PC.KD","NY.ADJ.NNTY.PC.KD.ZG","NY.ADJ.SVNG.GN.ZS","NY.ADJ.SVNG.CD","NY.ADJ.NNTY.PC.CD","NY.ADJ.SVNX.CD","NY.ADJ.SVNX.GN.ZS","NY.GDP.DEFL.ZS","NY.GDP.DEFL.KD.ZG","NY.EXP.CAPM.KN","NY.GDP.DISC.CN","NY.GDP.DISC.KN","NY.GDP.FCST.CD","NY.GDP.MKTP.CD","NY.GDP.FCST.KD","NY.GDP.FCST.CN","NY.GDP.MKTP.CN","NY.GDP.MKTP.CN.AD","NY.GDP.MKTP.KD","NY.GDP.MKTP.KD.ZG","NY.GDP.MKTP.KN","NY.GDP.MKTP.PP.CD","NY.GDP.PCAP.CD","NY.GDP.MKTP.PP.KD","NY.GDP.PCAP.CN","NY.GDP.PCAP.KD","NY.GDP.PCAP.KD.ZG","NY.GDP.PCAP.PP.KD","NY.GDS.TOTL.CD","NY.GDP.PCAP.PP.CD","NY.GDP.PCAP.KN","NY.GDS.TOTL.CN","NY.GDS.TOTL.ZS","NY.GDY.TOTL.KN","NY.GNP.ATLS.CD","NY.GNP.MKTP.CN","NY.GNP.MKTP.CN.AD","NY.GNP.MKTP.CD","NY.GNP.MKTP.KD","NY.GNP.MKTP.PP.KD","NY.GNP.PCAP.CD","NY.GNP.MKTP.KD.ZG","NY.GNP.MKTP.PP.CD","NY.GNP.MKTP.KN","NY.GNP.PCAP.CN","NY.GNP.PCAP.KD","NY.GNP.PCAP.KD.ZG","NY.GNP.PCAP.PP.CD","NY.GNP.PCAP.PP.KD","NY.GNS.ICTR.CD","NY.GNS.ICTR.GN.ZS","NY.GNS.ICTR.CN","NY.GNP.PCAP.KN","NY.GNS.ICTR.ZS","NY.GSR.NFCY.CD","NY.GSR.NFCY.CN","NY.GSR.NFCY.KN","NY.TAX.NIND.CD","NY.TAX.NIND.CN","NY.TRF.NCTR.CD","NY.TTF.GNFS.KN","NY.TRF.NCTR.KN","NY.TRF.NCTR.CN","PA.NUS.ATLS","PA.NUS.PPP","PA.NUS.PRVT.PP"];
const data = await request.http(`https://api.worldbank.org/v2/topic/3/indicator?per_page=1000&format=json`);
const currentTopicIndicators = data[1].filter(indicator => validIndicatorIds.includes(indicator.id));
const indicatorTitles = currentTopicIndicators.map(indicator => indicator.name);
const currentIndicatorTitle = input.select('Indicator', indicatorTitles[0], indicatorTitles);
const currentIndicator = currentTopicIndicators.find(indicator => indicator.name == currentIndicatorTitle);
const indicatorId = currentIndicator.id;
const indicatorNote = (str => str.length > 80 ? str.slice(0, 80 - 3) + '...' : str)(currentIndicator.sourceNote);
describe_indicator(`World Bank Indicators - Economy & Growth`, 'lower', { citation: indicatorNote, shortName: `WBI Economy` });
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
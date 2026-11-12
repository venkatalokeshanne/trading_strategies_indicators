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
const validIndicatorIds = ["AG.LND.EL5M.RU.ZS","AG.LND.EL5M.RU.K2","AG.LND.AGRI.ZS","AG.LND.FRST.K2","AG.LND.FRST.ZS","AG.LND.ARBL.ZS","AG.LND.PRCP.MM","AG.LND.EL5M.ZS","AG.LND.TOTL.K2","AG.LND.TOTL.RU.K2","AG.SRF.TOTL.K2","AG.LND.EL5M.UR.ZS","AG.LND.TOTL.UR.K2","AG.LND.EL5M.UR.K2","EG.CFT.ACCS.RU.ZS","EG.EGY.PRIM.PP.KD","EG.CFT.ACCS.UR.ZS","EG.CFT.ACCS.ZS","EG.ELC.FOSL.ZS","EG.ELC.ACCS.ZS","EG.ELC.RNEW.ZS","EG.ELC.RNWX.ZS","EG.ELC.RNWX.KH","EG.FEC.RNEW.ZS","EN.ATM.PM25.MC.T2.ZS","EN.ATM.PM25.MC.M3","EN.ATM.PM25.MC.T1.ZS","EN.ATM.PM25.MC.T3.ZS","EN.ATM.PM25.MC.ZS","EN.BIR.THRD.NO","EN.CLC.DRSK.XQ","EN.CLC.MDAT.ZS","EN.FSH.THRD.NO","EN.GHG.ALL.LU.MT.CE.AR5","EN.GHG.ALL.MT.CE.AR5","EN.GHG.CH4.AG.MT.CE.AR5","EN.GHG.CH4.FE.MT.CE.AR5","EN.GHG.CH4.IC.MT.CE.AR5","EN.GHG.CH4.MT.CE.AR5","EN.GHG.CH4.IP.MT.CE.AR5","EN.GHG.CH4.BU.MT.CE.AR5","EN.GHG.CH4.PI.MT.CE.AR5","EN.GHG.CH4.TR.MT.CE.AR5","EN.GHG.CH4.ZG.AR5","EN.GHG.ALL.PC.CE.AR5","EN.GHG.CH4.WA.MT.CE.AR5","EN.GHG.CO2.AG.MT.CE.AR5","EN.GHG.CO2.BU.MT.CE.AR5","EN.GHG.CO2.FE.MT.CE.AR5","EN.GHG.CO2.LU.DF.MT.CE.AR5","EN.GHG.CO2.IC.MT.CE.AR5","EN.GHG.CO2.LU.FL.MT.CE.AR5","EN.GHG.CO2.IP.MT.CE.AR5","EN.GHG.CO2.LU.OS.MT.CE.AR5","EN.GHG.CO2.PC.CE.AR5","EN.GHG.CO2.PI.MT.CE.AR5","EN.GHG.CO2.RT.GDP.KD","EN.GHG.CO2.RT.GDP.PP.KD","EN.GHG.CO2.TR.MT.CE.AR5","EN.GHG.CO2.LU.OL.MT.CE.AR5","EN.GHG.FGAS.IP.MT.CE.AR5","EN.GHG.N2O.AG.MT.CE.AR5","EN.GHG.CO2.ZG.AR5","EN.GHG.N2O.BU.MT.CE.AR5","EN.GHG.CO2.WA.MT.CE.AR5","EN.GHG.N2O.IC.MT.CE.AR5","EN.GHG.N2O.FE.MT.CE.AR5","EN.GHG.N2O.MT.CE.AR5","EN.GHG.N2O.IP.MT.CE.AR5","EN.GHG.N2O.PI.MT.CE.AR5","EN.GHG.N2O.WA.MT.CE.AR5","EN.GHG.CO2.MT.CE.AR5","EN.GHG.N2O.TR.MT.CE.AR5","EN.GHG.TOT.ZG.AR5","EN.GHG.N2O.ZG.AR5","EN.HPT.THRD.NO","EN.MAM.THRD.NO","EN.POP.EL5M.UR.ZS","EN.POP.EL5M.RU.ZS","EN.POP.EL5M.ZS","EN.POP.SLUM.UR.ZS","ER.FSH.CAPT.MT","ER.FSH.AQUA.MT","ER.FSH.PROD.MT","ER.GDP.FWTL.M3.KD","ER.H2O.FWAG.ZS","ER.H2O.FWDM.ZS","ER.H2O.FWTL.ZS","ER.H2O.FWST.ZS","ER.H2O.FWIN.ZS","ER.H2O.FWTL.K3","ER.H2O.INTR.K3","ER.LND.PTLD.ZS","ER.H2O.INTR.PC","ER.MRN.PTMR.ZS","NY.ADJ.AEDU.GN.ZS","ER.PTD.TOTL.ZS","NY.ADJ.DCO2.GN.ZS","NY.ADJ.AEDU.CD","NY.ADJ.DCO2.CD","NY.ADJ.DFOR.CD","NY.ADJ.DKAP.CD","NY.ADJ.DFOR.GN.ZS","NY.ADJ.DKAP.GN.ZS","NY.ADJ.DMIN.CD","NY.ADJ.DMIN.GN.ZS","NY.ADJ.DNGY.CD","NY.ADJ.DNGY.GN.ZS","NY.ADJ.ICTR.GN.ZS","NY.ADJ.DPEM.GN.ZS","NY.ADJ.SVNG.CD","NY.ADJ.NNAT.GN.ZS","NY.ADJ.SVNG.GN.ZS","NY.ADJ.SVNX.CD","NY.ADJ.NNAT.CD","NY.ADJ.SVNX.GN.ZS","NY.ADJ.DPEM.CD","NY.GDP.COAL.RT.ZS","NY.GDP.MINR.RT.ZS","NY.GDP.NGAS.RT.ZS","NY.GDP.FRST.RT.ZS","NY.GDP.PETR.RT.ZS","NY.GDP.TOTL.RT.ZS","SH.H2O.BASW.UR.ZS","SH.H2O.BASW.RU.ZS","SH.H2O.BASW.ZS","SH.STA.BASS.RU.ZS","SH.STA.BASS.UR.ZS","SH.STA.AIRP.P5","SH.H2O.SMDW.ZS","SH.STA.BASS.ZS","SH.STA.ODFC.RU.ZS","SH.STA.POIS.P5","SH.H2O.SMDW.UR.ZS","SH.STA.ODFC.ZS","SH.STA.ODFC.UR.ZS","SH.STA.POIS.P5.FE","SH.STA.SMSS.ZS","SH.STA.POIS.P5.MA","SH.STA.WASH.P5","SH.STA.SMSS.UR.ZS","EN.GHG.CO2.LU.MT.CE.AR5"];
const data = await request.http(`https://api.worldbank.org/v2/topic/6/indicator?per_page=1000&format=json`);
const currentTopicIndicators = data[1].filter(indicator => validIndicatorIds.includes(indicator.id));
const indicatorTitles = currentTopicIndicators.map(indicator => indicator.name);
const currentIndicatorTitle = input.select('Indicator', indicatorTitles[0], indicatorTitles);
const currentIndicator = currentTopicIndicators.find(indicator => indicator.name == currentIndicatorTitle);
const indicatorId = currentIndicator.id;
const indicatorNote = (str => str.length > 80 ? str.slice(0, 80 - 3) + '...' : str)(currentIndicator.sourceNote);
describe_indicator(`World Bank Indicators - Environment`, 'lower', { citation: indicatorNote, shortName: `WBI Environment` });
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
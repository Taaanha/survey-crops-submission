/* Field twin page (#/twin). Draws what the server returns for the farmer's field; it computes nothing about
   crops, weather or risk. Every value is a past-season record or a what-if on past seasons, never a forecast.
   Uses globals from modes.html: st, lang, s, esc, T, N, bi, iso2d, fd, $, art, spinner, watchBtn, showSources, CS_API.
   Adapters: CS_TW (replay), CS_SOIL, CS_PP (passport), CS_SC (what-if). */
var TW={crop:'mustard',year:2023,sow:'',scenSow:'',rain:0,temp:0,week:0,play:false,timer:null,layer:'elevation',
 key:{},soil:null,pass:null,rep:null,scen:null,map:null,grid:null,ads:{}};
var TW_CROPS=['wheat','mustard','potato','lentil'];   // the server's replay and what-if cover these four; boro rice is not built yet
var TW_EV={heat:['#FF7A6B','Hot day','গরম দিন'],night_heat:['#FFB547','Warm night','গরম রাত'],cold:['#4FC3F7','Cold','ঠান্ডা'],rain:['#4FC3F7','Heavy rain','ভারী বৃষ্টি'],dry:['#F2C14E','Dry','শুকনো'],irrigation:['#2BB3A3','Watering','সেচ'],ok:['#7BD389','No problem','সমস্যা নেই']};
var TW_STAGE={initial:['Start','শুরু'],development:['Growing','বৃদ্ধি'],mid:['Flowering / middle','ফুল / মাঝ'],late:['Ripening','পাকা']};
var TW_METRIC={irrigation_mm_mean:['Irrigation needed, average','সেচ লাগে, গড়','mm','মিমি'],irrigation_mm_worst20:['Irrigation needed, worst 20% of years','সেচ লাগে, সবচেয়ে খারাপ ২০% বছর','mm','মিমি'],water_stress_days_mean:['Dry-soil days (no irrigation)','শুকনো মাটির দিন (সেচ ছাড়া)','days','দিন'],rain_mm_mean:['Rain in the season','মৌসুমে বৃষ্টি','mm','মিমি'],etc_mm_mean:['Crop water demand','ফসলের পানির চাহিদা','mm','মিমি']};
(function(){var c=document.createElement('style');c.textContent=
 '.twrow,.twcharts{display:grid;gap:14px;margin-bottom:14px}.twrow>div{display:flex;flex-direction:column;gap:14px;min-width:0}.twrow>.card,.twrow>div>.card{margin:0}.twch{min-width:0}'+
 '@media(min-width:900px){.twrow,.twcharts{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.twrow{align-items:stretch}.twrow>.card:first-child{display:flex;flex-direction:column}.twrow>.card:first-child .twmapbox{flex:1;display:flex;flex-direction:column}.twrow>.card:first-child #twmap{flex:1;height:auto;min-height:330px}body[data-mode="farmer"] .twcharts>.twch:nth-child(3){grid-column:1/-1}}'+
 '.twmapbox{position:relative;border-radius:18px;overflow:hidden;border:1px solid var(--line)}#twmap{height:330px;background:#0a1d27}'+
 '.twlayers{position:absolute;right:10px;top:10px;z-index:500;display:flex;flex-direction:column;gap:8px}'+
 '.twc{width:64px;height:64px;border-radius:50%;border:1px solid rgba(255,255,255,.35);background:rgba(11,38,48,.82);color:var(--ink);font:600 .68rem/1.1 var(--body);display:flex;align-items:center;justify-content:center;text-align:center;padding:4px;cursor:pointer}'+
 '.twc.on{border-color:var(--gold);color:var(--gold);box-shadow:0 0 0 2px rgba(242,193,78,.35)}.twc[disabled]{opacity:.4;cursor:not-allowed}'+
 '.twleg{height:10px;border-radius:6px;background:linear-gradient(90deg,hsl(220,80%,50%),hsl(150,80%,45%),hsl(60,85%,50%),hsl(0,80%,50%))}'+
 '.twtiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px}.twt{background:rgba(255,255,255,.05);border:1px solid var(--line);border-radius:14px;padding:10px}.twt b{display:block;font-size:1.25rem}.twt small{color:var(--mute)}'+
 '.twscrub{display:flex;gap:10px;align-items:center;margin:8px 0}.twscrub input{flex:1;min-width:0}'+
 '.twctl{display:flex;flex-wrap:wrap;gap:8px;align-items:end;margin:8px 0}.twctl label{display:flex;flex-direction:column;font-size:.85em;color:var(--mute);gap:2px}'+
 '#pg-twin .crops{grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:6px}#pg-twin .crop{padding:6px 2px;font-size:.74rem;min-height:0;gap:2px}#pg-twin .crop svg{width:36px;height:36px}.twrng{width:100%}.twtab{width:100%;border-collapse:collapse;font-size:.9em}.twtab th,.twtab td{padding:6px 4px;border-bottom:1px solid var(--line);text-align:left}';
 document.head.appendChild(c)})();
function twT(k){return {en:{
  h:'Field twin',lead:'Your field and its NASA data in one place. Replay a past season with a crop, or ask “what if” on past seasons. Never a forecast.',
  field:'Your field',terrain:'Terrain and flood history (30 m pixels)',noPass:'30 m field maps are ready only for the two demo fields. For your place you see soil and past-season replays.',
  soil:'Soil here',ph:'Soil acidity (pH)',oc:'Organic carbon',tex:'Texture',na:'not available for this point',est1:'SoilGrids model estimate for this point, not a lab test.',est2:'District soil values (SoilGrids did not answer or has no value here).',
  season:'Replay a past season',crop:'Crop',year:'Past year',sow:'Sowing date',go:'Replay',week:'Week',stage:'Stage',tot:'Whole season',
  chSoil:'Soil water (% of available water, no irrigation)',chRain:'Rain (bars) and crop water demand (line), mm per week',chTemp:'Temperature, °C (weekly average of the daily highest and lowest)',chSmap:'NASA SMAP root-zone soil moisture, for comparison',
  limits:'Limits the crop can bear (from the sources)',whatif:'What if… (on past seasons)',rain:'Rain change',temp:'Warmer by',base:'Now',what:'What if',chg:'Change',
  pick:'Pick a past year and a sowing date, then tap Replay.',wait:'Asking the server…',play:'Play',pause:'Pause',legend:'Week flags',notfc:'A record of past seasons and what-ifs on them. Not a forecast.',
  dataFor:'NASA data for the area around your field (rain ~0.1°, temperature ~0.5°, soil moisture ~9 km), not the exact plot.',
  elevation:'Height',slope:'Slope',flood:'Flood days',noLayer:'Not available here',irrN:'Irrigation',stressN:'Dry-soil days',rainN:'Rain',demN:'Crop water demand',evN:'Waterings'},
 bn:{h:'মাঠের ডিজিটাল যমজ',lead:'আপনার মাঠ ও তার NASA তথ্য এক জায়গায়। কোনো ফসল দিয়ে অতীতের একটি মৌসুম আবার দেখুন, বা অতীত মৌসুমে “যদি” প্রশ্ন করুন। কখনও পূর্বাভাস নয়।',
  field:'আপনার মাঠ',terrain:'ভূমির গঠন ও বন্যার ইতিহাস (৩০ মিটার পিক্সেল)',noPass:'৩০ মিটার মাঠের মানচিত্র শুধু দুটি ডেমো মাঠের জন্য তৈরি। আপনার জায়গার জন্য মাটি ও অতীত মৌসুমের পুনরায়-দেখা পাবেন।',
  soil:'এখানকার মাটি',ph:'মাটির অম্লতা (pH)',oc:'জৈব কার্বন',tex:'মাটির ধরন',na:'এই বিন্দুর জন্য পাওয়া যায়নি',est1:'এই বিন্দুর জন্য SoilGrids মডেলের অনুমান, ল্যাব পরীক্ষা নয়।',est2:'জেলার মাটির মান (SoilGrids উত্তর দেয়নি বা এখানে মান নেই)।',
  season:'অতীতের একটি মৌসুম আবার দেখুন',crop:'ফসল',year:'অতীতের বছর',sow:'বপনের তারিখ',go:'দেখুন',week:'সপ্তাহ',stage:'ধাপ',tot:'পুরো মৌসুম',
  chSoil:'মাটির পানি (প্রাপ্য পানির %, সেচ ছাড়া)',chRain:'বৃষ্টি (স্তম্ভ) ও ফসলের পানির চাহিদা (রেখা), মিমি/সপ্তাহ',chTemp:'তাপমাত্রা, °সে (দৈনিক সর্বোচ্চ ও সর্বনিম্নের সাপ্তাহিক গড়)',chSmap:'NASA SMAP শিকড় অঞ্চলের মাটির আর্দ্রতা, তুলনার জন্য',
  limits:'ফসল যে সীমা সইতে পারে (উৎস থেকে)',whatif:'যদি… (অতীত মৌসুমে)',rain:'বৃষ্টির পরিবর্তন',temp:'বেশি গরম',base:'এখন',what:'যদি',chg:'পরিবর্তন',
  pick:'অতীতের একটি বছর ও বপনের তারিখ বাছুন, তারপর “দেখুন” চাপুন।',wait:'সার্ভারকে জিজ্ঞেস করা হচ্ছে…',play:'চালান',pause:'থামান',legend:'সপ্তাহের চিহ্ন',notfc:'অতীত মৌসুমের রেকর্ড ও তার উপর “যদি” হিসাব। পূর্বাভাস নয়।',
  dataFor:'আপনার মাঠের আশেপাশের এলাকার NASA তথ্য (বৃষ্টি ~০.১°, তাপমাত্রা ~০.৫°, মাটির আর্দ্রতা ~৯ কিমি), সঠিক প্লট নয়।',
  elevation:'উচ্চতা',slope:'ঢাল',flood:'বন্যার দিন',noLayer:'এখানে নেই',irrN:'সেচ',stressN:'শুকনো মাটির দিন',rainN:'বৃষ্টি',demN:'ফসলের পানির চাহিদা',evN:'সেচের সংখ্যা'}}[lang][k]||k}
function twSrc(ids,ad){if(!ad||!ids||!ids.length)return '';var key='k'+Object.keys(TW.ads).length;TW.ads[key]=ad;return '<button class="src" data-act="twsrc" data-v="'+key+'|'+esc(ids.join(','))+'">'+bi('Source','উৎস')+' ›</button>'}
function twU(u){return lang==='bn'?({mm:'মিমি',days:'দিন','%':'%'}[u]||u):u}
function twMeas(m){return m?N(m.value)+' '+esc(twU(m.unit)):''}
function twFieldId(){var f=st.fromField&&FIELDS[st.field];return f?f.id:null}
/* ---- loading ---- */
function twLoad(){
 var kSoil=JSON.stringify([st.district,st.lat,st.lon]);
 if(TW.key.soil!==kSoil){TW.key.soil=kSoil;TW.soil=null;CS_API.get('/api/v1/soil?district='+st.district+'&lat='+st.lat+'&lon='+st.lon).then(function(r){if(TW.key.soil===kSoil){TW.soil={r:r,ad:r.data?CS_SOIL.adapt(r.data):null};twPaint()}})}
 var fid=twFieldId(),kP=String(fid);
 if(TW.key.pass!==kP){TW.key.pass=kP;TW.pass=null;if(fid)CS_API.get('/api/v1/map/passport?field='+fid).then(function(r){if(TW.key.pass===kP){TW.pass={r:r,ad:r.data?CS_PP.adapt(r.data):null};twPaint()}})}
 twScenario(true)}
function twScenario(first,force){
 var q='district='+st.district+'&crop='+TW.crop+'&rain_pct='+TW.rain+'&temp_add_c='+TW.temp+(TW.scenSow?'&sowing='+TW.scenSow:''),k=q;
 if(!force&&TW.key.scen===k&&TW.scen)return;
 TW.key.scen=k;TW.scenWait=true;twResPaint();
 CS_API.get('/api/v1/map/scenario?'+q).then(function(r){if(TW.key.scen!==k)return;TW.scenWait=false;TW.scen={r:r,ad:r.data?CS_SC.adapt(r.data):null};
  if(first&&!TW.sow&&TW.scen.ad&&TW.scen.ad.inputs&&TW.scen.ad.inputs.sowing_mmdd){TW.sow=TW.year+'-'+TW.scen.ad.inputs.sowing_mmdd;twReplay();return}
  twResPaint()})}
function twReplay(){
 if(!TW.sow){TW.rep=null;twPaint();return}
 var k=JSON.stringify([st.district,st.lat,st.lon,TW.crop,TW.year,TW.sow]);TW.key.rep=k;TW.repWait=true;twPaint();
 CS_API.get('/api/v1/field-twin?district='+st.district+'&lat='+st.lat+'&lon='+st.lon+'&crop='+TW.crop+'&year='+TW.year+'&sow_date='+TW.sow+'&lang='+lang).then(function(r){
  if(TW.key.rep!==k)return;TW.repWait=false;TW.rep={r:r,ad:r.data?CS_TW.adapt(r.data):null};TW.week=0;twPaint()})}
/* ---- drawing helpers (plot the server's numbers; nothing is worked out here) ---- */
function twHue(t){return 'hsl('+Math.round(220-220*t)+',80%,'+(t>.45&&t<.75?45:50)+'%)'}
function twFinite(g){var v=[];g.forEach(function(r){r.forEach(function(x){if(typeof x==='number'&&isFinite(x))v.push(x)})});return v}
function twMapInit(){
 var el=$('#twmap');if(!el||!window.L)return;if(TW.map){try{TW.map.remove()}catch(e){}TW.map=null}
 TW.map=L.map(el,{zoomControl:true}).setView([st.lat,st.lon],17);
 var ok=0,er=0,esri=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Imagery © Esri, Maxar, Earthstar Geographics'}).addTo(TW.map);
 esri.on('tileload',function(){ok++});esri.on('tileerror',function(){er++;if(er>=3&&!ok){TW.map.removeLayer(esri);L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(TW.map)}});
 L.circleMarker([st.lat,st.lon],{radius:6,color:'#F2C14E',weight:2,fillOpacity:.9}).addTo(TW.map);
 TW.grid=L.layerGroup().addTo(TW.map);twGrid();setTimeout(function(){TW.map&&TW.map.invalidateSize()},250)}
var TW_LKEY={elevation:'nasadem_elevation',slope:'nasadem_slope',flood:'inundation'};
function twLayer(){var p=TW.pass&&TW.pass.ad;if(!p||!p.ok)return null;
 var ly=p.layers.filter(function(l){return l.key.indexOf(TW_LKEY[TW.layer])>=0})[0];
 if(!ly||ly.status!=='assessed'||!ly.grid.length)return null;
 var vals=twFinite(ly.grid);if(!vals.length)return null;var mn=Math.min.apply(null,vals),mx=Math.max.apply(null,vals);if(mx===mn)mx=mn+1;return {ly:ly,mn:mn,mx:mx}}
function twGrid(){
 if(!TW.map||!TW.grid)return;TW.grid.clearLayers();var Lr=twLayer();if(!Lr)return;var ly=Lr.ly,mn=Lr.mn,mx=Lr.mx;
 var n=ly.grid.length,half=(n-1)/2,dlat=ly.pixelM/111320,dlon=ly.pixelM/(111320*Math.cos(st.lat*Math.PI/180));
 ly.grid.forEach(function(row,r){row.forEach(function(v,c){if(typeof v!=='number'||!isFinite(v))return;
  var la=st.lat+(half-r)*dlat,lo=st.lon+(c-half)*dlon,col=twHue((v-mn)/(mx-mn));
  L.rectangle([[la-dlat/2,lo-dlon/2],[la+dlat/2,lo+dlon/2]],{stroke:false,fillColor:col,fillOpacity:.55}).bindTooltip(N(Math.round(v*10)/10)+' '+ly.unit).addTo(TW.grid)})});
}
function twLine(rows,keys,styles,cur,label,fmt){
 var W=320,H=96,P=8,vals=[];rows.forEach(function(r){keys.forEach(function(k){if(typeof r[k]==='number')vals.push(r[k])})});if(rows.length<2||!vals.length)return '';
 var mn=Math.min.apply(null,vals.concat([0])),mx=Math.max.apply(null,vals);if(mx===mn)mx=mn+1;
 function X(i){return P+i*(W-2*P)/(rows.length-1)}function Y(v){return H-P-(v-mn)*(H-2*P)/(mx-mn)}
 var g='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+esc(label)+'" style="width:100%;height:auto;background:rgba(255,255,255,.04);border-radius:10px">';
 keys.forEach(function(k,ki){if(styles[ki]==='bar'){var bw=(W-2*P)/rows.length*.7;rows.forEach(function(r,i){if(typeof r[k]==='number')g+='<rect x="'+(X(i)-bw/2).toFixed(1)+'" y="'+Y(r[k]).toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+Math.max(0,Y(0)-Y(r[k])).toFixed(1)+'" style="fill:var(--water);opacity:.75"/>'});return}
  var pts=rows.map(function(r,i){return typeof r[k]==='number'?X(i).toFixed(1)+','+Y(r[k]).toFixed(1):null}).filter(Boolean).join(' ');g+='<polyline fill="none" stroke-width="2" style="'+styles[ki]+'" points="'+pts+'"/>'});
 g+='<line x1="'+X(cur).toFixed(1)+'" x2="'+X(cur).toFixed(1)+'" y1="'+P+'" y2="'+(H-P)+'" stroke-dasharray="3 3" style="stroke:var(--gold)"/></svg>';
 return '<p style="margin:10px 0 2px;font-size:.88em;color:var(--mute)">'+esc(label)+'</p>'+g}
function twStrip(rows,cur){var W=320,n=rows.length,w=(W-16)/n,g='<svg viewBox="0 0 '+W+' 30" style="width:100%;height:auto"><title>'+esc(twT('stage'))+'</title>';
 rows.forEach(function(r,i){var st_=TW_STAGE[r.stage];g+='<rect x="'+(8+i*w).toFixed(1)+'" y="2" width="'+(w-1).toFixed(1)+'" height="12" rx="2" style="fill:'+({initial:'#7BD389',development:'#2BB3A3',mid:'#F2C14E',late:'#FFB547'}[r.stage]||'#888')+';opacity:'+(i===cur?1:.55)+'"/>';
  var evs=r.events.filter(function(e){return e!=='ok'});evs.slice(0,2).forEach(function(e,j){g+='<circle cx="'+(8+i*w+w/2).toFixed(1)+'" cy="'+(21+j*5)+'" r="2.2" fill="'+((TW_EV[e]||['#888'])[0])+'"/>'})});
 return g+'</svg>'}
function twWeekTile(r){
 var ev=r.events.map(function(e){var x=TW_EV[e]||['#888',e,e];return '<span class="badge" style="border-color:'+x[0]+'">'+esc(bi(x[1],x[2]))+'</span>'}).join(' ');
 var st_=TW_STAGE[r.stage]||[r.stage,r.stage];
 return '<div class="twtiles"><div class="twt"><small>'+esc(twT('week'))+'</small><b>'+iso2d(r.week)+'</b><small>'+esc(bi(st_[0],st_[1]))+'</small></div>'+
  '<div class="twt"><small>'+esc(twT('rainN'))+'</small><b>'+N(r.rain)+' '+esc(twU('mm'))+'</b></div><div class="twt"><small>'+esc(twT('demN'))+'</small><b>'+N(r.demand)+' '+esc(twU('mm'))+'</b></div>'+
  '<div class="twt"><small>°C</small><b>'+N(r.tmax)+' / '+N(r.tmin)+'</b></div><div class="twt"><small>'+esc(twT('chSoil').split('(')[0])+'</small><b>'+N(r.soil)+'%</b></div>'+
  '<div class="twt"><small>'+esc(twT('stressN'))+'</small><b>'+N(r.stress)+'</b></div><div class="twt"><small>'+esc(twT('irrN'))+'</small><b>'+N(r.irr)+' '+esc(twU('mm'))+'</b></div></div><p style="margin:8px 0">'+ev+'</p>'}
/* ---- sections ---- */
function twSoilHtml(){
 var S=TW.soil;if(!S)return '<div class="card"><p>'+spinner()+esc(twT('wait'))+'</p></div>';var a=S.ad;
 if(!a||!a.ok)return '<div class="note warn"><span>'+esc(a&&a.errors.length?T(a.errors[0]):s('offline'))+'</span></div>';
 var live=CS_API.isLive(S.r);
 return '<div class="card"><h3>'+esc(twT('soil'))+'</h3>'+(live?'':'<div class="note warn"><span class="badge">'+esc(s('planDemo'))+'</span></div>')+'<div class="twtiles">'+
  '<div class="twt"><small>'+esc(twT('ph'))+'</small><b>'+(a.ph?N(a.ph.value):'–')+'</b>'+(a.ph?twSrc(a.ph.src,a):'<small>'+esc(twT('na'))+'</small>')+'</div>'+
  '<div class="twt"><small>'+esc(twT('oc'))+'</small><b>'+(a.oc?N(a.oc.value)+' <small>g/kg</small>':'–')+'</b>'+(a.oc?twSrc(a.oc.src,a):'<small>'+esc(twT('na'))+'</small>')+'</div>'+
  '<div class="twt"><small>'+esc(twT('tex'))+'</small><b>'+(a.texture?esc(T(a.texture)):'–')+'</b><small>'+(a.sand?N(a.sand.value)+'% / '+N(a.silt.value)+'% / '+N(a.clay.value)+'%':'')+'</small></div></div>'+
  '<p style="color:var(--mute);font-size:.85em;margin-top:8px">'+esc(a.estimate==='field'?twT('est1'):twT('est2'))+'</p>'+a.notices.map(function(n){return '<div class="note"><span>'+esc(T(n))+'</span></div>'}).join('')+(a.advice?'<div class="note"><span>'+esc(T(a.advice))+'</span></div>':'')+'</div>'}
function twMapHtml(){
 var p=TW.pass&&TW.pass.ad,layers=[['elevation','nasadem_elevation'],['slope','nasadem_slope'],['flood','inundation']];
 var chips='';if(p&&p.ok)chips='<div class="twlayers">'+layers.map(function(l){var ly=p.layers.filter(function(x){return x.key.indexOf(l[1])>=0})[0],okk=ly&&ly.status==='assessed';return '<button class="twc'+(TW.layer===l[0]?' on':'')+'" data-act="twlayer" data-v="'+l[0]+'"'+(okk?'':' disabled title="'+esc((ly&&ly.reason)||twT('noLayer'))+'"')+'>'+esc(twT(l[0]))+'</button>'}).join('')+'</div>';
 var Lr=twLayer(),leg=Lr?'<div style="padding:8px 4px"><div class="twleg"></div><div style="display:flex;justify-content:space-between;font-size:.85em;color:var(--mute)"><span>'+N(Math.round(Lr.mn*10)/10)+'</span><span>'+esc(twT(TW.layer))+' ('+esc(Lr.ly.unit)+')</span><span>'+N(Math.round(Lr.mx*10)/10)+'</span></div><p style="font-size:.8em;color:var(--mute)">'+(Lr.ly.url?'<a href="'+esc(Lr.ly.url)+'" target="_blank" rel="noopener">'+esc(Lr.ly.dataset)+' ↗</a>':'')+'</p></div>':'';
 return '<div class="card"><h3>'+esc(twT('field'))+': '+(st.fromField&&FIELDS[st.field]?esc(T(FIELDS[st.field].n)):N(st.lat.toFixed(4))+'° N, '+N(st.lon.toFixed(4))+'° E')+'</h3><div class="twmapbox"><div id="twmap"></div>'+chips+'</div>'+leg+
  (p&&p.ok?'<p style="color:var(--mute);font-size:.85em">'+esc(twT('terrain'))+'</p>':'<div class="note'+(TW.pass&&!TW.pass.ad?' warn':'')+'"><span>'+esc(TW.pass&&!TW.pass.ad?s('offline'):(TW.pass===null&&twFieldId()?twT('wait'):twT('noPass')))+'</span></div>')+
  '<p style="color:var(--mute);font-size:.8em">'+esc(twT('dataFor'))+'</p></div>'}
function twSeasonHtml(){
 var yrs='';for(var y=2024;y>=2001;y--)yrs+='<option value="'+y+'"'+(y===TW.year?' selected':'')+'>'+N(y)+'</option>';
 var h='<div class="card"><h3>'+esc(twT('season'))+'</h3><div class="crops">'+TW_CROPS.map(function(c){var k=c==='boro_rice'?'boro':c;return '<button class="crop'+(TW.crop===c?' on':'')+'" data-act="twcrop" data-v="'+c+'">'+art((CROPS[k]||{a:'sow'}).a,36)+'<span>'+esc(T((CROPS[k]||{n:{en:c,bn:c}}).n))+'</span></button>'}).join('')+'</div>'+
  '<p style="color:var(--mute);font-size:.82em;margin:6px 0 0">'+esc(bi('Boro rice replay is not built yet.','বোরো ধানের পুনরায়-দেখা এখনও তৈরি হয়নি।'))+'</p><div class="twctl"><label>'+esc(twT('year'))+'<select id="twyear">'+yrs+'</select></label><label>'+esc(twT('sow'))+'<input type="date" id="twsow" value="'+esc(TW.sow)+'"></label><button class="btn sm" data-act="twgo">'+esc(twT('go'))+'</button></div>';
 var R=TW.rep;
 if(TW.repWait)return h+'<p>'+spinner()+esc(twT('wait'))+'</p></div>';
 if(!R)return h+'<p style="color:var(--mute)">'+esc(twT('pick'))+'</p></div>';
 var a=R.ad;if(!a)return h+'<div class="note warn"><span>'+esc(s('offline'))+'</span></div></div>';
 if(!a.ok)return h+'<div class="note warn"><span>'+esc(a.errors.length?T(a.errors[0]):s('planNone'))+'</span></div></div>';
 var live=CS_API.isLive(R.r),rows=a.rows,i=Math.min(TW.week,rows.length-1);
 h+=(live?'':'<div class="note warn"><span class="badge">'+esc(s('planDemo'))+'</span></div>')+(a.label?'<p style="color:var(--mute)">'+esc(T(a.label))+'</p>':'')+
  '<div class="twscrub"><button class="playbtn" data-act="twplay" aria-label="'+esc(TW.play?twT('pause'):twT('play'))+'">'+(TW.play?'❚❚':'▶')+'</button><input type="range" id="twscrub" min="0" max="'+(rows.length-1)+'" value="'+i+'" aria-label="'+esc(twT('week'))+'"></div>'+
  '<div id="twdyn">'+twDynTop(a,i)+'</div>';
  return h+'</div>'}
var TW_SC={initial:'#7BD389',development:'#2BB3A3',mid:'#F2C14E',late:'#FFB547'};
function twLegend(rows){var seen={},ev={};rows.forEach(function(r){seen[r.stage]=1;r.events.forEach(function(e){if(e!=='ok')ev[e]=1})});
 return '<p style="font-size:.78em;color:var(--mute);margin:2px 0 8px">'+Object.keys(TW_SC).filter(function(k){return seen[k]}).map(function(k){return '<span style="white-space:nowrap"><i style="display:inline-block;width:10px;height:10px;border-radius:2px;background:'+TW_SC[k]+'"></i> '+esc(bi(TW_STAGE[k][0],TW_STAGE[k][1]))+'</span>'}).join(' · ')+(Object.keys(ev).length?' &nbsp;|&nbsp; '+Object.keys(ev).map(function(k){var x=TW_EV[k]||['#888',k,k];return '<span style="white-space:nowrap"><i style="display:inline-block;width:8px;height:8px;border-radius:50%;background:'+x[0]+'"></i> '+esc(bi(x[1],x[2]))+'</span>'}).join(' · '):'')+'</p>'}
function twDynTop(a,i){var rows=a.rows;return twStrip(rows,i)+twLegend(rows)+twWeekTile(rows[i])}
function twCh(x){return '<div class="twch">'+x+'</div>'}
function twDynCharts(a,i){var rows=a.rows;return twCh(twLine(rows,['soil'],['stroke:var(--water)'],i,twT('chSoil')))+twCh(twLine(rows,['rain','demand'],['bar','stroke:var(--gold)'],i,twT('chRain')))+twCh(twLine(rows,['tmax','tmin'],['stroke:var(--coral)','stroke:var(--water)'],i,twT('chTemp')))+'<div class="only-officer twch">'+twLine(rows,['smap'],['stroke:var(--leaf)'],i,twT('chSmap'))+(a.smapNote?'<p style="color:var(--mute);font-size:.8em">'+esc(T(a.smapNote))+'</p>':'')+'</div>'}
function twTotals(a){var h='',t=a.totals;{h+='<h4 style="margin:12px 0 6px">'+esc(twT('tot'))+'</h4><div class="twtiles">'+[['irrN',t.irrNeed],['evN',t.irrEvents],['stressN',t.stress],['rainN',t.rain],['demN',t.demand]].filter(function(x){return x[1]}).map(function(x){return '<div class="twt"><small>'+esc(twT(x[0]))+'</small><b>'+twMeas(x[1])+'</b>'+twSrc(x[1].src,a)+'</div>'}).join('')+'</div>'}
 return h}
function twRest(a){var h='';
 if(a.thresholds.length)h+='<div class="only-officer"><h4 style="margin:12px 0 6px">'+esc(twT('limits'))+'</h4><table class="twtab"><tbody>'+a.thresholds.map(function(x){return '<tr><td>'+esc(x.label?T(x.label):x.event)+'</td><td>'+(x.limit?N(x.limit.value)+' '+esc(x.limit.unit):'')+'</td><td>'+(x.span.length?esc(bi('days ','দিন '))+N(x.span[0])+'–'+N(x.span[1]):'')+'</td><td>'+(x.limit?twSrc(x.limit.src,a):'')+'</td></tr>'}).join('')+'</tbody></table></div>';
 a.notices.forEach(function(n){h+='<div class="note'+(n.level==='caution'?' warn':'')+'"><span>'+esc(T(n))+'</span></div>'});
 return h}
function twChartsHtml(){var a=TW.rep&&TW.rep.ad;if(TW.repWait||!a||!a.ok)return '';var i=Math.min(TW.week,a.rows.length-1);return '<div class="card"><h3>'+esc(bi('Season charts','মৌসুমের চার্ট'))+'</h3><div id="twcharts" class="twcharts" style="margin-bottom:0">'+twDynCharts(a,i)+'</div></div>'}
function twTotalsCard(){var a=TW.rep&&TW.rep.ad;return (!TW.repWait&&a&&a.ok&&a.totals)?'<div class="card">'+twTotals(a)+'</div>':''}
function twNotes(){var a=TW.rep&&TW.rep.ad;return (!TW.repWait&&a&&a.ok)?'<div>'+twRest(a)+'</div>':''}
function twWhatIfHtml(){
 var S=TW.scen,h='<div class="card"><h3>'+esc(twT('whatif'))+'</h3>'+
  '<div class="twctl"><label style="flex:1;min-width:150px">'+esc(twT('rain'))+': <b id="twrainv">'+(TW.rain>0?'+':'')+N(TW.rain)+'%</b><input class="twrng" type="range" id="twrain" min="-30" max="30" step="5" value="'+TW.rain+'"></label>'+
  '<label style="flex:1;min-width:150px">'+esc(twT('temp'))+': <b id="twtempv">+'+N(TW.temp)+' °C</b><input class="twrng" type="range" id="twtemp" min="0" max="2" step="0.5" value="'+TW.temp+'"></label></div>';
 return h+'<div id="twwhatres">'+twWhatRes()+'</div></div>'}
function twWhatRes(){
 var S=TW.scen,h='';
 if(!S||TW.scenWait)return '<p>'+spinner()+esc(twT('wait'))+'</p>';
 var a=S.ad;if(!a)return '<div class="note warn"><span>'+esc(s('offline'))+'</span></div>';
 if(!a.ok)return '<div class="note warn"><span>'+esc(a.errors.length?T(a.errors[0]):s('planNone'))+'</span></div>';
 var live=CS_API.isLive(S.r);
 h+=(live?'':'<div class="note warn"><span class="badge">'+esc(s('planDemo'))+'</span></div>')+'<p style="color:var(--mute);font-size:.88em">'+esc(a.label||'')+(a.nYears?' · '+N(a.nYears)+' '+esc(bi('past seasons','অতীত মৌসুম')):'')+'</p>'+
  '<table class="twtab"><thead><tr><th></th><th>'+esc(twT('base'))+'</th><th>'+esc(twT('what'))+'</th><th>'+esc(twT('chg'))+'</th></tr></thead><tbody>'+a.rows.map(function(r){var m=TW_METRIC[r.key]||[r.key,r.key,'',''];return '<tr><td>'+esc(bi(m[0],m[1]))+'</td><td>'+N(r.base)+' '+esc(bi(m[2],m[3]))+'</td><td><b>'+N(r.what)+'</b></td><td>'+(r.delta>0?'+':'')+N(r.delta)+'</td></tr>'}).join('')+'</tbody></table>'+
  '<div class="only-officer">'+(a.heat.length?'<table class="twtab"><tbody>'+a.heat.map(function(x){return '<tr><td>'+esc(x.item)+'</td><td>'+N(x.limit)+' '+esc(x.unit)+'</td><td>'+N(x.base)+'</td><td>'+N(x.what)+'</td><td>'+(x.url?'<a href="'+esc(x.url)+'" target="_blank" rel="noopener">↗</a>':'')+'</td></tr>'}).join('')+'</tbody></table>':'')+
  '<details><summary>'+esc(bi('Assumptions','ধরে নেওয়া বিষয়'))+'</summary>'+a.assumptions.map(function(x){return '<p style="font-size:.85em;color:var(--mute)">'+esc(typeof x==='string'?x:T(x))+'</p>'}).join('')+'</details></div>'+
  (a.sources.length?'<p style="font-size:.8em">'+a.sources.map(function(p){return '<a href="'+esc(p.source_url)+'" target="_blank" rel="noopener">'+esc(p.dataset)+' ↗</a>'}).join(' · ')+'</p>':'');
 return h}
function twResPaint(){var e=$('#twwhatres');if(e)e.innerHTML=twWhatRes()}
function twDynPaint(){var a=TW.rep&&TW.rep.ad;if(!a||!a.ok)return;var i=Math.min(TW.week,a.rows.length-1),d=$('#twdyn'),r=$('#twscrub');if(d)d.innerHTML=twDynTop(a,i);var ch=$('#twcharts');if(ch)ch.innerHTML=twDynCharts(a,i);if(r)r.value=i;var pb=document.querySelector('[data-act="twplay"]');if(pb)pb.textContent=TW.play?'❚❚':'▶'}
function twPaint(){var el=$('#pg-twin');if(!el||cur!=='twin')return;
 var sc=window.scrollY;el.innerHTML=twShell();twMapInit();window.scrollTo(0,sc)}
function twShell(){
 return '<div class="eyebrow">'+esc(s('nav')[4]||'Twin')+'</div><h1 style="font-size:clamp(1.5rem,5.5vw,2.1rem);margin-top:6px">'+esc(twT('h'))+'</h1><p class="lead">'+esc(twT('lead'))+'</p>'+watchBtn('twin')+
  '<div class="twrow">'+twMapHtml()+twSeasonHtml()+'</div>'+twChartsHtml()+'<div class="twrow">'+twWhatIfHtml()+'<div>'+twSoilHtml()+twTotalsCard()+'</div></div>'+twNotes()+'<p style="color:var(--mute)">'+esc(twT('notfc'))+'</p>'}
function renderTwin(){
 if(!window.CS_API||!window.CS_TW){$('#pg-twin').innerHTML='<div class="note warn"><span>'+esc(s('offline'))+'</span></div>';return}
 var lk=JSON.stringify([st.district,st.lat,st.lon]);if(TW.loc!==lk){TW.loc=lk;TW.sow='';TW.rep=null;TW.scen=null;TW.key.scen=null;TW.week=0}
 TW.ads={};twPaint();twLoad()}
/* ---- events (data-act values start with "tw", so modes.html ignores them) ---- */
document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-act^="tw"]');if(!b)return;var a=b.dataset.act,v=b.dataset.v;
 if(a==='twcrop'){TW.crop=v;TW.sow='';TW.rep=null;TW.scenSow='';TW.week=0;twPaint();twScenario(true,true)}
 else if(a==='twgo'){twReplay()}
 else if(a==='twlayer'){TW.layer=v;twPaint()}
 else if(a==='twplay'){TW.play=!TW.play;clearInterval(TW.timer);var n=TW.rep&&TW.rep.ad?TW.rep.ad.rows.length:0;
  if(TW.play&&n){if(TW.week>=n-1)TW.week=0;TW.timer=setInterval(function(){TW.week++;if(TW.week>=n-1){TW.week=n-1;TW.play=false;clearInterval(TW.timer)}twDynPaint()},700)}twDynPaint()}
 else if(a==='twsrc'){var p=v.split('|');showSources(p[1],TW.ads[p[0]])}});
document.addEventListener('input',function(e){var id=e.target.id;
 if(id==='twscrub'){TW.week=+e.target.value;clearInterval(TW.timer);TW.play=false;var a=TW.rep&&TW.rep.ad;if(a&&a.ok){twDynPaint()}}
 else if(id==='twrain'){TW.rain=+e.target.value;$('#twrainv').textContent=(TW.rain>0?'+':'')+N(TW.rain)+'%'}
 else if(id==='twtemp'){TW.temp=+e.target.value;$('#twtempv').textContent='+'+N(TW.temp)+' °C'}});
document.addEventListener('change',function(e){var id=e.target.id;
 if(id==='twrain'||id==='twtemp'){twScenario(false)}
 else if(id==='twyear'){TW.year=+e.target.value;if(TW.sow)TW.sow=TW.year+TW.sow.slice(4);twReplay()}
 else if(id==='twsow'&&e.target.value){TW.sow=e.target.value;TW.year=+TW.sow.slice(0,4);twReplay()}});

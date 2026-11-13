/* Explanations for the agriculture officer, and the Sources page (the (i) button).
   - Sources: every source the server has named in any answer this session (CS_API.prov()), with period, resolution,
     note, dataset link and a "see the satellite data" link where the server gives one. Nothing is invented here.
   - "In short" card: the server's own sentence and the result of its wording check.
   - Place line: which district point the field is nearest to, and how far.
   - Farm soil card: the server's soil answer for the field point (texture, pH, organic carbon) with its notices.
   - wvUrl(): a NASA Worldview link centred on the farmer's field (the link only opens a map; no number is computed).
   Uses globals from modes.html: st, lang, s, esc, T, N, bi, spinner, showSources, go, CS_API, CS_SOIL, $, cur. */
var OF={q:'',soil:null,soilKey:null};
(function(){var c=document.createElement('style');c.textContent='.ofsrc{padding:10px 0;border-bottom:1px solid var(--line)}.ofsrc p{margin:2px 0;color:var(--mute)}.ofsrc a{word-break:break-all}.oftiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin:8px 0}.oftile{background:rgba(255,255,255,.05);border-radius:12px;padding:10px}.oftile small{display:block;color:var(--mute)}.oftile b{font-size:1.15rem}';document.head.appendChild(c)})();

/* ---- NASA Worldview centred on the field ---- */
function wvUrl(){var d=new Date();d.setDate(d.getDate()-2);var t=d.toISOString().slice(0,10),la=+st.lat,lo=+st.lon,w=0.25;
 return 'https://worldview.earthdata.nasa.gov/?v='+(lo-w).toFixed(3)+','+(la-w*0.8).toFixed(3)+','+(lo+w).toFixed(3)+','+(la+w*0.8).toFixed(3)+'&l=Reference_Labels_15m,Reference_Features_15m,Coastlines_15m,VIIRS_SNPP_CorrectedReflectance_TrueColor&t='+t}

/* ---- the (i) page ---- */
function ofGroup(p){var a=(p.agency||'')+' '+(p.dataset||'');return /^\s*NASA|NASA /i.test(a)?0:(/map picture/i.test(a)?3:(/FAO|Survey Crops/i.test(a)?1:2))}
function renderSourcesPage(){
 var list=(CS_API.prov?CS_API.prov():[]).slice();
 var q=OF.q.trim().toLowerCase();
 if(q)list=list.filter(function(p){return ((p.dataset||'')+' '+(p.agency||'')+' '+(p.note||'')).toLowerCase().indexOf(q)>=0});
 list.sort(function(a,b){return ofGroup(a)-ofGroup(b)});
 var head=['<span>NASA</span>',bi('Methods and Survey Crops analysis','পদ্ধতি ও সার্ভে ক্রপস বিশ্লেষণ'),bi('Research papers and reference tables','গবেষণাপত্র ও রেফারেন্স তালিকা'),bi('Map pictures (not data)','মানচিত্রের ছবি (ডেটা নয়)')];
 var h='<div class="eyebrow">'+esc(s('srcl'))+'</div><h1 style="font-size:clamp(1.5rem,5.5vw,2.1rem);margin-top:6px">'+esc(s('src'))+'</h1><p class="lead">'+esc(bi('Every number in Survey Crops links to one of these sources. This list comes from the server with each answer.','সার্ভে ক্রপসের প্রতিটি সংখ্যা এই উৎসগুলোর একটির সঙ্গে যুক্ত। এই তালিকা প্রতিটি উত্তরের সঙ্গে সার্ভার থেকে আসে।'))+'</p>';
 h+='<p><a class="chip" style="text-decoration:none;color:var(--water)" target="_blank" rel="noopener" href="'+esc(wvUrl())+'">NASA Worldview ↗ '+esc(bi('(your field)','(আপনার জমি)'))+'</a></p>';
 if(!list.length&&!q){h+='<div class="card"><p>'+spinner()+esc(s('planWait'))+'</p></div>';ofWarm()}
 else{
  h+='<input type="search" id="ofq" placeholder="'+esc(bi('Search sources','উৎস খুঁজুন'))+'" value="'+esc(OF.q)+'" style="width:100%;margin:6px 0;padding:10px;border-radius:10px;border:1px solid var(--line);background:rgba(255,255,255,.05);color:inherit"><p style="color:var(--mute)">'+N(list.length)+' '+esc(bi('sources','উৎস'))+'</p>';
  var g=-1;list.forEach(function(p){var k=ofGroup(p);if(k!==g){if(g>=0)h+='</div>';g=k;h+='<h3>'+head[k]+'</h3><div class="card">'}
   var u=p.url||p.source_url||'';
   h+='<div class="ofsrc"><b>'+esc(p.dataset||p.id||'')+'</b>'+(p.agency?'<p>'+esc(p.agency)+(p.period?' · '+esc(bi('Period','সময়কাল'))+': '+esc(p.period):'')+(p.resolution?' · '+esc(bi('Resolution','রেজোলিউশন'))+': '+esc(p.resolution):'')+'</p>':(p.period?'<p>'+esc(bi('Period','সময়কাল'))+': '+esc(p.period)+'</p>':''))+
    (p.note?'<p>'+esc(p.note)+'</p>':'')+'<p>'+(u?'<a href="'+esc(u)+'" target="_blank" rel="noopener">'+esc(bi('Dataset page','ডেটাসেট পাতা'))+' ↗</a>':'<span>'+esc(bi('Link pending','লিংক পরে যোগ হবে'))+'</span>')+(p.view_url?' · <a href="'+esc(p.view_url)+'" target="_blank" rel="noopener">'+esc(bi('See the satellite data','স্যাটেলাইট ডেটা দেখুন'))+' ↗</a>':'')+'</p></div>'});
  if(g>=0)h+='</div>'}
 h+='<div class="only-officer"><h2>'+esc(s('method'))+'</h2><div class="card"><p>'+esc(s('methodT'))+'</p></div></div><h2>'+esc(lang==='bn'?'সীমাবদ্ধতা':'Limits')+'</h2><div class="card">'+s('lim').map(function(x){return '<div class="note warn" style="margin:6px 0"><span>'+esc(x)+'</span></div>'}).join('')+'<p style="margin:10px 0 0;font-size:.85em;color:var(--mute)">'+esc(lang==='bn'?'ভয়েস: ElevenLabs (এআই-তৈরি কণ্ঠস্বর)':'Voice: ElevenLabs (AI-generated voices)')+'</p></div>';
 h+=(window.moreCard?moreCard():'');$('#pg-sources').innerHTML=h;
 var q2=document.getElementById('ofq');if(q2)q2.addEventListener('input',function(){OF.q=q2.value;var pos=q2.selectionStart;renderSourcesPage();var n=document.getElementById('ofq');if(n){n.focus();n.setSelectionRange(pos,pos)}})}
/* the list fills as answers arrive; ask for the ones that carry the most sources so the page is never empty */
function ofWarm(){if(OF.warm)return;OF.warm=true;CS_API.get('/api/v1/districts');CS_API.get('/api/v1/data/sources');if(window.liveLoad)liveLoad()}
if(window.CS_API)CS_API.on(function(ev){if(ev.type==='end'&&typeof cur!=='undefined'&&cur==='sources'&&!document.activeElement.matches('#ofq'))renderSourcesPage()});

/* ---- "In short" and the place line, for answers that carry them ---- */
function shortCard(ad){var n=ad&&ad.narration;if(!n||!(n[lang]||n.en))return '';
 var ok=n.check==='passed';
 return '<div class="card gold" style="margin:8px 0"><div style="color:var(--mute);font-size:.8em;text-transform:uppercase;letter-spacing:.04em">'+esc(bi('In short','সংক্ষেপে'))+(ok?' · '+esc(bi('every number checked against its source','প্রতিটি সংখ্যা তার উৎসের সঙ্গে মিলিয়ে দেখা'))+' ✓':'')+'</div><p style="margin:6px 0 0">'+esc(n[lang]||n.en)+'</p>'+(n.check&&!ok?'<p style="color:var(--amber);font-size:.85em">'+esc(bi('The wording check did not pass, so this is the plain template sentence.','ভাষা যাচাই পাস করেনি, তাই এটি সাধারণ ছক-বাক্য।'))+'</p>':'')+'<span class="only-officer" style="font-size:.8em;color:var(--mute)">'+esc((n.narrator||'')+' · '+(n.check||''))+'</span></div>'}
function placeLine(ad,srcFn){var l=ad&&ad.location;if(!l)return '';var nm=l.district_name?T(l.district_name):l.district,d=l.distance_km;
 return '<p style="color:var(--mute);margin:4px 0">'+esc(bi('District for your location','আপনার অবস্থানের জেলা'))+': <b>'+esc(nm||'')+'</b>'+(d&&d.value!=null?' · '+N(d.value)+' '+esc(bi('km to the district point','কিমি জেলার বিন্দু থেকে')):'')+' '+(srcFn&&d&&d.src?srcFn(d.src):'')+'</p>'+(l.method?'<p style="color:var(--mute);font-size:.85em;margin:0 0 6px">'+esc(T(l.method))+'</p>':'')}

/* ---- the soil card on the Farm page ---- */
function farmSoilLoad(){var k=JSON.stringify([st.district,st.lat,st.lon]);if(OF.soilKey===k)return;OF.soilKey=k;OF.soil=null;
 CS_API.get('/api/v1/soil?district='+st.district+'&lat='+st.lat+'&lon='+st.lon).then(function(r){if(OF.soilKey!==k)return;OF.soil={r:r,ad:r.data?CS_SOIL.adapt(r.data):null};var e=document.getElementById('farmsoil');if(e)e.innerHTML=farmSoilInner()})}
function farmSoilInner(){var S=OF.soil;if(!S)return '<p>'+spinner()+esc(s('planWait'))+'</p>';var a=S.ad;if(!a)return '<div class="note warn"><span>'+esc(s('offline'))+'</span></div>';if(!a.ok)return '<div class="note warn"><span>'+esc(a.errors&&a.errors.length?T(a.errors[0]):s('planNone'))+'</span></div>';
 var live=CS_API.isLive(S.r),na='<span style="color:var(--mute)">'+esc(bi('not available for this point','এই বিন্দুর জন্য পাওয়া যায়নি'))+'</span>';
 function tile(l,v){return '<div class="oftile"><small>'+esc(l)+'</small><b>'+v+'</b></div>'}
 function mm(m){return m?N(m.value)+' '+esc(m.unit):na}
 var h=(live?'':'<div class="note warn"><span class="badge">'+esc(s('planDemo'))+'</span></div>')+'<div class="oftiles">'+tile(bi('Texture','মাটির ধরন'),a.texture?esc(T(a.texture)):na)+tile(bi('Soil acidity (pH)','মাটির অম্লতা (pH)'),mm(a.ph))+tile(bi('Organic carbon','জৈব কার্বন'),mm(a.oc))+'</div>';
 if(a.estimate)h+='<p style="color:var(--mute);font-size:.85em">'+esc(a.estimate==='field'?bi('SoilGrids model estimate for this point, not a lab test.','এই বিন্দুর জন্য SoilGrids মডেলের অনুমান, ল্যাব পরীক্ষা নয়।'):bi('District soil values (SoilGrids did not answer or has no value here).','জেলার মাটির মান (SoilGrids উত্তর দেয়নি বা এখানে মান নেই)।'))+(a.depth?' ('+esc(String(a.depth))+')':'')+'</p>';
 a.notices.forEach(function(n){h+='<div class="note'+(n.level==='caution'?' warn':'')+'"><span>'+esc(T(n))+'</span></div>'});
 if(a.advice)h+='<p>'+esc(T(a.advice))+'</p>';
 return h}
function farmSoilCard(){farmSoilLoad();return '<div class="card"><h3>'+esc(bi('Your soil','আপনার মাটি'))+'</h3><div id="farmsoil">'+farmSoilInner()+'</div></div>'}

/* Weather-warning and El Nino context cards (on the Issues page). They draw what /api/v1/warnings and
   /api/v1/enso-lens return. Nothing is worked out here. Both server answers are currently marked example data,
   so the DEMO badge stays on (a screen is "live" only for a real, non-mock answer). El Nino context is past seasons.
   Uses globals from modes.html: st, lang, s, esc, T, N, bi, iso2d, spinner, showSources, CS_API, RK; adapters CS_WN, CS_EN. */
var OL={wn:{key:null,res:null,ad:null,wait:false},en:{key:null,res:null,ad:null,wait:false}};
var OL_TYPE={heavy_rain:['Heavy rain','ভারী বৃষ্টি'],heat:['Hot weather','গরম আবহাওয়া'],cold:['Cold weather','ঠান্ডা আবহাওয়া'],strong_wind:['Strong wind','জোর বাতাস'],hail:['Hail','শিলাবৃষ্টি'],fog:['Fog','কুয়াশা']};
var OL_MET={rabi_rain:['Rain in the dry (rabi) season','রবি মৌসুমের বৃষ্টি'],mustard_irrigation_need:['Mustard: irrigation needed','সরিষা: সেচ লাগে'],wheat_irrigation_need:['Wheat: irrigation needed','গম: সেচ লাগে'],potato_irrigation_need:['Potato: irrigation needed','আলু: সেচ লাগে'],lentil_irrigation_need:['Lentil: irrigation needed','মসুর: সেচ লাগে']};
function olLabel(map,k){var m=map[k];return m?bi(m[0],m[1]):String(k||'').replace(/_/g,' ')}
function olSrc(w,ids){var a=OL[w].ad;if(!a||!ids||!ids.length)return '';return '<button class="src" data-act="olsrc" data-v="'+w+'|'+esc(ids.join(','))+'">'+bi('Source','উৎস')+' ›</button>'}
function olMeas(m){return m?N(m.value)+' '+esc(m.unit):'<span style="color:var(--mute)">'+esc(bi('not assessed','মূল্যায়ন হয়নি'))+'</span>'}
function olDay(iso){return iso?iso2d(iso):''}
function olLoad(){
 var dk=st.district,crop=(window.RK&&RK.crop)||'mustard';
 [['wn','/api/v1/warnings?district='+dk,CS_WN,dk],['en','/api/v1/enso-lens?district='+dk+'&crop='+crop,CS_EN,dk+'|'+crop]].forEach(function(x){
  var w=x[0],o=OL[w];if(o.key===x[3]&&(o.wait||o.ad))return;o.key=x[3];o.wait=true;o.ad=null;o.res=null;olPaint(w);
  CS_API.get(x[1]).then(function(r){if(o.key!==x[3])return;o.wait=false;o.res=r;o.ad=r.data?x[2].adapt(r.data):null;olPaint(w)})})}
function olPaint(w){var e=document.getElementById('ol'+w);if(e)e.innerHTML=olInner(w)}
function olHead(o){var live=CS_API.isLive(o.res);return '<div class="note warn" style="margin:6px 0"><span class="badge">'+esc(live?s('planLive'):s('planDemo'))+'</span></div>'}
/* a server notice that uses the banned word (other than the "not a forecast" disclaimer) is replaced by a plain line */
function olOk(x){var t=(x.en||'')+' '+(x.bn||'');return !/forecast|predict/i.test(t.replace(/not a forecast/ig,''))}
function olNotices(a,w){var h=a.notices.filter(olOk).map(function(x){return '<div class="note'+(x.level==='caution'?' warn':'')+'"><span>'+esc(T(x))+'</span></div>'}).join('');
 if(w==='wn'&&a.notices.some(function(x){return !olOk(x)}))h+='<div class="note"><span>'+esc(bi('Weather data is from Open-Meteo, not NASA.','আবহাওয়ার তথ্য Open-Meteo থেকে, NASA নয়।'))+'</span></div>';return h}
function olInner(w){
 var o=OL[w];if(o.wait)return '<p>'+spinner()+esc(s('planWait'))+'</p>';
 var a=o.ad;if(!a)return '<div class="note warn"><span>'+esc(s('offline'))+'</span></div>';
 if(!a.ok)return '<div class="note warn"><span>'+esc(a.errors.length?T(a.errors[0]):s('planNone'))+'</span></div>';
 return w==='wn'?olWarn(a,o):olEnso(a,o)}
function olWarn(a,o){
 var h=olHead(o)+olNotices(a,'wn');
 if(a.from)h+='<p style="color:var(--mute);margin:4px 0">'+esc(bi('Weather for','আবহাওয়া'))+' '+olDay(a.from)+' – '+olDay(a.to)+'</p>';
 if(!a.items.length)return h+'<p>'+esc(bi('The server lists no weather warnings for these days.','এই দিনগুলোর জন্য সার্ভার কোনো আবহাওয়া সতর্কতা দেয়নি।'))+'</p>';
 a.items.forEach(function(i){var src=(i.expected?i.expected.src:[]).concat(i.threshold?i.threshold.src:[]);
  h+='<div class="card" style="margin:8px 0"><h4 style="margin:0 0 4px">'+esc(olLabel(OL_TYPE,i.type))+' · '+olDay(i.date)+'</h4>'+
   '<p style="margin:2px 0">'+esc(bi('Expected','প্রত্যাশিত'))+': <b>'+olMeas(i.expected)+'</b> · '+esc(bi('warning limit','সতর্কতার সীমা'))+': <b>'+olMeas(i.threshold)+'</b> '+olSrc('wn',src)+'</p>'+
   (i.action?'<p style="margin:4px 0 0">'+esc(T(i.action))+'</p>':'')+'</div>'});
 return h}
function olEnso(a,o){
 var h=olHead(o)+olNotices(a,'en');
 if(a.phase)h+='<p>'+esc(bi('Now','এখন'))+': <b>'+esc(a.phase)+'</b>'+(a.nino34?' · Niño 3.4: <b>'+olMeas(a.nino34)+'</b> '+olSrc('en',a.nino34.src):'')+'</p>';
 if(a.rows.length){h+='<div class="rkbox"><table class="rktab"><thead><tr><th class="rkh"></th><th>'+esc(bi('All years','সব বছর'))+'</th><th>'+esc(bi('El Niño years','এল নিনো বছর'))+'</th><th>'+esc(bi('Number of El Niño years','এল নিনো বছরের সংখ্যা'))+'</th></tr></thead><tbody>';
  a.rows.forEach(function(r){h+='<tr><th class="rkh">'+esc(olLabel(OL_MET,r.metric))+'</th><td class="num" style="white-space:nowrap">'+olMeas(r.all)+(r.all?' '+olSrc('en',r.all.src):'')+'</td><td class="num" style="white-space:nowrap">'+olMeas(r.nino)+(r.nino?' '+olSrc('en',r.nino.src):'')+'</td><td class="num" style="white-space:nowrap">'+olMeas(r.n)+'</td></tr>'});
  h+='</tbody></table></div>'}
 if(a.years&&a.years.list.length)h+='<p style="color:var(--mute);font-size:.85em;margin:6px 0 0">'+esc(bi('El Niño years used','যে এল নিনো বছর ব্যবহৃত'))+': '+a.years.list.map(N).join(', ')+' '+olSrc('en',a.years.src)+'</p>';
 h+='<p style="color:var(--mute);font-size:.85em;margin:4px 0 0">'+esc(a.usedInRanking?bi('Used in the ranking.','র‍্যাঙ্কিংয়ে ব্যবহৃত।'):bi('Context only. Not used in the ranking.','শুধু প্রেক্ষাপট। র‍্যাঙ্কিংয়ে ব্যবহৃত হয়নি।'))+'</p>';
 if(a.narration&&a.narration[lang])h+='<p>'+esc(a.narration[lang])+'</p>';
 return h}
function outlookCards(){OL.wn.key=null;OL.en.key=null;
 return '<div class="card"><h3>'+esc(bi('Weather warnings for the next days','আগামী দিনের আবহাওয়া সতর্কতা'))+(window.voiceBtn?voiceBtn('page-warnings'):'')+'</h3><div id="olwn">'+olInner('wn')+'</div></div>'+
  '<div class="card"><h3>'+esc(bi('El Niño years: context','এল নিনো বছর: প্রেক্ষাপট'))+(window.voiceBtn?voiceBtn('page-enso'):'')+'</h3><p style="color:var(--mute);margin:0">'+esc(bi('Based on past seasons. Not a forecast.','অতীতের মৌসুমের ভিত্তিতে। পূর্বাভাস নয়।'))+'</p><div id="olen">'+olInner('en')+'</div></div>'}
document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-act="olsrc"]');if(!b)return;var p=b.dataset.v.split('|');showSources(p[1],OL[p[0]].ad)});
(function(){var c=document.createElement('style');c.textContent='.rktab .src{white-space:nowrap;display:inline-block}';document.head.appendChild(c)})();

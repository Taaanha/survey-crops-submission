/* Desktop | Phone view switch, always in the top bar.
   - On a wide screen: "Desktop" is on; "Phone" opens the same page inside a phone-sized frame (390 x 844). The frame is a
     real phone-width window, so the phone layout (bottom bar, one column) is the real one, not a mock-up.
   - On a narrow screen (a phone): "Phone" is on; "Desktop" asks the browser for the wide layout (viewport width 1100) and
     remembers it for this tab; "Phone" there switches back.
   Inside the phone frame the switch is hidden. The frame copies the current language, mode and page.
   Uses globals from modes.html: lang, st. */
(function(){
 var inFrame=/[?&]frame=1/.test(location.search);
 var forced=false;try{forced=sessionStorage.getItem('csdesk')==='1'}catch(e){}
 var meta=document.querySelector('meta[name="viewport"]');
 if(forced&&meta)meta.setAttribute('content','width=1100');
 var c=document.createElement('style');c.textContent=
  '#viewSeg{display:inline-flex}#viewSeg button{display:inline-flex;align-items:center;gap:5px;white-space:nowrap}#viewSeg svg{width:17px;height:17px;flex:none}'+
  '@media(max-width:520px){#viewSeg button span{display:none}#viewSeg button{padding:0 9px}}'+
  '#phoneov{position:fixed;inset:0;z-index:9000;background:rgba(3,10,16,.86);display:none;align-items:center;justify-content:center;flex-direction:column;gap:10px}#phoneov.on{display:flex}'+
  '#phoneov .dev{width:min(410px,92vw);height:min(864px,calc(100vh - 70px));border-radius:38px;border:10px solid #101c24;box-shadow:0 0 0 2px #2c3d49,0 30px 80px rgba(0,0,0,.6);overflow:hidden;background:#000}'+
  '#phoneov iframe{width:100%;height:100%;border:0;display:block;background:#0B2630}#phoneov .x{align-self:center}'+
  (inFrame?'#viewSeg{display:none!important}':'');
 document.head.appendChild(c);
 function isWide(){return window.innerWidth>=900}
 function ico(kind){return kind==='d'?'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg>':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2.5" width="10" height="19" rx="2.5"/><path d="M11 18.5h2"/></svg>'}
 function bn(){return typeof lang!=='undefined'&&lang==='bn'}
 function paint(){var d=document.getElementById('vDesk'),p=document.getElementById('vPhone');if(!d||!p)return;
  var wide=isWide();d.className=wide?'on':'';p.className=wide?'':'on';
  d.innerHTML=ico('d')+'<span>'+(bn()?'ডেস্কটপ':'Desktop')+'</span>';p.innerHTML=ico('p')+'<span>'+(bn()?'ফোন':'Phone')+'</span>';
  d.setAttribute('aria-label',bn()?'ডেস্কটপ দেখা':'Desktop view');p.setAttribute('aria-label',bn()?'ফোনে দেখা':'Phone view')}
 function ready(fn){if(document.readyState!=='loading')fn();else document.addEventListener('DOMContentLoaded',fn)}
 ready(function(){
  var hdr=document.querySelector('header.top');
  if(hdr&&!inFrame){var s=document.createElement('div');s.className='seg';s.id='viewSeg';s.setAttribute('role','group');s.setAttribute('aria-label','View');
   s.innerHTML='<button id="vDesk" data-act="viewdesk"></button><button id="vPhone" data-act="viewphone"></button>';
   hdr.insertBefore(s,hdr.querySelector('[data-act="speak"]')||null);paint()}
  if(inFrame){ /* copy language and mode from the parent page once the app has drawn */
   var q=new URLSearchParams(location.search),L=q.get('lang'),M=q.get('mode');setTimeout(function(){
    if(L&&typeof lang!=='undefined'&&lang!==L){var l=document.querySelector('[data-act="lang"][data-v="'+L+'"]');l&&l.click()}
    if(M&&typeof st!=='undefined'&&st.mode!==M){var m=document.getElementById('modeBtn');m&&m.click()}},400)}
 });
 function openFrame(){
  var ov=document.getElementById('phoneov');
  if(!ov){ov=document.createElement('div');ov.id='phoneov';ov.innerHTML='<div class="dev"><iframe title="Phone view"></iframe></div><button class="btn sm x" data-act="phoneclose"></button>';document.body.appendChild(ov)}
  var q=new URLSearchParams(location.search);q.set('frame','1');q.set('lang',typeof lang!=='undefined'?lang:'en');q.set('mode',(typeof st!=='undefined'&&st.mode)||'farmer');
  ov.querySelector('iframe').src=location.pathname+'?'+q.toString()+location.hash;
  ov.querySelector('.x').textContent=bn()?'বন্ধ করুন (ডেস্কটপ দেখুন)':'Close (back to desktop view)';
  ov.classList.add('on')}
 function closeFrame(){var ov=document.getElementById('phoneov');if(ov){ov.classList.remove('on');ov.querySelector('iframe').src='about:blank'}}
 function setForced(v){try{if(v)sessionStorage.setItem('csdesk','1');else sessionStorage.removeItem('csdesk')}catch(e){}location.reload()}
 document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-act="viewdesk"],[data-act="viewphone"],[data-act="phoneclose"]');if(!b)return;var a=b.dataset.act;
  if(a==='phoneclose')closeFrame();
  else if(a==='viewphone'){if(forced)setForced(false);else if(window.innerWidth>=900)openFrame()}
  else if(a==='viewdesk'){if(window.innerWidth<900&&!forced)setForced(true);else closeFrame()}});
 document.addEventListener('keydown',function(e){if(e.key==='Escape')closeFrame()});
 setInterval(paint,800);
})();

/* Crops the server left out of the Rotation list, shown as cards instead of one plain line.
   - "Sowing time has passed" (window_status.code = closed): the crop, the server's own sentence and its cited sowing window.
     No risk number is shown for it, because the server does not compute one for a sowing date this far past the window.
   - Any other reason (for example "no sourced risk yet"): officer view only, as the server's text.
   When fewer than three crops fit, a note points to "Other ways to rotate", which always compares five full rotations.
   Uses globals from modes.html: s, esc, T, bi, iso2d, lsrc, art, CROPS, demoKey, st. */
function closedCard(o){
 var cur_=CROPS[st.current]||{a:'sow',n:{en:'',bn:''}};
 var h='<div class="card strat"><div class="chain"><span class="step">'+art(cur_.a,32)+esc(T(cur_.n))+'</span><span class="arr">→</span><span class="step">'+art((CROPS[demoKey(o.id)]||{a:'sow'}).a,32)+esc(T(o.name))+'</span></div>'+
  '<div style="margin:10px 0"><span class="badge blue">'+esc(bi('Not this season','এই মৌসুমে নয়'))+'</span></div>';
 if(o.status)h+='<p>'+esc(T(o.status))+'</p>';
 if(o.window)h+='<p style="color:var(--mute)">'+esc(bi('Recommended sowing window','সুপারিশকৃত বপনের সময়'))+': <b>'+iso2d(o.window.start)+' – '+iso2d(o.window.end)+'</b> '+lsrc(o.window.src)+'</p>';
 return h+'</div>'}
function closedCards(ad){
 var all=ad.filtered||[],closed=all.filter(function(o){return o.status&&o.status.code==='closed'}),other=all.filter(function(o){return !(o.status&&o.status.code==='closed')}),h='';
 if(ad.options.length<3)h+='<div class="note warn"><span>'+esc(bi('Fewer than three crops fit this harvest date. The crops below are past their sowing window. You can also compare five full rotations.','এই ফসল কাটার তারিখে তিনটির কম ফসল মানাচ্ছে। নিচের ফসলগুলোর বপনের সময় পেরিয়ে গেছে। আপনি পাঁচটি পূর্ণ ফসলক্রমও তুলনা করতে পারেন।'))+'</span> <button class="pill" data-act="go" data-v="strategies">'+esc(bi('Compare','তুলনা'))+'</button></div>';
 if(closed.length)h+='<h3>'+esc(bi('Sowing time has passed this season','এই মৌসুমে বপনের সময় পেরিয়ে গেছে'))+'</h3><div class="strats">'+closed.map(closedCard).join('')+'</div>';
 if(other.length)h+='<div class="only-officer"><h3>'+esc(s('planNo'))+'</h3>'+other.map(function(o){return '<p><b>'+esc(T(o.name))+'</b>'+(o.reason?': '+esc(T(o.reason)):'')+'</p>'}).join('')+'</div>';
 return h}

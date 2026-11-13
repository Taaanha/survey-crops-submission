/* A cited market price line, shared by the Rotation and Strategies pages. Draws what the server sent:
   the price, its month, a Source button, "a price, not income per hectare", and "past prices: not assessed".
   Nothing is worked out here and no price is ever shown as 0. Officers also see the market and price type.
   Uses globals from modes.html: esc, bi, N, T, lang, MON. */
function csPriceMonth(asOf){
 var m=/^(\d{4})-(\d{2})/.exec(asOf||'');if(!m)return '';
 return MON[lang][+m[2]-1]+' '+N(m[1])}
function csPriceHtml(p,srcHtml){
 if(!p)return '';
 if(p.na)return '<p class="pricel" style="margin:6px 0;color:var(--mute)">'+esc(bi('Market price','বাজার দাম'))+': '+esc(bi('not assessed','মূল্যায়ন হয়নি'))+'</p>';
 var when=csPriceMonth(p.asOf),
     h='<p class="pricel" style="margin:6px 0"><span style="color:var(--mute)">'+esc(bi('Market price','বাজার দাম'))+':</span> <b>'+N(p.value)+' '+esc(p.unit)+'</b>'
      +(when?' <span style="color:var(--mute)">('+esc(bi('reported','প্রতিবেদন'))+' '+esc(when)+')</span>':'')+' '+(srcHtml||'')
      +'<br><span style="color:var(--mute);font-size:.85em">'+esc(p.label?T(p.label):bi('a price, not income per hectare','এটি একটি দাম, হেক্টর প্রতি আয় নয়'))+'</span>'
      +'<br><span class="only-officer" style="color:var(--mute);font-size:.85em">'+esc(bi('Past prices','আগের দাম'))+': '+esc(bi('not assessed','মূল্যায়ন হয়নি'))+'</span>'
      +'<span class="only-officer" style="display:block;color:var(--mute);font-size:.85em">'
      +esc(bi('Price type','দামের ধরন'))+': '+esc(p.type||'')+(p.variant?' ('+esc(String(p.variant).replace(/_/g,' '))+')':'')
      +' · '+esc(bi('Market','বাজার'))+': '+esc(p.market||'')+' · '+esc(bi('Saved copy, not live','সংরক্ষিত কপি, সরাসরি নয়'))
      +(p.caveat?'<br>'+esc(p.caveat):'')+'</span></p>';
 return h}

/* "Market prices" at a glance on the Rotation page: only the options the server gave a cited price for.
   Each line is the server's price with its month and a Source button. A price, not income per hectare. */
function priceStrip(ad){var rows=(ad.options||[]).filter(function(o){return o.price&&!o.price.na});if(!rows.length)return '';
 return '<div class="card"><h3>'+esc(bi('Market prices','বাজার দাম'))+'</h3>'+rows.map(function(o){var p=o.price,when=csPriceMonth(p.asOf);
  return '<p style="margin:6px 0"><b>'+esc(T(o.name))+'</b>: '+N(p.value)+' '+esc(p.unit)+(p.type?' <span style="color:var(--mute)">('+esc(p.type)+(when?', '+esc(when):'')+')</span>':(when?' <span style="color:var(--mute)">('+esc(when)+')</span>':''))+' '+lsrc(p.src)+'</p>'}).join('')+
  '<p style="color:var(--mute);font-size:.85em;margin:6px 0 0">'+esc(bi('A price, not income per hectare. Not a forecast of future prices.','এটি একটি দাম, হেক্টর প্রতি আয় নয়। ভবিষ্যতের দামের পূর্বাভাস নয়।'))+'</p></div>'}

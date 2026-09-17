(function(){
 const set=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=Number.isFinite(Number(v))?Number(v).toLocaleString():'—'};
 function renderLeaders(data){
  const render=(id,rows)=>{
    const el=document.getElementById(id);
    if(!el)return;
    if(!Array.isArray(rows)||!rows.length){el.innerHTML='<div class="pota-leader-empty">Leaderboard data is temporarily unavailable.</div>';return;}
    el.innerHTML=rows.slice(0,5).map((r,i)=>{
      const call=String(r.callsign||r.activeCallsign||'').toUpperCase();
      const value=Number(r.count ?? r.totalQSOs ?? 0);
      const cls=call==='K5KAZ'?'pota-leader-call is-you':'pota-leader-call';
      return '<div class="pota-leader-row"><span class="pota-leader-rank">'+(i+1)+'.</span><span class="'+cls+'">'+call+'</span><span class="pota-leader-value">'+(Number.isFinite(value)?value.toLocaleString():'—')+'</span></div>';
    }).join('');
  };
  const lb=data&&data.parkLeaders?data.parkLeaders:{};
  render('pota-leaders-activations',lb.activations);
  render('pota-leaders-qsos',lb.activator_qsos);
 }
 function renderLiveLeaders(){
  const render=(id,rows)=>{
    const el=document.getElementById(id); if(!el)return;
    if(!Array.isArray(rows)||!rows.length){el.innerHTML='<div class="pota-leader-empty">Leaderboard data is temporarily unavailable.</div>';return;}
    el.innerHTML=rows.slice(0,5).map((r,i)=>{
      const call=String(r.callsign||r.activeCallsign||'').toUpperCase();
      const value=Number(r.count ?? r.totalQSOs ?? 0);
      const cls=call==='K5KAZ'?'pota-leader-call is-you':'pota-leader-call';
      return '<div class="pota-leader-row"><span class="pota-leader-rank">'+(i+1)+'.</span><span class="'+cls+'">'+call+'</span><span class="pota-leader-value">'+(Number.isFinite(value)?value.toLocaleString():'—')+'</span></div>';
    }).join('');
  };
  fetch('https://api.pota.app/park/leaderboard/US-1928?count=5',{cache:'no-store'})
    .then(r=>{if(!r.ok)throw Error('Leaderboard request failed');return r.json()})
    .then(d=>{
      const lb=d&&d.leaderboard?d.leaderboard:d;
      render('pota-leaders-activations',lb&&lb.activations);
      render('pota-leaders-qsos',lb&&lb.activator_qsos);
    })
    .catch(()=>{
      fetch('https://api.pota.app/park/activations/US-1928?count=all',{cache:'no-store'})
        .then(r=>{if(!r.ok)throw Error('Activation history request failed');return r.json()})
        .then(d=>{
          const history=Array.isArray(d)?d:(Array.isArray(d&&d.activations)?d.activations:[]);
          const a={},q={};
          history.forEach(x=>{
            const c=String(x.activeCallsign||x.callsign||'').trim().toUpperCase();
            if(!c)return;
            a[c]=(a[c]||0)+1;
            q[c]=(q[c]||0)+Number(x.totalQSOs||0);
          });
          const activations=Object.entries(a).map(([callsign,count])=>({callsign,count})).sort((x,y)=>y.count-x.count||x.callsign.localeCompare(y.callsign));
          const qsos=Object.entries(q).map(([callsign,count])=>({callsign,count})).sort((x,y)=>y.count-x.count||x.callsign.localeCompare(y.callsign));
          render('pota-leaders-activations',activations);
          render('pota-leaders-qsos',qsos);
        })
        .catch(()=>{render('pota-leaders-activations',[]);render('pota-leaders-qsos',[]);});
    });
 }
 function map(parks){const el=document.getElementById('pota-map');if(!el||typeof L==='undefined')return;const m=L.map(el,{scrollWheelZoom:false}).setView([35.5,-96],4);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap contributors'}).addTo(m);const b=[];const icon=L.divIcon({className:'pota-map-marker',html:'<span style="display:block;width:14px;height:14px;border-radius:50%;background:#ff7626;border:2px solid #fff;box-shadow:0 1px 5px rgba(0,0,0,.55)"></span>',iconSize:[18,18],iconAnchor:[9,9]});(Array.isArray(parks)?parks:[]).forEach(p=>{const lat=Number(p.lat),lon=Number(p.lon);if(!Number.isFinite(lat)||!Number.isFinite(lon))return;b.push([lat,lon]);const esc=s=>String(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));L.marker([lat,lon],{icon}).addTo(m).bindPopup('<strong>'+esc(p.name||p.reference)+'</strong><br>'+esc(p.reference||''));});if(b.length)m.fitBounds(b,{padding:[30,30],maxZoom:7})}
 fetch('data/pota.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('POTA data unavailable');return r.json()}).then(d=>{const s=d.stats||{};renderLeaders(d);renderLiveLeaders();set('pota-activations',s.activations);set('pota-parks',s.parks);set('pota-qsos',s.qsos);set('pota-states',s.states);const u=document.getElementById('pota-updated');if(u)u.textContent=d.updatedAt?'Last updated: '+new Date(d.updatedAt).toLocaleString()+' • Source: POTA public API':'Waiting for current POTA data…';map(d.parks||[])}).catch(()=>{const u=document.getElementById('pota-updated');if(u)u.textContent='Current POTA data will appear after the automatic update runs.';map([])});
})();

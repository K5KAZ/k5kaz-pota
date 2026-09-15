const CALLSIGN="K5KAZ";
const DATA_URL="data/pota.json";

const $=id=>document.getElementById(id);
const fmt=v=>Number.isFinite(Number(v))?Number(v).toLocaleString():"—";
function first(o,keys){for(const k of keys){if(o&&o[k]!==undefined&&o[k]!==null)return o[k]}return null}
function normalize(data){
  const s=data?.stats||data||{};
  return {
    activations:first(s,["activations","activationCount","totalActivations","activatorActivations"]),
    parks:first(s,["parks","parkCount","uniqueParks","uniqueParksActivated","activatorParks"]),
    qsos:first(s,["qsos","qsoCount","totalQsos","totalQSOs","activatorQsos"]),
    states:first(s,["states","stateCount","uniqueStates"]),
    activationsList:Array.isArray(data?.activationsList)?data.activationsList:(Array.isArray(s?.activations)?s.activations:[])
  }
}
function render(data){
  const n=normalize(data);
  $("activations-stat").textContent=fmt(n.activations);
  $("parks-stat").textContent=fmt(n.parks);
  $("qsos-stat").textContent=fmt(n.qsos);
  $("states-stat").textContent=fmt(n.states);

  const list=$("activation-list");
  if(!n.activationsList.length){
    list.innerHTML=`<div class="notice">POTA statistics are connected, but the current public response does not expose recent activation rows in the cached shape yet. The data updater is ready for the activation-history fields when available.</div>`;
  }else{
    list.innerHTML=n.activationsList.slice(0,8).map(a=>{
      const ref=a.reference||a.parkReference||a.ref||"POTA";
      const name=a.parkName||a.name||a.locationName||"Park";
      const date=a.date||a.activationDate||a.qso_date||"";
      const qsos=Number(a.qsos??a.qsoCount??a.total??a.contacts??0);
      return `<article class="activation"><div class="thumb">▲</div><div><h4>${esc(ref)} — ${esc(name)}</h4><p>${esc(date)}</p><p>POTA activation</p></div><div class="qso">${qsos.toLocaleString()} QSOs</div></article>`
    }).join("");
  }
  renderMap(data);
}
function renderMap(data){
  const parks=Array.isArray(data?.parks)?data.parks:[];
  const map=L.map("map").setView([37.8,-96],4);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:"&copy; OpenStreetMap contributors"}).addTo(map);
  const icon=L.divIcon({className:"",html:'<div class="pin"></div>',iconSize:[15,15],iconAnchor:[7,15]});
  const valid=parks.filter(p=>Number.isFinite(Number(p.lat))&&Number.isFinite(Number(p.lon)));
  if(valid.length){
    const bounds=[];
    valid.forEach(p=>{
      const lat=Number(p.lat),lon=Number(p.lon);bounds.push([lat,lon]);
      const ref=esc(p.reference||"POTA"),name=esc(p.name||"Park");
      L.marker([lat,lon],{icon}).addTo(map).bindPopup(`<strong>${ref}</strong><br>${name}`);
    });
    map.fitBounds(bounds,{padding:[20,20],maxZoom:8});
  }else{
    L.control.scale().addTo(map);
    const note=L.control({position:"topright"});note.onAdd=()=>{const d=L.DomUtil.create("div");d.style.cssText="background:#0d191d;color:#c8d2cf;padding:7px 9px;border:1px solid #294045";d.textContent="Park coordinates appear after the first data enrichment run.";return d};note.addTo(map);
  }
}
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
fetch(DATA_URL).then(r=>r.ok?r.json():Promise.reject()).then(render).catch(()=>{$("activation-list").innerHTML='<div class="notice">The site is ready, but no POTA cache has been published yet. Run the scheduled updater after publishing this repository.</div>';$("activations-stat").textContent="—";$("parks-stat").textContent="—";$("qsos-stat").textContent="—";$("states-stat").textContent="—";renderMap({})});

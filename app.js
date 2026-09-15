const CALLSIGN="K5KAZ";
const DATA_URL=new URL("data/pota.json",window.location.href).href;
const $=id=>document.getElementById(id);
const fmt=v=>Number.isFinite(Number(v))?Number(v).toLocaleString():"—";
function first(o,keys){for(const k of keys){if(o&&o[k]!==undefined&&o[k]!==null)return o[k]}return null}
function normalize(data){const s=data?.stats||{};return{
activations:first(s,["activations","activationCount","totalActivations","activatorActivations"]),
parks:first(s,["parks","parkCount","uniqueParks","uniqueParksActivated","activatorParks"]),
qsos:first(s,["qsos","qsoCount","totalQsos","totalQSOs","activatorQsos"]),
states:first(s,["states","stateCount","uniqueStates","statesActivated"]),
activationsList:Array.isArray(data?.activationsList)?data.activationsList:[]
}}
function qso(a){return Number(a?.qsos??a?.qsoCount??a?.total??a?.contacts??0)||0}
function ref(a){return a?.reference||a?.parkReference||a?.ref||"POTA"}
function name(a){return a?.parkName||a?.name||a?.locationName||"Park"}
function date(a){return a?.date||a?.activationDate||a?.qso_date||""}
function render(data){const n=normalize(data);
$("activations-stat").textContent=fmt(n.activations);$("parks-stat").textContent=fmt(n.parks);
$("qsos-stat").textContent=fmt(n.qsos);$("states-stat").textContent=fmt(n.states);
window.k5kazActivations=n.activationsList;applyFilters();renderRecent(n.activationsList);renderMap(data)}
function applyFilters(){const body=$("activation-table-body");if(!body)return;
const search=($("activation-search")?.value||"").trim().toLowerCase(),sort=$("activation-sort")?.value||"date-desc",all=window.k5kazActivations||[];
let rows=all.filter(a=>`${ref(a)} ${name(a)} ${date(a)}`.toLowerCase().includes(search));
rows.sort((a,b)=>{if(sort==="qso-desc")return qso(b)-qso(a);if(sort==="qso-asc")return qso(a)-qso(b);if(sort==="park-asc")return ref(a).localeCompare(ref(b));
const da=new Date(date(a)).getTime()||0,db=new Date(date(b)).getTime()||0;return sort==="date-asc"?da-db:db-da});
$("activation-count").textContent=`${rows.length.toLocaleString()} of ${all.length.toLocaleString()} activations`;
body.innerHTML=rows.length?rows.map(a=>`<tr><td class="date-cell">${esc(date(a))}</td><td><strong>${esc(ref(a))}</strong></td><td>${esc(name(a))}</td><td class="qso-cell">${qso(a).toLocaleString()}</td></tr>`).join(""):`<tr><td colspan="4" class="activation-empty">No activations match your search.</td></tr>`}
function renderRecent(rows){const list=$("activation-list");if(!list)return;
list.innerHTML=rows.length?rows.slice(0,8).map(a=>`<article class="activation"><div class="thumb">▲</div><div><h4>${esc(ref(a))} — ${esc(name(a))}</h4><p>${esc(date(a))}</p><p>POTA activation</p></div><div class="qso">${qso(a).toLocaleString()} QSOs</div></article>`).join(""):`<div class="notice">POTA statistics are connected, but recent activation rows are not available.</div>`}
function renderMap(data){const el=$("map");if(!el||typeof L==="undefined")return;const parks=Array.isArray(data?.parks)?data.parks:[],map=L.map("map").setView([37.8,-96],4);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:"&copy; OpenStreetMap contributors"}).addTo(map);
const icon=L.divIcon({className:"",html:'<div class="pin"></div>',iconSize:[15,15],iconAnchor:[7,15]});
const valid=parks.filter(p=>Number.isFinite(Number(p.lat))&&Number.isFinite(Number(p.lon)));
if(valid.length){const bounds=[];valid.forEach(p=>{const lat=Number(p.lat),lon=Number(p.lon);bounds.push([lat,lon]);L.marker([lat,lon],{icon}).addTo(map).bindPopup(`<strong>${esc(p.reference||"POTA")}</strong><br>${esc(p.name||"Park")}`)});map.fitBounds(bounds,{padding:[20,20],maxZoom:8})}else{L.control.scale().addTo(map)}}
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
document.addEventListener("DOMContentLoaded",()=>{$("activation-search")?.addEventListener("input",applyFilters);$("activation-sort")?.addEventListener("change",applyFilters);
fetch(DATA_URL,{cache:"no-store"}).then(r=>{if(!r.ok)throw Error(`HTTP ${r.status}`);return r.json()}).then(render).catch(e=>{console.error(e);
if($("activation-table-body"))$("activation-table-body").innerHTML='<tr><td colspan="4" class="activation-empty">Unable to load the current POTA data.</td></tr>';
if($("activation-list"))$("activation-list").innerHTML='<div class="notice">Unable to load the current POTA data.</div>'})});
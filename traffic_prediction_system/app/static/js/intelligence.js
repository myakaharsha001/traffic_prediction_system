(() => {
const $=id=>document.getElementById(id), csrf=window.CSRF_TOKEN;
async function api(url,options={}) {
  options.headers={...(options.headers||{}),...(options.method==="POST"?{"Content-Type":"application/json","X-CSRF-Token":csrf}:{})};
  const r=await fetch(url,options); const d=await r.json().catch(()=>({error:"Invalid server response"}));
  if(!r.ok) throw new Error(d.error||"Request failed"); return d;
}
let map,marker,routeLayer;
function setLocation(lat,lon,address,loadWeather=true) {
  if(!map) return;
  if(marker) marker.setLatLng([lat,lon]); else marker=L.marker([lat,lon]).addTo(map);
  map.setView([lat,lon],15);
  if($("latitude")) { $("latitude").value=lat; $("longitude").value=lon; $("latText").textContent=lat.toFixed(5); $("lonText").textContent=lon.toFixed(5); }
  if($("intelLat")) {$("intelLat").textContent=lat.toFixed(5);$("intelLon").textContent=lon.toFixed(5);$("selectedAddress").textContent=address||"Selected location";}
  if(loadWeather) loadWeatherData(lat,lon);
}
async function loadWeatherData(lat,lon) {
  try {
    const d=await api(`/api/v2/weather?lat=${lat}&lon=${lon}`);
    if($("weatherSelect")) $("weatherSelect").value=d.condition;
    ["humidity","wind_speed","visibility"].forEach(k=>{if($(k)&&d[k]!=null) $(k).value=d[k];});
    if($("iWeather")) $("iWeather").value=d.condition;
    if($("iHumidity")&&d.humidity!=null) $("iHumidity").value=d.humidity;
    if($("iWind")&&d.wind_speed!=null) $("iWind").value=d.wind_speed;
    if($("iVisibility")&&d.visibility!=null) $("iVisibility").value=d.visibility;
    const html=`<b>${d.condition}</b><strong>${d.temperature??"—"}°C</strong><span>Humidity ${d.humidity??"—"}% · Wind ${d.wind_speed??"—"} km/h · Visibility ${d.visibility??"—"} km</span>`;
    if($("weatherCard")) {$("weatherCard").innerHTML=html;$("weatherCard").classList.remove("hidden");}
    if($("intelWeather")) $("intelWeather").innerHTML=html;
  } catch(e) {
    if($("weatherCard")) {$("weatherCard").innerHTML="Weather service unavailable. Choose weather manually."; $("weatherCard").classList.remove("hidden");}
    if($("intelWeather")) $("intelWeather").textContent=e.message+" You can continue with manual weather.";
  }
}
async function searchLocations(inputId,resultId) {
  const q=$(inputId)?.value.trim(); if(!q){$(resultId).innerHTML="<p class='muted'>Enter a location to search.</p>";return;}
  $(resultId).innerHTML="<span class='muted'>Searching…</span>";
  try {const d=await api(`/api/v2/geocode?q=${encodeURIComponent(q)}`);
    $(resultId).innerHTML=d.results.length?d.results.map((x,i)=>`<button type="button" class="search-result" data-i="${i}">${x.display_name}</button>`).join(""):"<p class='muted'>No matching locations found.</p>";
    $(resultId).querySelectorAll(".search-result").forEach((b,i)=>b.onclick=()=>{const x=d.results[i];setLocation(x.lat,x.lon,x.display_name);$(resultId).innerHTML="";if($(inputId).name==="location")$(inputId).value=x.display_name;});
  } catch(e){$(resultId).innerHTML=`<p class="error-text">${e.message}</p>`;}
}
function initPredictionMap(){
 if(!$("predictionMap")) return;
 map=L.map("predictionMap").setView([20.5937,78.9629],5);
 L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:"© OpenStreetMap contributors",maxZoom:19}).addTo(map);
 const la=parseFloat($("latitude")?.value),lo=parseFloat($("longitude")?.value);
 if(Number.isFinite(la)&&Number.isFinite(lo)){marker=L.marker([la,lo]).addTo(map);map.setView([la,lo],15);}
 map.on("click",async e=>{let address="Selected map location";try{address=await api(`/api/v2/reverse?lat=${e.latlng.lat}&lon=${e.latlng.lng}`).then(x=>x.address)}catch{};setLocation(e.latlng.lat,e.latlng.lng,address);if($("locationSearch"))$("locationSearch").value=address;});
 $("gpsBtn")?.addEventListener("click",()=>navigator.geolocation?navigator.geolocation.getCurrentPosition(async p=>{let a="Current location";try{a=(await api(`/api/v2/reverse?lat=${p.coords.latitude}&lon=${p.coords.longitude}`)).address}catch{};setLocation(p.coords.latitude,p.coords.longitude,a);$("locationSearch").value=a},()=>alert("Location permission was denied or GPS is unavailable. You can select a point on the map or search manually."),{enableHighAccuracy:true,timeout:10000}):alert("Browser geolocation is unavailable. Please select a location manually."));
 let timer; $("locationSearch")?.addEventListener("input",()=>{clearTimeout(timer);timer=setTimeout(()=>searchLocations("locationSearch","searchResults"),450)});
}
let intelMap;
function initIntelMap(){
 if(!$("intelMap")) return;
 intelMap=L.map("intelMap").setView([20.5937,78.9629],5);map=intelMap;
 L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:"© OpenStreetMap contributors",maxZoom:19}).addTo(map);
 const la=parseFloat($("latitude")?.value),lo=parseFloat($("longitude")?.value);
 if(Number.isFinite(la)&&Number.isFinite(lo)){marker=L.marker([la,lo]).addTo(map);map.setView([la,lo],15);}
 map.on("click",async e=>{let a="Selected map location";try{a=(await api(`/api/v2/reverse?lat=${e.latlng.lat}&lon=${e.latlng.lng}`)).address}catch{};setLocation(e.latlng.lat,e.latlng.lng,a);});
 $("intelGps")?.addEventListener("click",()=>navigator.geolocation?navigator.geolocation.getCurrentPosition(async p=>{let a="Current location";try{a=(await api(`/api/v2/reverse?lat=${p.coords.latitude}&lon=${p.coords.longitude}`)).address}catch{};setLocation(p.coords.latitude,p.coords.longitude,a)},()=>alert("Location permission was denied or GPS is unavailable. Select a map point or search instead."),{enableHighAccuracy:true,timeout:10000}):alert("Browser geolocation is unavailable."));
 fetch("/api/v2/incidents").then(r=>r.json()).then(d=>d.incidents.forEach(i=>L.circleMarker([i.lat,i.lon],{radius:8}).addTo(map).bindPopup(`<b>${i.title}</b><br>${i.type} · ${i.severity}<br>${i.description||""}<br><button class="small-btn" onclick="document.getElementById('iIncident').value='${i.type.replaceAll("'","\\'")}'">Use incident evidence</button>`)));
 $("intelSearchBtn")?.addEventListener("click",()=>searchLocations("intelSearch","intelResults"));
 let timer; $("intelSearch")?.addEventListener("input",()=>{clearTimeout(timer);timer=setTimeout(()=>searchLocations("intelSearch","intelResults"),500)});
}
function payload(){
 return {location:$("selectedAddress")?.textContent||"Selected location",vehicle_count:+$("iVehicles").value,average_speed:+$("iSpeed").value,time_of_day:$("iTime").value,weather:$("iWeather").value,incident:$("iIncident").value,road_condition:$("iRoad").value,visibility:$("iVisibility").value||null,humidity:$("iHumidity").value||null,wind_speed:$("iWind").value||null,latitude:+$("intelLat").textContent||null,longitude:+$("intelLon").textContent||null};
}
function renderReason(d){
 $("reasonOutput").innerHTML=`<div class="result-condition ${d.predicted.toLowerCase()}"><span>Most likely state</span><strong>${d.predicted}</strong><b>${d.confidence}% confidence</b></div><div class="prob-detail">${[["Low",d.low],["Moderate",d.moderate],["High",d.high],["Severe",d.severe]].map(x=>`<div class="prob-line"><div><span>${x[0]}</span><b>${x[1]}%</b></div><div class="bar"><i style="width:${x[1]}%"></i></div></div>`).join("")}</div><div class="panel-inset"><span class="eyebrow">EXPLAINABILITY</span>${d.evidence.map(e=>`<div class="evidence"><div><span>${e.label}</span><b>${e.strength}%</b></div><div class="bar"><i style="width:${e.strength}%"></i></div><small>${e.detail}</small></div>`).join("")}<p class="explain">${d.explanation}</p></div>`;
 renderTrend(d);
}
let trendChart;
function renderTrend(d){if(!$("trendChart"))return;const rows=[0,1,2,3,4].map(i=>({label:i?"+"+(i*15)+" min":"Now",high:Math.min(99,d.high*(1+.08*i/4)),severe:Math.min(99,d.severe*(1+.2*i/4))}));if(trendChart)trendChart.destroy();trendChart=new Chart($("trendChart"),{type:"line",data:{labels:rows.map(x=>x.label),datasets:[{label:"High",data:rows.map(x=>x.high),tension:.35,borderWidth:3},{label:"Severe",data:rows.map(x=>x.severe),tension:.35,borderWidth:3}]},options:{responsive:true,scales:{y:{beginAtZero:true,max:100}}}});}
async function reason(){try{const d=await api("/api/v2/reason",{method:"POST",body:JSON.stringify(payload())});renderReason(d);$("reasonTitle").textContent=`${d.predicted} traffic · ${d.confidence}% confidence`;return d}catch(e){$("reasonOutput").innerHTML=`<p class="error-text">${e.message}</p>`}}
async function whatIf(s){try{const d=await api("/api/v2/what-if",{method:"POST",body:JSON.stringify({...payload(),scenario:s})});$("whatIfOutput").innerHTML=`<b>${d.before.predicted} → ${d.after.predicted}</b><p>High: ${d.before.high}% → ${d.after.high}% (${d.change.high>=0?"+":""}${d.change.high} pp)</p><p>Severe: ${d.before.severe}% → ${d.after.severe}% (${d.change.severe>=0?"+":""}${d.change.severe} pp)</p>`}catch(e){$("whatIfOutput").textContent=e.message}}
const routePlaces={start:null,end:null};
function updateRouteSelection(kind,x){
 routePlaces[kind]={lat:+x.lat,lon:+x.lon,address:x.display_name||x.address||"Selected location"};
 const input=$(kind==="start"?"routeStart":"routeEnd"), selected=$(kind==="start"?"routeStartSelected":"routeEndSelected");
 if(input) input.value=routePlaces[kind].address;
 if(selected) selected.textContent=routePlaces[kind].address;
 $(kind==="start"?"routeStartResults":"routeEndResults").innerHTML="";
}
function renderRouteSearch(kind,data){
 const box=$(kind==="start"?"routeStartResults":"routeEndResults");
 if(!box)return;
 box.innerHTML=data.results.length?data.results.slice(0,6).map((x,i)=>`<button type="button" class="search-result route-search-result" data-i="${i}"><b>${x.display_name}</b><small>${Number(x.lat).toFixed(5)}, ${Number(x.lon).toFixed(5)}</small></button>`).join(""):"<p class='muted'>No matching locations found. Try a nearby landmark, area, city or full address.</p>";
 box.querySelectorAll(".route-search-result").forEach((b,i)=>b.onclick=()=>updateRouteSelection(kind,data.results[i]));
}
async function searchRoutePlace(kind){
 const input=$(kind==="start"?"routeStart":"routeEnd"),box=$(kind==="start"?"routeStartResults":"routeEndResults");
 const q=input?.value.trim();
 if(!q){box.innerHTML="<p class='muted'>Enter a location first.</p>";return;}
 box.innerHTML="<span class='muted'>Searching…</span>";
 try{const d=await api(`/api/v2/geocode?q=${encodeURIComponent(q)}`);renderRouteSearch(kind,d);}catch(e){box.innerHTML=`<p class="error-text">${e.message}</p>`;}
}
async function useRouteCurrentLocation(){
 if(!navigator.geolocation){$("routeStartResults").innerHTML="<p class='error-text'>Browser location is unavailable. Search for your starting point instead.</p>";return;}
 $("routeStartResults").innerHTML="<span class='muted'>Requesting your current location…</span>";
 navigator.geolocation.getCurrentPosition(async p=>{
   let address="Current location";
   try{address=(await api(`/api/v2/reverse?lat=${p.coords.latitude}&lon=${p.coords.longitude}`)).address||address;}catch{}
   updateRouteSelection("start",{lat:p.coords.latitude,lon:p.coords.longitude,display_name:address});
   if(map){setLocation(p.coords.latitude,p.coords.longitude,address,false);}
 },()=>{$("routeStartResults").innerHTML="<p class='error-text'>Location permission was denied or GPS is unavailable. You can type your starting location manually.</p>";},{enableHighAccuracy:true,timeout:10000,maximumAge:60000});
}
function initRouteSearch(){
 const config=[
  ["start","routeStart","routeStartResults"],["end","routeEnd","routeEndResults"]
 ];
 config.forEach(([kind,inputId])=>{
  const input=$(inputId); if(!input)return;
  let timer;
  input.addEventListener("input",()=>{
    routePlaces[kind]=null;
    const selected=$(kind==="start"?"routeStartSelected":"routeEndSelected"); if(selected)selected.textContent="Not selected";
    clearTimeout(timer);timer=setTimeout(()=>searchRoutePlace(kind),500);
  });
  input.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();searchRoutePlace(kind);}});
  input.addEventListener("blur",()=>setTimeout(()=>{
    const box=$(kind==="start"?"routeStartResults":"routeEndResults"); if(box)box.innerHTML="";
  },180));
 });
 $("routeStartGps")?.addEventListener("click",useRouteCurrentLocation);
}
async function routeCompare(){try{
 const getPlace=async kind=>{
   if(routePlaces[kind])return routePlaces[kind];
   const input=$(kind==="start"?"routeStart":"routeEnd"),q=input.value.trim();
   if(!q)throw Error(kind==="start"?"Enter a starting location or use Current Location.":"Enter a destination.");
   const d=await api(`/api/v2/geocode?q=${encodeURIComponent(q)}`);
   if(!d.results.length)throw Error(`Could not find ${kind==="start"?"the starting location":"the destination"}. Try a more specific place name.`);
   // If the user typed a place but did not explicitly choose a suggestion, use the best geocoding match.
   const x=d.results[0]; updateRouteSelection(kind,x); return routePlaces[kind];
 };
 const a=await getPlace("start"),b=await getPlace("end");
 if(a.lat===b.lat&&a.lon===b.lon)throw Error("Start and destination are the same. Choose two different locations.");
 const d=await api(`/api/v2/route?start_lat=${a.lat}&start_lon=${a.lon}&end_lat=${b.lat}&end_lon=${b.lon}`);
 if(!d.routes?.length)throw Error("No route was found between these locations.");
 if(routeLayer)routeLayer.clearLayers();routeLayer=L.layerGroup().addTo(map);
 const best=d.routes.reduce((ai,r,i)=>r.duration_min<d.routes[ai].duration_min?i:ai,0);
 $("routeOutput").innerHTML=d.routes.map((r,i)=>`<div class="route-card"><b>Route ${i+1} ${i===best?"· Recommended":""}</b><span>${r.distance_km} km · ${r.duration_min} min</span><button class="small-btn route-select" data-i="${i}">Show route</button></div>`).join("");
 const draw=i=>{routeLayer.clearLayers();const r=d.routes[i];const line=L.geoJSON(r.geometry).addTo(routeLayer);map.fitBounds(line.getBounds(),{padding:[25,25]});};
 $("routeOutput").querySelectorAll(".route-select").forEach((b,i)=>b.onclick=()=>draw(i));draw(0);
 }catch(e){$("routeOutput").innerHTML=`<p class="error-text">${e.message}</p>`}}

document.addEventListener("DOMContentLoaded",()=>{
 initPredictionMap();initIntelMap();initRouteSearch();
 $("reasonBtn")?.addEventListener("click",reason);document.querySelectorAll(".scenario").forEach(b=>b.addEventListener("click",()=>whatIf(b.dataset.scenario)));$("routeBtn")?.addEventListener("click",routeCompare);
});
})();
"""Free external-data adapters with conservative timeouts and graceful fallbacks."""
import json
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

NOMINATIM_URL="https://nominatim.openstreetmap.org"
OPEN_METEO_URL="https://api.open-meteo.com/v1/forecast"
OSRM_URL="https://router.project-osrm.org"

def _get_json(url, params=None, timeout=8):
    if params:
        from urllib.parse import urlencode
        url += ("&" if "?" in url else "?") + urlencode(params)
    req=Request(url,headers={"User-Agent":"ProbTraffic-Academic-V2/1.0 (college project; contact: admin@traffic.local)",
                              "Accept":"application/json"})
    with urlopen(req,timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def geocode(q):
    if not q or len(q.strip())<2: return []
    data=_get_json(NOMINATIM_URL+"/search",{"q":q.strip(),"format":"json","limit":5,"addressdetails":1})
    return [{"lat":float(x["lat"]),"lon":float(x["lon"]),"display_name":x.get("display_name","")} for x in data]

def reverse(lat,lon):
    data=_get_json(NOMINATIM_URL+"/reverse",{"lat":lat,"lon":lon,"format":"json","zoom":18,"addressdetails":1})
    return data.get("display_name","Unknown location")

def weather(lat,lon):
    data=_get_json(OPEN_METEO_URL,{"latitude":lat,"longitude":lon,
        "current":"temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,visibility",
        "timezone":"auto"})
    c=data.get("current",{})
    code=int(c.get("weather_code",0))
    return {"temperature":c.get("temperature_2m"),"humidity":c.get("relative_humidity_2m"),
            "wind_speed":c.get("wind_speed_10m"),"visibility":None if c.get("visibility") is None else c.get("visibility")/1000,
            "weather_code":code,"condition":weather_condition(code)}

def weather_condition(code):
    if code==0: return "Clear"
    if code in (1,2,3): return "Cloudy"
    if code in (45,48): return "Fog"
    if code in (51,53,55,61,63,65,80,81,82): return "Rain"
    if code in (66,67,71,73,75,77,85,86): return "Heavy Rain"
    if code in (95,96,99): return "Storm"
    return "Cloudy"

def routes(start_lat,start_lon,end_lat,end_lon):
    data=_get_json(f"{OSRM_URL}/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}",
                   {"alternatives":"true","overview":"full","geometries":"geojson","steps":"false"})
    out=[]
    for idx,r in enumerate(data.get("routes",[]),1):
        out.append({"id":idx,"distance_km":round(r["distance"]/1000,2),
                    "duration_min":round(r["duration"]/60,1),"geometry":r.get("geometry")})
    return {"routes":out,"code":data.get("code")}

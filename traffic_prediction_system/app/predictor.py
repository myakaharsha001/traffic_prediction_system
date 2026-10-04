"""Transparent probability/evidence reasoning engine for traffic state estimation."""
from math import exp
from datetime import datetime

STATES = ["Low", "Moderate", "High", "Severe"]
BASE = {"Low": 0.34, "Moderate": 0.34, "High": 0.23, "Severe": 0.09}

def _normalise(scores):
    total = sum(scores.values()) or 1
    return {k: (v / total) * 100 for k, v in scores.items()}

def _apply(scores, factors, evidence, label, strength=None):
    for state, factor in factors.items():
        scores[state] *= factor
    if strength is not None:
        evidence.append({"label": label, "strength": round(strength, 2), "detail": ""})

def _strength_from_factors(factors):
    # 0..100 magnitude of evidence away from neutral.
    vals = [abs(f - 1.0) for f in factors.values()]
    return min(100.0, (sum(vals) / len(vals)) * 100 * 1.6) if vals else 0

def predict(vehicle_count, average_speed, time_of_day, weather, incident,
            road_condition, visibility=None, humidity=None, wind_speed=None,
            evidence_detail=True):
    """Calculate a normalized four-state probability distribution.

    This is a transparent Bayesian-style likelihood-ratio model, not a trained ML
    model. Inputs multiply interpretable state likelihood factors and are normalized.
    """
    scores = BASE.copy()
    evidence = []

    # Volume: intentionally broad bands so the result is explainable.
    if vehicle_count >= 1000:
        factors = {"Low": .35, "Moderate": .70, "High": 2.0, "Severe": 2.5}
        label, detail, strength = "Vehicle volume", "Very strong congestion signal", 92
    elif vehicle_count >= 700:
        factors = {"Low": .55, "Moderate": 1.15, "High": 2.0, "Severe": 1.35}
        label, detail, strength = "Vehicle volume", "Strong congestion signal", 72
    elif vehicle_count >= 400:
        factors = {"Low": .85, "Moderate": 1.35, "High": 1.25, "Severe": .95}
        label, detail, strength = "Vehicle volume", "Moderate congestion signal", 48
    else:
        factors = {"Low": 1.6, "Moderate": 1.1, "High": .55, "Severe": .30}
        label, detail, strength = "Vehicle volume", "Low-volume signal", 62
    for s,f in factors.items(): scores[s] *= f
    evidence.append({"label":label,"strength":strength,"detail":detail})

    if average_speed < 15:
        factors = {"Low": .35, "Moderate": .8, "High": 1.7, "Severe": 2.1}
        detail, strength = "Strong congestion signal", 92
    elif average_speed < 30:
        factors = {"Low": .65, "Moderate": 1.2, "High": 1.65, "Severe": 1.1}
        detail, strength = "Strong congestion signal", 65
    elif average_speed < 45:
        factors = {"Low": .9, "Moderate": 1.25, "High": 1.05, "Severe": .9}
        detail, strength = "Moderate congestion signal", 35
    else:
        factors = {"Low": 1.55, "Moderate": 1.05, "High": .6, "Severe": .3}
        detail, strength = "Low-congestion signal", 60
    for s,f in factors.items(): scores[s] *= f
    evidence.append({"label":"Average speed","strength":strength,"detail":detail})

    if time_of_day in {"Morning Peak", "Evening Peak"}:
        factors={"Low":.7,"Moderate":1.0,"High":1.45,"Severe":1.3}
        detail,strength="Peak-hour signal",55
    elif time_of_day=="Night":
        factors={"Low":1.35,"Moderate":1.05,"High":.85,"Severe":.55}
        detail,strength="Off-peak signal",42
    else:
        factors={"Low":1.0,"Moderate":1.05,"High":1.0,"Severe":.95}
        detail,strength="Neutral time-period signal",15
    for s,f in factors.items(): scores[s] *= f
    evidence.append({"label":"Time period","strength":strength,"detail":detail})

    weather_factors = {
        "Clear":{"Low":1.05,"Moderate":1.0,"High":.95,"Severe":.9},
        "Cloudy":{"Low":.95,"Moderate":1.05,"High":1.05,"Severe":1.0},
        "Rain":{"Low":.65,"Moderate":1.1,"High":1.45,"Severe":1.35},
        "Heavy Rain":{"Low":.4,"Moderate":.85,"High":1.55,"Severe":1.9},
        "Fog":{"Low":.55,"Moderate":1.05,"High":1.45,"Severe":1.55},
        "Storm":{"Low":.25,"Moderate":.65,"High":1.55,"Severe":2.2},
    }
    factors=weather_factors.get(weather, {"Low":1,"Moderate":1,"High":1,"Severe":1})
    for s,f in factors.items(): scores[s] *= f
    evidence.append({"label":"Weather","strength":round(_strength_from_factors(factors),1),
                     "detail": ("Weather increases congestion risk" if weather not in ("Clear","Cloudy") else "Limited weather pressure")})

    incident_factors = {
        "None":{"Low":1.05,"Moderate":1.0,"High":.95,"Severe":.9},
        "Minor Accident":{"Low":.75,"Moderate":1.0,"High":1.35,"Severe":1.3},
        "Major Accident":{"Low":.35,"Moderate":.75,"High":1.55,"Severe":2.25},
        "Road Closure":{"Low":.25,"Moderate":.65,"High":1.4,"Severe":2.7},
        "Vehicle Breakdown":{"Low":.8,"Moderate":1.0,"High":1.3,"Severe":1.25},
        "Construction":{"Low":.75,"Moderate":1.0,"High":1.25,"Severe":1.2},
        "Traffic Jam":{"Low":.35,"Moderate":.7,"High":1.6,"Severe":2.0},
        "Weather Hazard":{"Low":.5,"Moderate":.85,"High":1.45,"Severe":1.8},
        "Other":{"Low":.9,"Moderate":1.0,"High":1.1,"Severe":1.05},
    }
    factors=incident_factors.get(incident, incident_factors["None"])
    for s,f in factors.items(): scores[s] *= f
    evidence.append({"label":"Incident","strength":round(_strength_from_factors(factors),1),
                     "detail": "Very strong congestion signal" if incident in ("Major Accident","Road Closure") else ("Moderate incident signal" if incident!="None" else "No active incident signal")})

    road_factors = {
        "Good":{"Low":1.05,"Moderate":1.0,"High":.95,"Severe":.9},
        "Wet":{"Low":.8,"Moderate":1.05,"High":1.3,"Severe":1.25},
        "Poor":{"Low":.55,"Moderate":.95,"High":1.45,"Severe":1.65},
        "Damaged":{"Low":.45,"Moderate":.9,"High":1.5,"Severe":1.8},
    }
    factors=road_factors.get(road_condition, road_factors["Good"])
    for s,f in factors.items(): scores[s] *= f
    evidence.append({"label":"Road condition","strength":round(_strength_from_factors(factors),1),
                     "detail": "Road condition increases congestion risk" if road_condition!="Good" else "Weak congestion signal"})

    if visibility is not None:
        try: visibility=float(visibility)
        except: visibility=None
        if visibility is not None:
            factors={"Low":1,"Moderate":1,"High":1,"Severe":1}
            if visibility < 2: factors={"Low":.65,"Moderate":1.0,"High":1.4,"Severe":1.6}
            elif visibility < 5: factors={"Low":.85,"Moderate":1.05,"High":1.2,"Severe":1.25}
            for s,f in factors.items(): scores[s]*=f
            evidence.append({"label":"Visibility","strength":round(_strength_from_factors(factors),1),
                             "detail":"Reduced visibility increases risk" if visibility<5 else "Good visibility"})

    if humidity is not None:
        try: humidity=float(humidity)
        except: humidity=None
        if humidity is not None and humidity >= 85 and weather in ("Rain","Heavy Rain","Fog","Storm"):
            factors={"Low":.9,"Moderate":1.02,"High":1.1,"Severe":1.15}
            for s,f in factors.items(): scores[s]*=f
            evidence.append({"label":"Humidity","strength":24,"detail":"High humidity reinforces adverse-weather signal"})

    if wind_speed is not None:
        try: wind_speed=float(wind_speed)
        except: wind_speed=None
        if wind_speed is not None and wind_speed >= 30:
            factors={"Low":.9,"Moderate":1.0,"High":1.12,"Severe":1.2}
            for s,f in factors.items(): scores[s]*=f
            evidence.append({"label":"Wind speed","strength":25,"detail":"Strong wind can increase disruption risk"})

    probabilities=_normalise(scores)
    # Round while ensuring exactly 100.00 for display/storage.
    rounded={s:round(probabilities[s],2) for s in STATES}
    rounded["Severe"]=round(100-sum(rounded[s] for s in STATES if s!="Severe"),2)
    predicted=max(rounded,key=rounded.get)
    confidence=rounded[predicted]
    explanation=_make_explanation(rounded,predicted,evidence,vehicle_count,average_speed,time_of_day,weather,incident,road_condition)
    return {"low":rounded["Low"],"moderate":rounded["Moderate"],"high":rounded["High"],
            "severe":rounded["Severe"],"predicted":predicted,"confidence":confidence,
            "evidence":evidence,"explanation":explanation}

def _make_explanation(p, predicted, evidence, vehicle_count, speed, time_of_day, weather, incident, road_condition):
    positives=[e for e in evidence if e["strength"] >= 45 and ("congestion" in e["detail"].lower() or "risk" in e["detail"].lower() or "peak" in e["detail"].lower() or "incident" in e["detail"].lower())]
    phrases=[]
    for e in sorted(positives,key=lambda x:x["strength"],reverse=True)[:4]:
        phrases.append(f'{e["label"].lower()} → {e["detail"].lower()}')
    if not phrases:
        phrases=["the selected evidence is relatively balanced across traffic states"]
    return f'{predicted} traffic is predicted mainly because ' + ", ".join(phrases) + "."

def trend(result, steps=5):
    """Project probabilities for the next 60 minutes as a model sensitivity projection."""
    base_high=result["high"]; base_severe=result["severe"]
    rows=[]
    for i in range(steps):
        # gradual projection, bounded and deterministic; not a live forecast.
        factor=i/4
        high=min(99, base_high*(1+0.08*factor))
        severe=min(99, base_severe*(1+0.20*factor))
        rows.append({"label":"Now" if i==0 else f"+{i*15} min",
                     "high":round(high,2),"severe":round(severe,2)})
    return rows

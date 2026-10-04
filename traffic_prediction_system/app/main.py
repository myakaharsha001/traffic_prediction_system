from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort, Response
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from . import db
from .models import Prediction, TrafficRecord, Location, WeatherData, Incident, PredictionFeedback, Notification
from .predictor import predict, trend
from .services import geocode, reverse, weather, routes as get_routes

main_bp=Blueprint("main",__name__)

def _num(v, cast=float):
    if v in (None,""): return None
    return cast(v)

def _payload_prediction(data):
    location=str(data.get("location","")).strip()
    vc=_num(data.get("vehicle_count"),int); speed=_num(data.get("average_speed"))
    vals={"location":location,"vehicle_count":vc,"average_speed":speed,
          "time_of_day":str(data.get("time_of_day","")).strip(),
          "weather":str(data.get("weather","")).strip(),"incident":str(data.get("incident","")).strip(),
          "road_condition":str(data.get("road_condition","")).strip(),
          "latitude":_num(data.get("latitude")),"longitude":_num(data.get("longitude")),
          "visibility":_num(data.get("visibility")),"humidity":_num(data.get("humidity")),
          "wind_speed":_num(data.get("wind_speed"))}
    if not location or vc is None or speed is None: raise ValueError("Location, vehicle count and average speed are required.")
    if not 0<=vc<=10000: raise ValueError("Vehicle count must be between 0 and 10,000.")
    if not 0<speed<=200: raise ValueError("Average speed must be between 0 and 200 km/h.")
    if not vals["time_of_day"] or not vals["weather"] or not vals["incident"] or not vals["road_condition"]:
        raise ValueError("Please complete all traffic evidence fields.")
    if vals["latitude"] is not None and not -90<=vals["latitude"]<=90: raise ValueError("Invalid latitude.")
    if vals["longitude"] is not None and not -180<=vals["longitude"]<=180: raise ValueError("Invalid longitude.")
    return vals

def _save_prediction(vals):
    result=predict(vals["vehicle_count"],vals["average_speed"],vals["time_of_day"],vals["weather"],
                   vals["incident"],vals["road_condition"],vals["visibility"],vals["humidity"],vals["wind_speed"])
    record=TrafficRecord(created_by=current_user.id,**{k:vals[k] for k in vals})
    db.session.add(record); db.session.flush()
    pred=Prediction(user_id=current_user.id,traffic_record_id=record.id,
        low_probability=result["low"],moderate_probability=result["moderate"],
        high_probability=result["high"],severe_probability=result["severe"],
        predicted_condition=result["predicted"],confidence=result["confidence"],
        explanation=result["explanation"])
    db.session.add(pred); db.session.commit()
    combined=result["high"]+result["severe"]
    if combined>45:
        level="critical" if combined>70 else "warning"
        title="SEVERE TRAFFIC WARNING" if combined>70 else "HIGH CONGESTION"
        message=("Severe traffic probability has exceeded the configured threshold."
                 if combined>70 else "There is an elevated probability of congestion at the selected location.")
        db.session.add(Notification(user_id=current_user.id,prediction_id=pred.id,title=title,message=message,severity=level))
        db.session.commit()
    return result,pred

@main_bp.route("/")
def index(): return render_template("index.html")

@main_bp.route("/dashboard")
@login_required
def dashboard():
    predictions=Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).limit(8).all()
    total=Prediction.query.filter_by(user_id=current_user.id).count()
    high_count=Prediction.query.filter(Prediction.user_id==current_user.id,Prediction.predicted_condition.in_(["High","Severe"])).count()
    evaluated=Prediction.query.join(PredictionFeedback).filter(Prediction.user_id==current_user.id).count()
    correct=Prediction.query.join(PredictionFeedback).filter(Prediction.user_id==current_user.id,Prediction.predicted_condition==PredictionFeedback.actual_condition).count()
    accuracy=round(correct/evaluated*100,1) if evaluated else None
    alerts=Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    return render_template("dashboard.html",predictions=predictions,total=total,high_count=high_count,
                           evaluated=evaluated,accuracy=accuracy,alerts=alerts)

@main_bp.route("/predict",methods=["GET","POST"])
@login_required
def prediction():
    result=None
    reopen_id=request.args.get("reopen", type=int)
    reopen_data=None
    if reopen_id:
        old=Prediction.query.filter_by(id=reopen_id,user_id=current_user.id).first()
        if old:
            r=old.traffic_record
            reopen_data={k:getattr(r,k) for k in ("location","latitude","longitude","vehicle_count","average_speed","time_of_day","weather","incident","road_condition","visibility","humidity","wind_speed")}
    if request.method=="POST":
        try:
            vals=_payload_prediction(request.form); result,pred=_save_prediction(vals)
            flash("Prediction calculated and saved successfully.","success")
        except ValueError as exc: db.session.rollback(); flash(str(exc),"danger")
        except Exception: db.session.rollback(); flash("Unable to save the prediction. Please try again.","danger")
    return render_template("prediction.html",result=result,reopen_id=reopen_id,reopen_data=reopen_data)

@main_bp.route("/intelligence")
@login_required
def intelligence():
    incidents=Incident.query.filter_by(active=True).order_by(Incident.created_at.desc()).all()
    return render_template("intelligence.html",incidents=incidents)

@main_bp.route("/history")
@login_required
def history():
    q=Prediction.query.filter_by(user_id=current_user.id).join(TrafficRecord)
    search=request.args.get("q","").strip()
    state=request.args.get("state","").strip()
    sort=request.args.get("sort","newest")
    if search: q=q.filter(or_(TrafficRecord.location.ilike(f"%{search}%"),TrafficRecord.weather.ilike(f"%{search}%")))
    if state: q=q.filter(Prediction.predicted_condition==state)
    q=q.order_by(Prediction.created_at.asc() if sort=="oldest" else Prediction.created_at.desc())
    predictions=q.limit(200).all()
    return render_template("history.html",predictions=predictions,search=search,state=state,sort=sort)

@main_bp.route("/history/<int:prediction_id>")
@login_required
def prediction_detail(prediction_id):
    p=Prediction.query.filter_by(id=prediction_id,user_id=current_user.id).first_or_404()
    return render_template("prediction_detail.html",p=p)

@main_bp.route("/history/<int:prediction_id>/reopen")
@login_required
def reopen_prediction(prediction_id):
    p=Prediction.query.filter_by(id=prediction_id,user_id=current_user.id).first_or_404()
    r=p.traffic_record
    return redirect(url_for("main.prediction",reopen=prediction_id))

@main_bp.route("/reports.csv")
@login_required
def reports_csv():
    import csv, io
    rows=Prediction.query.filter_by(user_id=current_user.id).join(TrafficRecord).order_by(Prediction.created_at.desc()).limit(1000).all()
    out=io.StringIO(); w=csv.writer(out)
    w.writerow(["Date","Location","Latitude","Longitude","Traffic State","Confidence","Low %","Moderate %","High %","Severe %","Weather","Vehicles","Speed","Incident","Road Condition","Actual"])
    for p in rows:
        w.writerow([p.created_at.isoformat(),p.traffic_record.location,p.traffic_record.latitude,p.traffic_record.longitude,p.predicted_condition,p.confidence,p.low_probability,p.moderate_probability,p.high_probability,p.severe_probability,p.traffic_record.weather,p.traffic_record.vehicle_count,p.traffic_record.average_speed,p.traffic_record.incident,p.traffic_record.road_condition,p.feedback.actual_condition if p.feedback else ""])
    return Response(out.getvalue(),mimetype="text/csv",headers={"Content-Disposition":"attachment; filename=traffic_predictions.csv"})

@main_bp.route("/notifications")
@login_required
def notifications():
    items=Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(100).all()
    return render_template("notifications.html",notifications=items)

@main_bp.route("/map")
@login_required
def map_view():
    points=TrafficRecord.query.filter(TrafficRecord.latitude.isnot(None),TrafficRecord.longitude.isnot(None)).order_by(TrafficRecord.created_at.desc()).limit(100).all()
    return render_template("map.html",locations=[{"name":x.location,"lat":x.latitude,"lon":x.longitude} for x in points])

@main_bp.route("/reports")
@login_required
def reports():
    q=Prediction.query.filter_by(user_id=current_user.id).join(TrafficRecord)
    search=request.args.get("q","").strip(); state=request.args.get("state","").strip()
    if search: q=q.filter(TrafficRecord.location.ilike(f"%{search}%"))
    if state: q=q.filter(Prediction.predicted_condition==state)
    predictions=q.order_by(Prediction.created_at.desc()).limit(300).all()
    return render_template("reports.html",predictions=predictions,search=search,state=state)

@main_bp.route("/api/dashboard")
@login_required
def dashboard_api():
    rows=Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.asc()).all()[-12:]
    return jsonify({"labels":[r.created_at.strftime("%d %b") for r in rows],
                    "high":[r.high_probability for r in rows],"severe":[r.severe_probability for r in rows],
                    "moderate":[r.moderate_probability for r in rows],"low":[r.low_probability for r in rows]})

# ---------- V2 APIs ----------
@main_bp.route("/api/v2/geocode")
@login_required
def api_geocode():
    try: return jsonify({"results":geocode(request.args.get("q",""))})
    except Exception: return jsonify({"error":"Location search is temporarily unavailable."}),502

@main_bp.route("/api/v2/reverse")
@login_required
def api_reverse():
    try:
        lat=float(request.args["lat"]); lon=float(request.args["lon"])
        if not -90<=lat<=90 or not -180<=lon<=180: raise ValueError
        return jsonify({"address":reverse(lat,lon)})
    except (KeyError,ValueError): return jsonify({"error":"Invalid coordinates."}),400
    except Exception: return jsonify({"error":"Reverse geocoding is temporarily unavailable."}),502

@main_bp.route("/api/v2/weather")
@login_required
def api_weather():
    try:
        lat=float(request.args["lat"]); lon=float(request.args["lon"])
        if not -90<=lat<=90 or not -180<=lon<=180: raise ValueError
        data=weather(lat,lon)
        db.session.add(WeatherData(latitude=lat,longitude=lon,**data)); db.session.commit()
        return jsonify(data)
    except (KeyError,ValueError): return jsonify({"error":"Invalid coordinates."}),400
    except Exception: return jsonify({"error":"Weather service unavailable. You can choose weather manually."}),502

@main_bp.route("/api/v2/route")
@login_required
def api_route():
    try:
        vals=[float(request.args[x]) for x in ("start_lat","start_lon","end_lat","end_lon")]
        if not (-90<=vals[0]<=90 and -180<=vals[1]<=180 and -90<=vals[2]<=90 and -180<=vals[3]<=180): raise ValueError
        return jsonify(get_routes(*vals))
    except (KeyError,ValueError): return jsonify({"error":"Invalid route coordinates."}),400
    except Exception: return jsonify({"error":"Routing service is unavailable."}),502

@main_bp.route("/api/v2/incidents")
@login_required
def api_incidents():
    return jsonify({"incidents":[{"id":i.id,"title":i.title,"type":i.incident_type,"description":i.description,
        "lat":i.latitude,"lon":i.longitude,"severity":i.severity,"active":i.active} for i in Incident.query.filter_by(active=True).all()]})

@main_bp.route("/api/v2/reason",methods=["POST"])
@login_required
def api_reason():
    try:
        vals=_payload_prediction(request.get_json(silent=True) or {})
        return jsonify(predict(vals["vehicle_count"],vals["average_speed"],vals["time_of_day"],vals["weather"],
                                vals["incident"],vals["road_condition"],vals["visibility"],vals["humidity"],vals["wind_speed"]))
    except ValueError as e: return jsonify({"error":str(e)}),400
    except Exception: return jsonify({"error":"Unable to calculate reasoning result."}),500

@main_bp.route("/api/v2/trend",methods=["POST"])
@login_required
def api_trend():
    try: return jsonify({"trend":trend(request.get_json(silent=True) or {})})
    except Exception: return jsonify({"error":"Unable to create trend projection."}),400

@main_bp.route("/api/v2/what-if",methods=["POST"])
@login_required
def api_what_if():
    try:
        data=request.get_json(silent=True) or {}; vals=_payload_prediction(data)
        base=predict(vals["vehicle_count"],vals["average_speed"],vals["time_of_day"],vals["weather"],vals["incident"],vals["road_condition"],vals["visibility"],vals["humidity"],vals["wind_speed"])
        scenario=data.get("scenario")
        changed=dict(vals)
        if scenario=="rain_starts": changed["weather"]="Rain"
        elif scenario=="rain_stops": changed["weather"]="Clear"
        elif scenario=="vehicles_up": changed["vehicle_count"]=round(vals["vehicle_count"]*1.3)
        elif scenario=="vehicles_down": changed["vehicle_count"]=round(vals["vehicle_count"]*.7)
        elif scenario=="accident": changed["incident"]="Major Accident"
        elif scenario=="road_worse": changed["road_condition"]="Poor"
        else: return jsonify({"error":"Unknown scenario."}),400
        after=predict(changed["vehicle_count"],changed["average_speed"],changed["time_of_day"],changed["weather"],changed["incident"],changed["road_condition"],changed["visibility"],changed["humidity"],changed["wind_speed"])
        return jsonify({"before":base,"after":after,"change":{"high":round(after["high"]-base["high"],2),"severe":round(after["severe"]-base["severe"],2)},
                        "scenario":scenario,"inputs":changed})
    except ValueError as e:return jsonify({"error":str(e)}),400
    except Exception:return jsonify({"error":"Unable to run what-if scenario."}),500

@main_bp.route("/api/v2/feedback",methods=["POST"])
@login_required
def api_feedback():
    try:
        data=request.get_json(silent=True) or {}; pid=int(data.get("prediction_id")); actual=data.get("actual_condition")
        if actual not in ("Low","Moderate","High","Severe"): raise ValueError("Invalid actual traffic state.")
        p=Prediction.query.filter_by(id=pid,user_id=current_user.id).first_or_404()
        existing=PredictionFeedback.query.filter_by(prediction_id=pid).first()
        if existing: existing.actual_condition=actual
        else: db.session.add(PredictionFeedback(prediction_id=pid,actual_condition=actual))
        db.session.commit()
        return jsonify({"ok":True,"actual":actual})
    except ValueError as e:return jsonify({"error":str(e)}),400

@main_bp.route("/api/v2/accuracy")
@login_required
def api_accuracy():
    q=Prediction.query.filter_by(user_id=current_user.id).join(PredictionFeedback)
    evaluated=q.count(); correct=q.filter(Prediction.predicted_condition==PredictionFeedback.actual_condition).count()
    return jsonify({"evaluated":evaluated,"correct":correct,"accuracy":round(correct/evaluated*100,1) if evaluated else None,
                    "note":"Accuracy is calculated only from predictions that have recorded actual outcomes."})

@main_bp.route("/api/v2/admin-analytics")
@login_required
def api_admin_analytics():
    if current_user.role!="admin": return jsonify({"error":"Administrator access required."}),403
    from .models import User
    states={x:Prediction.query.filter_by(predicted_condition=x).count() for x in ("Low","Moderate","High","Severe")}
    evaluated=Prediction.query.join(PredictionFeedback).count()
    correct=Prediction.query.join(PredictionFeedback).filter(Prediction.predicted_condition==PredictionFeedback.actual_condition).count()
    rows=Prediction.query.order_by(Prediction.created_at.asc()).limit(500).all()
    activity={}
    for p in rows:
        k=p.created_at.strftime("%d %b")
        activity[k]=activity.get(k,0)+1
    incidents={}
    for i in Incident.query.all(): incidents[i.incident_type]=incidents.get(i.incident_type,0)+1
    confusion={s:{a:Prediction.query.join(PredictionFeedback).filter(Prediction.predicted_condition==s,PredictionFeedback.actual_condition==a).count() for a in ("Low","Moderate","High","Severe")} for s in ("Low","Moderate","High","Severe")}
    return jsonify({"users":User.query.count(),"records":TrafficRecord.query.count(),"predictions":Prediction.query.count(),
        "high":states["High"],"severe":states["Severe"],"active_incidents":Incident.query.filter_by(active=True).count(),
        "evaluated":evaluated,"accuracy":round(correct/evaluated*100,1) if evaluated else None,"states":states,
        "activity":{"labels":list(activity.keys())[-14:],"values":list(activity.values())[-14:]},
        "incidents":incidents,"confusion":confusion})

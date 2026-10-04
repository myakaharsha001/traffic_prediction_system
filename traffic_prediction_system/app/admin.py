from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import db
from .models import User, TrafficRecord, Prediction, Incident, PredictionFeedback

admin_bp=Blueprint("admin",__name__,url_prefix="/admin")

def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args,**kwargs):
        if current_user.role!="admin":
            flash("Administrator access is required.","danger")
            return redirect(url_for("main.dashboard"))
        return view(*args,**kwargs)
    return wrapped

@admin_bp.route("/")
@admin_required
def dashboard():
    evaluated=Prediction.query.join(PredictionFeedback).count()
    correct=Prediction.query.join(PredictionFeedback).filter(Prediction.predicted_condition==PredictionFeedback.actual_condition).count()
    return render_template("admin/dashboard.html",users=User.query.order_by(User.created_at.desc()).all(),
      records=TrafficRecord.query.order_by(TrafficRecord.created_at.desc()).limit(20).all(),
      prediction_count=Prediction.query.count(),high_count=Prediction.query.filter_by(predicted_condition="High").count(),
      severe_count=Prediction.query.filter_by(predicted_condition="Severe").count(),
      incident_count=Incident.query.filter_by(active=True).count(),evaluated=evaluated,
      accuracy=round(correct/evaluated*100,1) if evaluated else None)

@admin_bp.route("/users")
@admin_required
def users(): return render_template("admin/users.html",users=User.query.order_by(User.created_at.desc()).all())

@admin_bp.route("/traffic")
@admin_required
def traffic(): return render_template("admin/traffic.html",records=TrafficRecord.query.order_by(TrafficRecord.created_at.desc()).limit(200).all())

@admin_bp.route("/predictions")
@admin_required
def predictions(): return render_template("admin/predictions.html",predictions=Prediction.query.order_by(Prediction.created_at.desc()).limit(300).all())

@admin_bp.route("/incidents")
@admin_required
def incidents(): return render_template("admin/incidents.html",incidents=Incident.query.order_by(Incident.created_at.desc()).all())

@admin_bp.route("/incidents/add",methods=["POST"])
@admin_required
def add_incident():
    try:
        i=Incident(title=request.form["title"].strip(),incident_type=request.form["incident_type"],description=request.form.get("description","").strip(),
          latitude=float(request.form["latitude"]),longitude=float(request.form["longitude"]),severity=request.form.get("severity","Medium"),
          active=request.form.get("active")=="on",created_by=current_user.id)
        if not -90<=i.latitude<=90 or not -180<=i.longitude<=180: raise ValueError
        db.session.add(i);db.session.commit();flash("Incident added.","success")
    except Exception:db.session.rollback();flash("Invalid incident details.","danger")
    return redirect(url_for("admin.incidents"))

@admin_bp.route("/incidents/<int:incident_id>/toggle",methods=["POST"])
@admin_required
def toggle_incident(incident_id):
    i=Incident.query.get_or_404(incident_id);i.active=not i.active;db.session.commit()
    flash("Incident status updated.","success");return redirect(url_for("admin.incidents"))

@admin_bp.route("/incidents/<int:incident_id>/delete",methods=["POST"])
@admin_required
def delete_incident(incident_id):
    i=Incident.query.get_or_404(incident_id);db.session.delete(i);db.session.commit()
    flash("Incident removed.","success");return redirect(url_for("admin.incidents"))

@admin_bp.route("/delete-record/<int:record_id>",methods=["POST"])
@admin_required
def delete_record(record_id):
    record=TrafficRecord.query.get_or_404(record_id)
    preds=Prediction.query.filter_by(traffic_record_id=record.id).all()
    for pred in preds:
        PredictionFeedback.query.filter_by(prediction_id=pred.id).delete()
        db.session.delete(pred)
    db.session.delete(record);db.session.commit();flash("Traffic record deleted.","success")
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/make-admin/<int:user_id>",methods=["POST"])
@admin_required
def make_admin(user_id):
    user=User.query.get_or_404(user_id);user.role="admin";db.session.commit()
    flash(f"{user.name} is now an administrator.","success");return redirect(url_for("admin.users"))

@admin_bp.route("/users/<int:user_id>/delete",methods=["POST"])
@admin_required
def delete_user(user_id):
    if user_id==current_user.id: flash("You cannot delete your own admin account.","danger");return redirect(url_for("admin.users"))
    u=User.query.get_or_404(user_id);db.session.delete(u);db.session.commit();flash("User removed.","success")
    return redirect(url_for("admin.users"))

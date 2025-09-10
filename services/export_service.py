import pandas as pd
from models.models import Incident, ShiftKeyPoint
from app import db
from flask import send_file
from reportlab.pdfgen import canvas
import io

def export_incidents_csv(date, shift_id):
    incidents = Incident.query.filter_by(shift_id=shift_id).all()
    df = pd.DataFrame([{'Title': i.title, 'Status': i.status, 'Priority': i.priority, 'Handover': i.handover} for i in incidents])
    csv_io = io.StringIO()
    df.to_csv(csv_io, index=False)
    csv_io.seek(0)
    return send_file(io.BytesIO(csv_io.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name=f'incidents_{date}.csv')

def export_keypoints_pdf(date, shift_id):
    keypoints = ShiftKeyPoint.query.filter_by(shift_id=shift_id).all()
    pdf_io = io.BytesIO()
    c = canvas.Canvas(pdf_io)
    c.drawString(100, 800, f"Shift Key Points for {date}")
    y = 780
    for kp in keypoints:
        c.drawString(100, y, f"{kp.description} - {kp.status}")
        y -= 20
    c.save()
    pdf_io.seek(0)
    return send_file(pdf_io, mimetype='application/pdf', as_attachment=True, download_name=f'keypoints_{date}.pdf')

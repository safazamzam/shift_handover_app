from flask_mail import Message
from app import mail
from flask import current_app

def send_handover_email(shift):
    import logging
    from models.models import Incident, ShiftKeyPoint, TeamMember
    subject = f"{shift.current_shift_type} to {shift.next_shift_type} Handover - {shift.date}"
    recipients = [current_app.config['TEAM_EMAIL']]

    # Gather details
    current_engineers = ', '.join([e.name for e in shift.current_engineers])
    next_engineers = ', '.join([e.name for e in shift.next_engineers])
    open_incidents = Incident.query.filter_by(shift_id=shift.id, type='Active').all()
    closed_incidents = Incident.query.filter_by(shift_id=shift.id, type='Closed').all()
    priority_incidents = Incident.query.filter_by(shift_id=shift.id, type='Priority').all()
    handover_incidents = Incident.query.filter_by(shift_id=shift.id, type='Handover').all()
    key_points = ShiftKeyPoint.query.filter_by(shift_id=shift.id).all()

    def incident_summary_table():
        # Find the max number of rows needed
        max_len = max(len(open_incidents), len(closed_incidents), len(priority_incidents), len(handover_incidents))
        def get_title(lst, idx):
            return lst[idx].title if idx < len(lst) else ''
        rows = ''
        for i in range(max_len):
            rows += f'<tr>' \
                f'<td>{get_title(open_incidents, i)}</td>' \
                f'<td>{get_title(closed_incidents, i)}</td>' \
                f'<td>{get_title(priority_incidents, i)}</td>' \
                f'<td>{get_title(handover_incidents, i)}</td>' \
                f'</tr>'
        if not rows:
            rows = '<tr><td colspan="4">No incidents</td></tr>'
        return (
            '<h4>Incidents Summary</h4>'
            '<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%; text-align:left;">'
            '<tr>'
            '<th>Open</th><th>Closed</th><th>Priority</th><th>Handover</th>'
            '</tr>'
            f'{rows}'
            '</table>'
        )

    def key_points_table(items):
        if not items:
            return '<h4>Key Points</h4><table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%;"><tr><td colspan="3">None</td></tr></table>'
        rows = ''
        for kp in items:
            responsible = TeamMember.query.get(kp.responsible_engineer_id).name if kp.responsible_engineer_id else "-"
            rows += f'<tr><td>{kp.description}</td><td>{kp.status}</td><td>{responsible}</td></tr>'
        return f'<h4>Key Points</h4><table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%;"><tr><th>Description</th><th>Status</th><th>Responsible</th></tr>{rows}</table>'

    html = f"""
    <h2>Shift Handover Details</h2>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
        <tr><th>Date</th><td>{shift.date}</td></tr>
        <tr><th>From</th><td>{shift.current_shift_type}</td></tr>
        <tr><th>To</th><td>{shift.next_shift_type}</td></tr>
        <tr><th>Current Shift Engineers</th><td>{current_engineers}</td></tr>
        <tr><th>Next Shift Engineers</th><td>{next_engineers}</td></tr>
    </table>
    <br>
    {incident_summary_table()}<br>
    {key_points_table(key_points)}
    """
    msg = Message(subject, recipients=recipients)
    msg.body = "Please view this email in HTML format."
    msg.html = html
    logging.basicConfig(level=logging.DEBUG, force=True)
    print(f"[EMAIL_SERVICE] Attempting to send email to {recipients} with subject '{subject}'")
    logging.debug(f"[EMAIL_SERVICE] Attempting to send email to {recipients} with subject '{subject}'")
    try:
        mail.send(msg)
        print(f"[EMAIL_SERVICE] Email sent successfully to {recipients}")
        logging.debug(f"[EMAIL_SERVICE] Email sent successfully to {recipients}")
    except Exception as e:
        print(f"[EMAIL_SERVICE] Failed to send email to {recipients}: {e}")
        logging.error(f"[EMAIL_SERVICE] Failed to send email to {recipients}: {e}")
        raise

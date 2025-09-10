from flask import Blueprint, render_template

misc_bp = Blueprint('misc', __name__)

@misc_bp.route('/change-management')
def change_management():
    return render_template('coming_soon.html', title='Change Management')

@misc_bp.route('/problem-tickets')
def problem_tickets():
    return render_template('coming_soon.html', title='Problem Tickets')

@misc_bp.route('/kb-details')
def kb_details():
    return render_template('coming_soon.html', title='KB Details')

@misc_bp.route('/vendor-details')
def vendor_details():
    return render_template('coming_soon.html', title='Vendor Details')

@misc_bp.route('/postmortem-details')
def postmortem_details():
    return render_template('coming_soon.html', title='Postmortem Details')

@misc_bp.route('/application-details')
def application_details():
    return render_template('coming_soon.html', title='Application Details')


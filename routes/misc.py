from flask import Blueprint, render_template, request
from services.audit_service import log_action

misc_bp = Blueprint('misc', __name__)

@misc_bp.route('/change-management')
def change_management():
    log_action('View Change Management Tab', f'Path: {request.path}')
    return render_template('coming_soon.html', title='Change Management')

@misc_bp.route('/problem-tickets')
def problem_tickets():
    log_action('View Problem Tickets Tab', f'Path: {request.path}')
    return render_template('coming_soon.html', title='Problem Tickets')

@misc_bp.route('/kb-details')
def kb_details():
    log_action('View KB Details Tab', f'Path: {request.path}')
    return render_template('coming_soon.html', title='KB Details')


@misc_bp.route('/postmortem-details')
def postmortem_details():
    log_action('View Postmortem Details Tab', f'Path: {request.path}')
    return render_template('coming_soon.html', title='Postmortem Details')



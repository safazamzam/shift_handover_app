from flask import Blueprint, render_template, request, jsonify
from models.application_detail import ApplicationDetail
from app import db

bp = Blueprint('application_details', __name__)

@bp.route('/application-details', methods=['GET'])
def application_details():
    apps = ApplicationDetail.query.all()
    return render_template('application_details.html', apps=apps)

@bp.route('/api/application-details', methods=['POST'])
def add_application():
    data = request.json
    app = ApplicationDetail(
        name=data['name'],
        purpose=data['purpose'],
        recording_link=data['recording_link'],
        documents_link=data['documents_link']
    )
    db.session.add(app)
    db.session.commit()
    return jsonify({'id': app.id})

@bp.route('/api/application-details/<int:id>', methods=['PUT'])
def edit_application(id):
    app = ApplicationDetail.query.get_or_404(id)
    data = request.json
    app.name = data['name']
    app.purpose = data['purpose']
    app.recording_link = data['recording_link']
    app.documents_link = data['documents_link']
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/api/application-details/<int:id>', methods=['DELETE'])
def delete_application(id):
    app = ApplicationDetail.query.get_or_404(id)
    db.session.delete(app)
    db.session.commit()
    return jsonify({'success': True})

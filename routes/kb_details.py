from flask import Blueprint, render_template, request, jsonify
from models.kb_detail import KBDetail
from app import db

bp = Blueprint('kb_details', __name__)

@bp.route('/kb-details', methods=['GET'])
def kb_details():
    kbs = KBDetail.query.all()
    return render_template('kb_details.html', kbs=kbs)

@bp.route('/api/kb-details', methods=['POST'])
def add_kb():
    data = request.json
    kb = KBDetail(
        application_name=data['application_name'],
        issue=data['issue'],
        description=data['description'],
        kb_number=data['kb_number']
    )
    db.session.add(kb)
    db.session.commit()
    return jsonify({'id': kb.id})

@bp.route('/api/kb-details/<int:id>', methods=['PUT'])
def edit_kb(id):
    kb = KBDetail.query.get_or_404(id)
    data = request.json
    kb.application_name = data['application_name']
    kb.issue = data['issue']
    kb.description = data['description']
    kb.kb_number = data['kb_number']
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/api/kb-details/<int:id>', methods=['DELETE'])
def delete_kb(id):
    kb = KBDetail.query.get_or_404(id)
    db.session.delete(kb)
    db.session.commit()
    return jsonify({'success': True})

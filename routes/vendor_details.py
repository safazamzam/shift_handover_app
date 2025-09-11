from flask import Blueprint, render_template, request, jsonify
from models.vendor_detail import VendorDetail
from app import db

bp = Blueprint('vendor_details', __name__)

@bp.route('/vendor-details', methods=['GET'])
def vendor_details():
    vendors = VendorDetail.query.all()
    return render_template('vendor_details.html', vendors=vendors)

@bp.route('/api/vendor-details', methods=['POST'])
def add_vendor():
    data = request.json
    vendor = VendorDetail(
        application_name=data['application_name'],
        vendor_name=data['vendor_name'],
        contact_name=data['contact_name'],
        phone=data['phone'],
        email=data['email']
    )
    db.session.add(vendor)
    db.session.commit()
    return jsonify({'id': vendor.id})

@bp.route('/api/vendor-details/<int:id>', methods=['PUT'])
def edit_vendor(id):
    vendor = VendorDetail.query.get_or_404(id)
    data = request.json
    vendor.application_name = data['application_name']
    vendor.vendor_name = data['vendor_name']
    vendor.contact_name = data['contact_name']
    vendor.phone = data['phone']
    vendor.email = data['email']
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/api/vendor-details/<int:id>', methods=['DELETE'])
def delete_vendor(id):
    vendor = VendorDetail.query.get_or_404(id)
    db.session.delete(vendor)
    db.session.commit()
    return jsonify({'success': True})

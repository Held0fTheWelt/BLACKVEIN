"""
Admin settings API routes for global configuration management.

MVP5: Typewriter delivery configuration endpoint.
"""

import json
from flask import request, jsonify
from app.extensions import db
from app.models.backend.site_setting import SiteSetting
from app.api.v1 import api_v1_bp


@api_v1_bp.route('/admin/frontend-config/typewriter', methods=['GET', 'PATCH'])
def typewriter_config():
    """
    Get or update typewriter delivery configuration.

    GET: Return current typewriter config or defaults
    PATCH: Update typewriter config in database
    """
    if request.method == 'GET':
        # Retrieve from database or return defaults
        setting = SiteSetting.query.get('frontend_typewriter_config')
        if setting and setting.value:
            try:
                config = json.loads(setting.value)
                return jsonify(config)
            except (json.JSONDecodeError, ValueError):
                pass

        # Return defaults
        return jsonify({
            'characters_per_second': 44,
            'pause_before_ms': 150,
            'pause_after_ms': 650,
            'skippable': True,
        })

    if request.method == 'PATCH':
        # Update configuration in database
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON body provided'}), 400

        # Validate required fields (optional, for now accept any dict)
        try:
            # Get or create setting
            setting = SiteSetting.query.get('frontend_typewriter_config')
            if not setting:
                setting = SiteSetting(key='frontend_typewriter_config')
                db.session.add(setting)

            # Store as JSON
            setting.value = json.dumps(data)
            db.session.commit()

            return jsonify({'saved': True, 'config': data})

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to save config: {str(e)}'}), 500

    return jsonify({'error': 'Method not allowed'}), 405

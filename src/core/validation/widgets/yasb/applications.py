DEFAULTS = {
    'animation': {
        'enabled': True,
        'type': 'fadeInOut',
        'duration': 200
    },
    'container_padding': {'top': 0, 'left': 0, 'bottom': 0, 'right': 0}
}
VALIDATION_SCHEMA = {
    'label': {
        'type': 'string'
    },
    'class_name': {
        'type': 'string',
        'required': False,
        'default': ""
    },
    'image_icon_size': {
        'type': 'integer',
        'required': False,
        'default': 14
    },
    'app_list': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                'icon': {'type': 'string'},
                'launch': {'type': 'string'}
            }
        }
    },
    'animation': {
        'type': 'dict',
        'required': False,
        'schema': {
            'enabled': {
                'type': 'boolean',
                'default': DEFAULTS['animation']['enabled']
            },
            'type': {
                'type': 'string',
                'default': DEFAULTS['animation']['type']
            },
            'duration': {
                'type': 'integer',
                'default': DEFAULTS['animation']['duration']
            }
        },
        'default': DEFAULTS['animation']
    },
    'container_padding': {
        'type': 'dict',
        'default': DEFAULTS['container_padding'],
        'required': False
    }
}

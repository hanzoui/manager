import os
import logging

ENABLE_LEGACY_COMFYUI_MANAGER_FRONT_DEFAULT = True # Enable legacy ComfyUI Manager frontend while new UI is in beta phase

def prestartup():
    from . import prestartup_script  # noqa: F401
    logging.info('[PRE] ComfyUI-Manager')


def start():
    logging.info('[START] ComfyUI-Manager')
    from .glob import manager_server  # noqa: F401
    from .glob import share_3rdparty  # noqa: F401
    from .glob import cm_global       # noqa: F401

    if os.environ.get('ENABLE_LEGACY_COMFYUI_MANAGER_FRONT', 'false') == 'true' or ENABLE_LEGACY_COMFYUI_MANAGER_FRONT_DEFAULT:
        try:
            import nodes
            nodes.EXTENSION_WEB_DIRS['comfyui-manager-legacy'] = os.path.join(os.path.dirname(__file__), 'js')
        except Exception as e:
            print("Error enabling legacy ComfyUI Manager frontend:", e)

"""
Salvatore Nodes - ComfyUI Custom Node Suite
Refactored version with nodes organized by category in separate files.
"""
import importlib.util
import os
import sys

# Get the directory where this __init__.py is located
_module_dir = os.path.dirname(os.path.abspath(__file__))

# List of module files to load
_module_files = [
    'salvatore_loaders',
    'salvatore_sampling',
    'salvatore_conditioning',
    'salvatore_latent',
    'salvatore_z_image_latent',
    'salvatore_star_qwen_image_ratio',
    'salvatore_image',
    'salvatore_inpainting',
    'salvatore_upscaling',
    'salvatore_numbers',
    'salvatore_text',
    'salvatore_io',
    'salvatore_utils',
]

# Load each module from the same directory
for _module_name in _module_files:
    _module_path = os.path.join(_module_dir, f"{_module_name}.py")
    _spec = importlib.util.spec_from_file_location(_module_name, _module_path)
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_module_name] = _module
    _spec.loader.exec_module(_module)
    # Store reference for later use
    globals()[_module_name] = _module

# Merge all NODE_CLASS_MAPPINGS into a single dictionary
NODE_CLASS_MAPPINGS = {}
NODE_CLASS_MAPPINGS.update(salvatore_loaders.NODE_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(salvatore_sampling.NODE_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(salvatore_conditioning.NODE_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(salvatore_latent.NODE_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(salvatore_z_image_latent.NODE_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(salvatore_star_qwen_image_ratio.NODE_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(salvatore_image.NODE_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(salvatore_inpainting.NODE_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(salvatore_upscaling.NODE_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(salvatore_numbers.NODE_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(salvatore_text.NODE_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(salvatore_io.NODE_CLASS_MAPPINGS)

# Merge all NODE_DISPLAY_NAME_MAPPINGS
NODE_DISPLAY_NAME_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS.update(getattr(salvatore_loaders, 'NODE_DISPLAY_NAME_MAPPINGS', {}))
NODE_DISPLAY_NAME_MAPPINGS.update(getattr(salvatore_sampling, 'NODE_DISPLAY_NAME_MAPPINGS', {}))
NODE_DISPLAY_NAME_MAPPINGS.update(getattr(salvatore_conditioning, 'NODE_DISPLAY_NAME_MAPPINGS', {}))
NODE_DISPLAY_NAME_MAPPINGS.update(getattr(salvatore_latent, 'NODE_DISPLAY_NAME_MAPPINGS', {}))
NODE_DISPLAY_NAME_MAPPINGS.update(getattr(salvatore_z_image_latent, 'NODE_DISPLAY_NAME_MAPPINGS', {}))
NODE_DISPLAY_NAME_MAPPINGS.update(getattr(salvatore_star_qwen_image_ratio, 'NODE_DISPLAY_NAME_MAPPINGS', {}))
NODE_DISPLAY_NAME_MAPPINGS.update(getattr(salvatore_image, 'NODE_DISPLAY_NAME_MAPPINGS', {}))
NODE_DISPLAY_NAME_MAPPINGS.update(getattr(salvatore_inpainting, 'NODE_DISPLAY_NAME_MAPPINGS', {}))
NODE_DISPLAY_NAME_MAPPINGS.update(getattr(salvatore_upscaling, 'NODE_DISPLAY_NAME_MAPPINGS', {}))
NODE_DISPLAY_NAME_MAPPINGS.update(getattr(salvatore_numbers, 'NODE_DISPLAY_NAME_MAPPINGS', {}))
NODE_DISPLAY_NAME_MAPPINGS.update(getattr(salvatore_text, 'NODE_DISPLAY_NAME_MAPPINGS', {}))
NODE_DISPLAY_NAME_MAPPINGS.update(getattr(salvatore_io, 'NODE_DISPLAY_NAME_MAPPINGS', {}))

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

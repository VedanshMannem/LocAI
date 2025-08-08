# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

# Import PyInstaller classes
block_cipher = None

# Collect llama-cpp-python binaries automatically
llama_binaries = collect_dynamic_libs('llama_cpp')

# Additional binaries if needed (usually auto-detected)
additional_binaries = []

# Collect all model data
model_data = []

# Add Phi-3 model if it exists
phi3_model = 'models/Phi-3-mini-4k-instruct-q4.gguf'
if os.path.exists(phi3_model):
    model_data.append((phi3_model, 'models/'))

# Add sentence-transformers model if it exists
sentence_model_dir = 'models/all-MiniLM-L6-v2'
if os.path.exists(sentence_model_dir):
    for root, dirs, files in os.walk(sentence_model_dir):
        for file in files:
            src = os.path.join(root, file)
            # Keep the relative path structure
            rel_path = os.path.relpath(src, 'models')
            model_data.append((src, f'models/{rel_path}'))

# Collect sentence-transformers data files
try:
    st_data = collect_data_files('sentence_transformers')
    model_data.extend(st_data)
except:
    pass

# Collect transformers data files
try:
    transformers_data = collect_data_files('transformers')
    model_data.extend(transformers_data)
except:
    pass

a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=llama_binaries + additional_binaries,
    datas=model_data + [
        ('*.py', '.'),  # Include all Python files
    ],
    hiddenimports=[
        'llama_cpp',
        'llama_cpp.llama_cpp', 
        'sentence_transformers',
        'transformers',
        'torch',
        'numpy',
        'faiss',
        'customtkinter',
        'tkinter',
        'threading',
        'huggingface_hub',
        'ctypes',
        'ctypes.util',
        'pkg_resources.py2_warn',
        'sklearn.utils._cython_blas',
        'sklearn.neighbors.typedefs',
        'sklearn.neighbors.quad_tree',
        'sklearn.tree._utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LocAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add 'icon.ico' if you have one

)
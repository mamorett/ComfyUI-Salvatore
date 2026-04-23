"""
Salvatore Nodes - Utility Functions
Shared helper functions used across multiple node files.
"""
import os
import json
import hashlib
import re
import random
import numpy as np
import torch
from PIL import Image, ImageOps, ImageFilter, ImageDraw
from PIL.PngImagePlugin import PngInfo
import piexif
import piexif.helper
import folder_paths
from datetime import datetime

MAX_RESOLUTION = 8192


# Tensor to PIL conversion
def tensor2pil(image):
    """Convert torch tensor to PIL Image."""
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))


# PIL to Tensor conversion
def pil2tensor(image):
    """Convert PIL Image to torch tensor."""
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


# Timestamp utilities
def get_timestamp(time_format="%Y-%m-%d-%H%M%S"):
    """Get current timestamp as string."""
    now = datetime.now()
    try:
        timestamp = now.strftime(time_format)
    except:
        timestamp = now.strftime("%Y-%m-%d-%H%M%S")
    return timestamp


def make_filename(filename="ComfyUI", seed={"seed": 0}, modelname="sd", counter=0, time_format="%Y-%m-%d-%H%M%S"):
    """
    Build filename using format tokens:
    %time - timestamp using time_format
    %model - model name
    %seed - seed value
    %counter - counter integer
    """
    timestamp = get_timestamp(time_format)

    filename = filename.replace("%time", timestamp)
    filename = filename.replace("%model", modelname)
    filename = filename.replace("%seed", str(seed))
    filename = filename.replace("%counter", str(counter))

    if filename == "":
        filename = timestamp
    return filename


def make_comment(positive="no positive prompt info", negative="no negative prompt info", 
                 modelname="unknown", seed=-1, info=None):
    """Create comment string with prompt and generation info."""
    comment = ""
    if info is None:
        comment = "Positive prompt:\n" + positive + "\nNegative prompt:\n" + negative + \
                  "\nModel: " + modelname + "\nSeed: " + str(seed)
        return comment
    else:
        # Reformat to stop long precision
        try:
            info['CFG scale: '] = "{:.2f}".format(info['CFG scale: '])
        except:
            pass
        try:
            info['Denoising strength: '] = "{:.2f}".format(info['Denoising strength: '])
        except:
            pass

        comment = "Positive prompt:\n" + positive + "\nNegative prompt:\n" + negative + \
                  "\nModel: " + modelname
        for key in info:
            newline = "\n" + key + str(info[key])
            comment += newline
    return comment


# Text file writing helper
def write_text_file(file_path, content):
    """Write content to a text file."""
    try:
        with open(file_path, 'w') as f:
            f.write(content)
    except OSError:
        print(f'Error: Unable to save file `{file_path}`')


# Image save helper
def save_images_to_output(images, output_path, path, filename_prefix="ComfyUI", 
                          comment="", extension='png', quality=100, 
                          prompt=None, extra_pnginfo=None):
    """
    Save images to output directory with metadata.
    Returns list of paths for UI.
    """
    img_count = 1
    paths = list()
    
    for image in images:
        i = 255. * image.cpu().numpy()
        img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
        metadata = PngInfo()

        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                metadata.add_text(x, json.dumps(extra_pnginfo[x]))
        metadata.add_text("parameters", comment)
        metadata.add_text("comment", comment)
        
        if images.size()[0] > 1:
            filename_prefix += "_{:02d}".format(img_count)

        file = f"{filename_prefix}.{extension}"
        
        if extension == 'png':
            img.save(os.path.join(output_path, file), comment=comment, pnginfo=metadata, optimize=True)
        elif extension == 'webp':
            img.save(os.path.join(output_path, file), quality=quality)
        elif extension == 'jpeg':
            img.save(os.path.join(output_path, file), quality=quality, comment=comment, optimize=True)
        elif extension == 'tiff':
            img.save(os.path.join(output_path, file), quality=quality, optimize=True)
        else:
            img.save(os.path.join(output_path, file))
            
        paths.append({
            "filename": file,
            "subfolder": path,
            "type": "output"
        })
        img_count += 1
        
    return paths

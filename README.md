# ComfyUI-Salvatore

A comprehensive collection of custom nodes for ComfyUI, providing advanced tools for image generation workflows including sampling, conditioning, latent manipulation, image processing, upscaling, and I/O operations.

## Installation

Clone this repository into your ComfyUI custom nodes directory:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/yourusername/ComfyUI-Salvatore.git
```

Restart ComfyUI after installation.

## Requirements

- ComfyUI
- Python 3.8+
- PIL (Pillow)
- NumPy
- piexif

## Nodes Overview

Nodes are organized into the following categories:

### Salvatore Nodes/loaders

- **Salvatore Checkpoint Loader w/Name** - Load checkpoint models and return MODEL, CLIP, VAE, and model name string.

### Salvatore Nodes/sampling

- **Salvatore KSampler Advanced** - Advanced KSampler with full control over sampling parameters, returns LATENT and INFO dictionary.
- **Salvatore Alternating KSampler Advanced** - KSampler that alternates between prompts using `<A|B>` syntax for dynamic prompt variation.

### Salvatore Nodes/conditioning

- **Salvatore CLIP Positive-Negative** - Encode positive and negative prompts from text.
- **Salvatore CLIP Positive-Negative w/Text** - Encode prompts and return the text strings as well.
- **Salvatore CLIP Positive-Negative XL** - SDXL-compatible CLIP encoding with crop/target coordinates.
- **Salvatore CLIP Positive-Negative XL w/Text** - SDXL encoding with text output.
- **Salvatore CLIP +/- w/Text Unified** - Unified CLIP text encoder supporting both SD1.5 and SDXL.

### Salvatore Nodes/latent

- **Salvatore Empty Latent by Size** - Create empty latent by explicit width and height, returns width/height outputs.
- **Salvatore Empty Latent by Ratio** - Create empty latent by aspect ratio and short side dimension.
- **Salvatore Empty Latent by Pixels** - Create empty latent by aspect ratio and megapixels total.
- **Salvatore SDXL Quick Empty Latent** - Quick SDXL latent with preset resolutions.
- **Salvatore SDXL Resolution Multiplier** - Multiply existing resolution by a factor.

### Salvatore Nodes/image

- **Salvatore Grayscale Image** - Convert image to grayscale.
- **Salvatore Image Load with Metadata** - Load image and extract prompt metadata, including workflow-based "magic" prompt extraction.
- **Salvatore Build Filename String** - Build filename from format string and inputs (%time_%seed, etc.).

### Salvatore Nodes/upscaling

- **Salvatore Image Scale By Factor** - Scale image by a factor (0.1 to 8.0).
- **Salvatore Image Scale by Shortside** - Scale image to match short side dimension, returns width/height.
- **Salvatore SDXL Quick Image Scale** - Quick SDXL image scaling with preset resolutions.
- **Salvatore Upscale by Factor with Model** - Upscale image using an upscaling model.

### Salvatore Nodes/text

- **Salvatore Time String** - Generate timestamp string in various formats.
- **Salvatore Simple Pattern Replace** - Replace patterns in string with values from a list.
- **Salvatore Simple String Combine** - Append or prepend string with optional separator.
- **Salvatore Prompt Weight** - Add weight to prompt text using `(text:weight)` syntax.

### Salvatore Nodes/IO

- **Salvatore Image Save with Prompt** - Save image with prompt metadata.
- **Salvatore Image Save with Prompt/Info** - Save image with prompt and generation info metadata.
- **Salvatore Image Save with Prompt File** - Save image and prompt to separate files.
- **Salvatore Image Save with Prompt/Info File** - Save image with prompt/info to separate files.
- **Salvatore Save Prompt** - Save prompt to text file.
- **Salvatore Save Prompt/Info** - Save prompt with info to text file.
- **Salvatore Save Positive Prompt** - Save positive prompt only to text file.
- **Salvatore Load Workflow and Extract Prompt** - Load a JSON workflow from input and extract positive prompt(s) from it.

## New Features

### Salvatore Load Workflow and Extract Prompt

This node accepts JSON workflow content as a STRING input and extracts positive prompts using intelligent CLIPTextEncode node detection. Perfect for workflows where JSON files are hosted on remote servers and cannot be accessed via ComfyUI's filesystem.

**Inputs:**
- `json_workflow` (STRING) - JSON workflow content from any connected node (e.g., HTTP/API nodes)

**Outputs:**
- `positive` (STRING) - Extracted positive prompt text
- `json_content` (STRING) - Full JSON workflow content as formatted string

**Use Case:** Extract prompts from remote workflow JSON files without needing filesystem access.

## Workflow Examples

### Basic SD1.5 Workflow
```
Checkpoint Loader → CLIP Text (+/-) → KSampler → VAE Decode → Image Save
```

### SDXL Workflow
```
Checkpoint Loader → CLIP Text XL → KSampler Advanced → VAE Decode → Image Save with Info
```

### Dynamic Prompt Alternation
```
Checkpoint Loader → Alternating KSampler → Image Save
```
Use `<promptA|promptB>` syntax in prompts for sequential alternation.

### Remote Workflow JSON Extraction
```
HTTP Request (JSON) → Load Workflow and Extract Prompt → CLIP Text → KSampler
```

## Tips

- Use the **INFO** output from KSampler nodes to pass generation metadata to save nodes.
- The **Image Load with Metadata** node can extract "magic" prompts from workflow metadata embedded in PNG files.
- For SDXL workflows, use the **CLIP +/- w/Text Unified** node and select "SDXL" conditioner.
- The **Simple Pattern Replace** node supports random selection from lists for variation.

## License

MIT License

## Credits

Created and maintained by Salvatore.

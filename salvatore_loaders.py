"""
Salvatore Nodes - Loaders
Checkpoint and model loading nodes.
"""
import comfy.sd
import folder_paths


class SalvatoreCheckpointLoaderModelName:
    """Load checkpoint by name and return model, clip, VAE, and model name."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "ckpt_name": (folder_paths.get_filename_list("checkpoints"), ),
                             }}
    
    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "STRING",)
    RETURN_NAMES = ("MODEL", "CLIP", "VAE", "modelname")
    FUNCTION = "load_checkpoint"
    CATEGORY = "Salvatore Nodes/loaders"

    def load_checkpoint(self, ckpt_name, output_vae=True, output_clip=True):
        ckpt_path = folder_paths.get_full_path("checkpoints", ckpt_name)
        name = self.parse_name(ckpt_name)

        out = comfy.sd.load_checkpoint_guess_config(ckpt_path, output_vae=True, output_clip=True, 
                                                    embedding_directory=folder_paths.get_folder_paths("embeddings"))

        new_out = list(out)
        new_out.pop()
        new_out.append(name)
        out = tuple(new_out)

        return (out)

    def parse_name(self, ckpt_name):
        path = ckpt_name
        filename = path.split("/")[-1]
        filename = filename.split(".")[:-1]
        filename = ".".join(filename)
        return filename


NODE_CLASS_MAPPINGS = {
    "SalvatoreCheckpointLoaderModelName": SalvatoreCheckpointLoaderModelName,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SalvatoreCheckpointLoaderModelName": "Salvatore Checkpoint Loader w/Name",
}

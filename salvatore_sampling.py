"""
Salvatore Nodes - Sampling
KSampler and sampling-related nodes.
"""
import comfy.samplers
from nodes import common_ksampler


class SalvatoreKSamplerAdvanced:
    """Advanced KSampler with full control over sampling parameters."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required":
                    {"model": ("MODEL",),
                    "add_noise": (["enable", "disable"], ),
                    "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                    "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                    "cfg": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0}),
                    "sampler_name": (comfy.samplers.KSampler.SAMPLERS, ),
                    "scheduler": (comfy.samplers.KSampler.SCHEDULERS, ),
                    "positive": ("CONDITIONING", ),
                    "negative": ("CONDITIONING", ),
                    "latent_image": ("LATENT", ),
                    "start_at_step": ("INT", {"default": 0, "min": 0, "max": 10000}),
                    "end_at_step": ("INT", {"default": 10000, "min": 0, "max": 10000}),
                    "return_with_leftover_noise": (["disable", "enable"], ),
                    "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                     }
                }

    RETURN_TYPES = ("LATENT", "INFO",)
    FUNCTION = "sample"
    CATEGORY = "Salvatore Nodes/sampling"

    def sample(self, model, add_noise, seed, steps, cfg, sampler_name, scheduler, positive, 
               negative, latent_image, start_at_step, end_at_step, return_with_leftover_noise, denoise):
        force_full_denoise = False
        if return_with_leftover_noise == "enable":
            force_full_denoise = False
        disable_noise = False
        if add_noise == "disable":
            disable_noise = True

        info = {
            "Seed: ": seed, 
            "Steps: ": steps, 
            "CFG scale: ": cfg, 
            "Sampler: ": sampler_name, 
            "Scheduler: ": scheduler, 
            "Start at step: ": start_at_step, 
            "End at step: ": end_at_step, 
            "Denoising strength: ": denoise
        }
        
        samples = common_ksampler(
            model, seed, steps, cfg, sampler_name, scheduler, positive, negative, latent_image,
            denoise=denoise, disable_noise=disable_noise, start_step=start_at_step, 
            last_step=end_at_step, force_full_denoise=force_full_denoise
        )

        return (samples[0], info)


class SalvatoreAlternatingKSamplerAdvanced:
    """KSampler that alternates between prompts using <A|B> syntax."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required":
                    {"model": ("MODEL",),
                    "add_noise": (["enable", "disable"], ),
                    "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                    "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                    "cfg": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0}),
                    "sampler_name": (comfy.samplers.KSampler.SAMPLERS, ),
                    "scheduler": (comfy.samplers.KSampler.SCHEDULERS, ),
                    "clip": ("CLIP", ),
                    "positive_prompt": ("STRING", {"forceInput": True }),
                    "negative_prompt": ("STRING", {"forceInput": True }),
                    "latent_image": ("LATENT", ),
                    "start_at_step": ("INT", {"default": 0, "min": 0, "max": 10000}),
                    "end_at_step": ("INT", {"default": 10000, "min": 0, "max": 10000}),
                    "return_with_leftover_noise": (["disable", "enable"], ),
                    "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                     }
                }

    RETURN_TYPES = ("LATENT",)
    FUNCTION = "sample"
    CATEGORY = "Salvatore Nodes/sampling"

    def sample(self, model, add_noise, seed, steps, cfg, sampler_name, scheduler, clip, 
               positive_prompt, negative_prompt, latent_image, start_at_step, end_at_step, 
               return_with_leftover_noise, denoise):
        noise_seed = seed
        force_full_denoise = False
        if return_with_leftover_noise == "enable":
            force_full_denoise = False
        disable_noise = False
        if add_noise == "disable":
            disable_noise = True

        # Alternating prompt parser
        # Syntax: {A|B} will sequentially alternate between A and B
        def parse_prompt(input_string, stepnum):
            def replace_match(match):
                options = match.group(1).split('|')
                return options[(stepnum - 1) % len(options)]

            pattern = r'<(.*?)>'
            parsed_string = re.sub(pattern, replace_match, input_string)
            return parsed_string

        import re
        
        latent_input = latent_image
        for step in range(0, steps):
            positive_txt = parse_prompt(positive_prompt, step + 1)
            positive = [[clip.encode(positive_txt), {}]]
            negative_txt = parse_prompt(negative_prompt, step + 1)
            negative = [[clip.encode(negative_txt), {}]]

            if step < steps:
                force_full_denoise = True
            if step > 0:
                disable_noise = True
                denoise = (steps - step) / (steps)

            latent_image = common_ksampler(
                model, noise_seed, 1, cfg, sampler_name, scheduler, positive, negative, latent_input,
                denoise=denoise, disable_noise=disable_noise, start_step=start_at_step, 
                last_step=end_at_step, force_full_denoise=force_full_denoise
            )
            latent_input = latent_image[0]

        return latent_image


NODE_CLASS_MAPPINGS = {
    "SalvatoreKSamplerAdvanced": SalvatoreKSamplerAdvanced,
    "SalvatoreAlternatingKSamplerAdvanced": SalvatoreAlternatingKSamplerAdvanced,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SalvatoreKSamplerAdvanced": "Salvatore KSampler Advanced",
    "SalvatoreAlternatingKSamplerAdvanced": "Salvatore Alternating KSampler Advanced",
}

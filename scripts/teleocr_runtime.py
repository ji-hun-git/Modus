"""Shared pinned TeleOCR inference, used only inside an isolated worker process."""
import importlib.util
import os
import socket
import time

from teleocr_assets import snapshot_dir, spec, verify


def deny_network(*args, **kwargs):
    raise RuntimeError('Network disabled in the OCR inference worker')


def bounded_repetition_penalty(value):
    if type(value) not in (int, float) or not 1.0 <= value <= 1.2:
        raise ValueError('Local OCR repetition penalty must be between 1.0 and 1.2')
    return float(value)


class TeleOCRRuntime:
    def __init__(self, resolution='primary'):
        self.config = spec()
        if resolution not in ('primary', 'fallback'):
            raise ValueError('Unsupported OCR resolution mode')
        self.resolution = resolution
        self.max_pixels = self.config['max_pixels' if resolution == 'primary' else 'fallback_max_pixels']
        if type(self.max_pixels) is not int or not 3136 <= self.max_pixels <= self.config['max_input_pixels']:
            raise ValueError('OCR processed pixel limit is invalid')
        self.repetition_penalty = bounded_repetition_penalty(self.config.get('repetition_penalty', 1.0))
        if verify():
            raise ValueError('Pinned model files missing or changed')
        if importlib.util.find_spec('kernels'):
            raise RuntimeError('Optional Hub kernels are not permitted')
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
            HF_HUB_DISABLE_TELEMETRY='1', HF_HUB_DISABLE_IMPLICIT_TOKEN='1')
        socket.create_connection = deny_network
        socket.socket.connect = deny_network
        import torch
        import transformers
        from transformers import AutoModel, AutoProcessor
        if transformers.__version__ != self.config['transformers']:
            raise RuntimeError('Use the audited Transformers version')
        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
            raise RuntimeError('The pinned experiment requires CUDA bfloat16 support')
        self.torch = torch
        started = time.perf_counter()
        model_dir = str(snapshot_dir())
        self.processor = AutoProcessor.from_pretrained(model_dir, local_files_only=True,
            trust_remote_code=False, use_fast=False, min_pixels=3136,
            max_pixels=self.max_pixels)
        self.model = AutoModel.from_pretrained(model_dir, local_files_only=True,
            trust_remote_code=True, torch_dtype=torch.bfloat16, use_safetensors=True,
            attn_implementation='sdpa').cuda().eval()
        self.model.generation_config.do_sample = False
        self.model.generation_config.temperature = None
        self.model.generation_config.top_p = None
        self.model.generation_config.top_k = None
        self.model_load_seconds = round(time.perf_counter() - started, 3)
        self.runtime = {'torch': torch.__version__, 'transformers': transformers.__version__,
            'cuda': torch.version.cuda, 'gpu': torch.cuda.get_device_name(),
            'dtype': 'bfloat16', 'attention': 'sdpa'}

    def read_page(self, image, page_no):
        started = time.perf_counter()
        prompt = self.processor.apply_chat_template([{'role': 'user', 'content': [
            {'type': 'image'}, {'type': 'text', 'text': self.config['prompt']}]}],
            tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[prompt], images=[image], padding=True,
            return_tensors='pt').to(device=self.model.device, dtype=self.model.dtype)
        input_tokens = inputs.input_ids.shape[1]
        if input_tokens > 4096:
            raise ValueError('Input token limit exceeded')
        with self.torch.inference_mode():
            ids = self.model.generate(**inputs, use_cache=True, do_sample=False,
                num_beams=1, max_new_tokens=self.config['max_new_tokens'],
                repetition_penalty=self.repetition_penalty)
        generated = ids[0, inputs.input_ids.shape[1]:].cpu().tolist()
        text = self.processor.batch_decode([generated], skip_special_tokens=True,
            clean_up_tokenization_spaces=False)[0].strip()
        eos = self.model.generation_config.eos_token_id
        eos_ids = eos if isinstance(eos, list) else [eos]
        stopped = bool(generated and generated[-1] in eos_ids)
        return {'page': page_no, 'text': text, 'output_tokens': len(generated),
            'input_tokens': input_tokens, 'image_grid_thw': inputs.image_grid_thw.cpu().tolist(),
            'stop_reason': 'eos' if stopped else 'token_limit_or_other',
            'truncated': not stopped,
            'duration_seconds': round(time.perf_counter() - started, 3)}

    def metadata(self):
        return {'model': self.config['model'], 'revision': self.config['revision'],
            'mode': 'local-teleocr', 'runtime': self.runtime,
            'settings': {**{key: self.config[key] for key in ('prompt', 'max_new_tokens')},
                'resolution': self.resolution, 'max_pixels': self.max_pixels,
                'prompt_version': self.config.get('prompt_version', 'audited-text-v1'),
                'strategy_version': self.config.get('strategy_version', 'single-attempt-v1'),
                'repetition_penalty': self.repetition_penalty},
            'model_load_seconds': self.model_load_seconds,
            'peak_allocated_gpu_bytes': self.torch.cuda.max_memory_allocated()}

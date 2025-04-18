# Copyright 2025 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import math

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def check_causal_lm_output_quality(model_id, generated_text, max_perplexity_threshold=100.0):
    """
    Evaluates the quality of text generated by a causal language model by calculating its perplexity.

    Args:
        model_id: HuggingFace model identifier (e.g., "google/gemma2-2b")
        generated_text: The text generated by the exported model to evaluate
        max_perplexity_threshold: Maximum acceptable perplexity (lower is better)

    Returns:
        tuple: (is_quality_ok, reason) with boolean result and explanation
    """
    logging.info(f"Starting perplexity check with model '{model_id}' ...")
    # Load model and tokenizer
    model = AutoModelForCausalLM.from_pretrained(model_id)
    tokenizer = AutoTokenizer.from_pretrained(model_id)

    # Encode the text
    encodings = tokenizer(generated_text, return_tensors="pt")

    # Create input_ids for language modeling evaluation
    input_ids = encodings.input_ids

    # Move to the same device as the model
    input_ids = input_ids.to(model.device)

    with torch.no_grad():
        outputs = model(input_ids=input_ids, labels=input_ids, use_cache=True)

    # Get the loss (negative log-likelihood)
    loss = outputs.loss.item()

    # Calculate perplexity (exp of the average negative log-likelihood)
    perplexity = math.exp(loss)

    is_quality_ok = perplexity <= max_perplexity_threshold
    if is_quality_ok:
        logging.info(f"✓ Perplexity check passed: {perplexity:.2f} <= {max_perplexity_threshold}")
    else:
        logging.warning(f"✗ Perplexity check failed: {perplexity:.2f} > {max_perplexity_threshold}")

    return is_quality_ok


def check_close_recursively(eager_outputs, exported_outputs, atol=1e-4, rtol=1e-4):
    is_close = False
    if isinstance(eager_outputs, torch.Tensor):
        torch.testing.assert_close(eager_outputs, exported_outputs, atol=atol, rtol=rtol)
        return True
    elif isinstance(eager_outputs, (tuple, list)):
        for eager_output, exported_output in zip(eager_outputs, exported_outputs):
            is_close = is_close or check_close_recursively(eager_output, exported_output)
        return is_close
    elif isinstance(eager_outputs, dict):
        for key in eager_outputs:
            is_close = is_close or check_close_recursively(eager_outputs[key], exported_outputs[key])
        return is_close
    return is_close

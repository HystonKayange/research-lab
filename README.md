# transformer-lab

An experimentation lab for understanding transformers from the ground up — and earning the right to
*improve* them. Goal: internalize the attention math by building it from scratch, then run rigorous
small-scale experiments to find something real.

> "Attention Is All You Need" → build it → measure it → change one thing → measure again.

## Why

Long-standing itch: deeply understand the transformer architecture, play with the math, and find an
innovative way to improve models. The honest path to that isn't inventing on day one — it's the
**small-scale training-science** loop (à la Karpathy's nanoGPT and the modded-nanoGPT speedrun, where
real improvements like the Muon optimizer were actually found on consumer-scale hardware):

> reproduce a baseline → measure it rigorously → change **one** thing → measure with proper controls → repeat.

The edge here is **rigor**: small-scale ML results are noisy and most repos report a single run.
Carrying over the statistical discipline from `skill-eval/skill-probe` (multiple seeds, confidence
intervals, "one run lies") is what separates a real result from noise.

## Compute

RTX 5070 (Blackwell, sm_120, ~12 GB) on WSL2. Verified ready: PyTorch 2.11.0+cu128 ships native
sm_120 kernels, bf16 autocast works, full train step runs on-GPU. Comfortable range: char-level models
(minutes) up through GPT-2-small / nanoGPT scale (124M) with small batch + gradient accumulation.
Don't run `ollama` and a training job at once — they compete for the 12 GB.

## Arc

1. **`transformer-from-scratch/`** — implement attention → multi-head → blocks → full GPT → training
   loop by hand, with the math explained at each step. Train a tiny char-level model so loss drops on
   day one. (This is itself a shippable, starrable public repo.)
2. **ablation harness** — fixed compute budget, multiple seeds, CIs, clean logging. skill-probe's
   philosophy pointed at training runs.
3. **innovate on one axis** — attention variant / positional encoding / optimizer / init / norm — run
   controlled experiments until something surprises you. Write it up (rigorous negative results count).

## Status

Scaffolding. Environment verified (see Compute). Next: build the from-scratch transformer.

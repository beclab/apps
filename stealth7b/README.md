# Model Description
This is a GGUF version of [jan-hq/stealth-v1.3](https://huggingface.co/jan-hq/stealth-v1.3)
- Model creator: [jan-hq](https://huggingface.co/jan-hq)
- Original model: [stealth-v1.3](https://huggingface.co/jan-hq/stealth-v1.3)
- Model description: [Readme](https://huggingface.co/jan-hq/stealth-v1.3/blob/main/README.md)

[Jan](https://jan.ai/) | [Discord](https://discord.gg/AsJ8krTT3N)

# Prompt template

ChatML
```
<|im_start|>system
{system_message}<|im_end|>
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant
```


# Open LLM Leaderboard Evaluation Results

Detailed results can be found [here](https://huggingface.co/datasets/open-llm-leaderboard/details_jan-hq__stealth-v1.3)

|             Metric              |Value|
|---------------------------------|----:|
|Avg.                             |71.12|
|AI2 Reasoning Challenge (25-Shot)|67.49|
|HellaSwag (10-Shot)              |86.74|
|MMLU (5-Shot)                    |64.45|
|TruthfulQA (0-shot)              |55.71|
|Winogrande (5-shot)              |80.74|
|GSM8k (5-shot)                   |71.57|



# About Jan
Jan believes in the need for an open-source AI ecosystem and is building the infra and tooling to allow open-source AIs to compete on a level playing field with proprietary ones.

Jan's long-term vision is to build a cognitive framework for future robots, who are practical, useful assistants for humans and businesses in everyday life.

# Jan Model Converter
This is a repository for the [open-source converter](https://github.com/janhq/model-converter). We would be grateful if the community could contribute and strengthen this repository. We are aiming to expand the repo that can convert into various types of format.

# Openchat 3.5 1210 - GGUF
- Model creator: [OpenChat](https://huggingface.co/openchat)
- Model card: [openchat-3.5-1210-GGUF](https://huggingface.co/TheBloke/openchat-3.5-1210-GGUF)
- Original model card: [Openchat 3.5 1210](https://huggingface.co/openchat/openchat-3.5-1210)


## Description

This repo contains GGUF format model files for [OpenChat's Openchat 3.5 1210](https://huggingface.co/openchat/openchat-3.5-1210).

These files were quantised using hardware kindly provided by [Massed Compute](https://massedcompute.com/).

## Prompt template: OpenChat-Correct

```
GPT4 Correct User: {prompt}<|end_of_turn|>GPT4 Correct Assistant:
```

## Compatibility

These quantised GGUFv2 files are compatible with llama.cpp from August 27th onwards, as of commit [d0cee0d](https://github.com/ggerganov/llama.cpp/commit/d0cee0d36d5be95a0d9088b674dbb27354107221)

They are also compatible with many third party UIs and libraries - please see the list at the top of this README.


## Discord

For further support, and discussions on these models and AI in general, join us at:

[TheBloke AI's Discord server](https://discord.gg/theblokeai)

## Thanks, and how to contribute

Thanks to the [chirper.ai](https://chirper.ai) team!

Thanks to Clay from [gpus.llm-utils.org](llm-utils)!

I've had a lot of people ask if they can contribute. I enjoy providing models and helping people, and would love to be able to spend even more time doing it, as well as expanding into new projects like fine tuning/training.

If you're able and willing to contribute it will be most gratefully received and will help me to keep providing more models, and to start work on new AI projects.

Donaters will get priority support on any and all AI/LLM/model questions and requests, access to a private Discord room, plus other benefits.

* Patreon: https://patreon.com/TheBlokeAI
* Ko-Fi: https://ko-fi.com/TheBlokeAI

**Special thanks to**: Aemon Algiz.

**Patreon special mentions**: Michael Levine, 阿明, Trailburnt, Nikolai Manek, John Detwiler, Randy H, Will Dee, Sebastain Graf, NimbleBox.ai, Eugene Pentland, Emad Mostaque, Ai Maven, Jim Angel, Jeff Scroggin, Michael Davis, Manuel Alberto Morcote, Stephen Murray, Robert, Justin Joy, Luke @flexchar, Brandon Frisco, Elijah Stavena, S_X, Dan Guido, Undi ., Komninos Chatzipapas, Shadi, theTransient, Lone Striker, Raven Klaugh, jjj, Cap'n Zoog, Michel-Marie MAUDET (LINAGORA), Matthew Berman, David, Fen Risland, Omer Bin Jawed, Luke Pendergrass, Kalila, OG, Erik Bjäreholt, Rooh Singh, Joseph William Delisle, Dan Lewis, TL, John Villwock, AzureBlack, Brad, Pedro Madruga, Caitlyn Gatomon, K, jinyuan sun, Mano Prime, Alex, Jeffrey Morgan, Alicia Loh, Illia Dulskyi, Chadd, transmissions 11, fincy, Rainer Wilmers, ReadyPlayerEmma, knownsqashed, Mandus, biorpg, Deo Leter, Brandon Phillips, SuperWojo, Sean Connelly, Iucharbius, Jack West, Harry Royden McLaughlin, Nicholas, terasurfer, Vitor Caleffi, Duane Dunston, Johann-Peter Hartmann, David Ziegler, Olakabola, Ken Nordquist, Trenton Dambrowitz, Tom X Nguyen, Vadim, Ajan Kanaga, Leonard Tan, Clay Pascal, Alexandros Triantafyllidis, JM33133, Xule, vamX, ya boyyy, subjectnull, Talal Aujan, Alps Aficionado, wassieverse, Ari Malik, James Bentley, Woland, Spencer Kim, Michael Dempsey, Fred von Graf, Elle, zynix, William Richards, Stanislav Ovsiannikov, Edmond Seymore, Jonathan Leane, Martin Kemka, usrbinkat, Enrico Ros


Thank you to all my generous patrons and donaters!

And thank you again to a16z for their generous grant.

# Original model card: OpenChat's Openchat 3.5 1210
```
Advancing Open-source Language Models with Mixed-Quality Data
```
**Table of Contents**
1. [Usage](#usage)
2. [Benchmarks](#benchmarks)
3. [Limitations](#limitations)
4. [License](#license)
5. [Dataset Details](#dataset-details)
6. [Citation](#citation)
7. [Acknowledgements](#acknowledgements)


## Usage
### Conversation templates

💡 **Default Mode (GPT4 Correct)**: Best for coding, chat and general tasks

```
GPT4 Correct User: Hello<|end_of_turn|>GPT4 Correct Assistant: Hi<|end_of_turn|>GPT4 Correct User: How are you today?<|end_of_turn|>GPT4 Correct Assistant:
```

🧮 **Mathematical Reasoning Mode**: Tailored for solving math problems

```
Math Correct User: 10.3 − 7988.8133=<|end_of_turn|>Math Correct Assistant:
```

⚠️ **Notice:** Remember to set `<|end_of_turn|>` as end of generation token.

The default (GPT4 Correct) template is also available as the integrated `tokenizer.chat_template`,
which can be used instead of manually specifying the template:

```python
messages = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi"},
    {"role": "user", "content": "How are you today?"}
]
tokens = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
assert tokens == [1, 420, 6316, 28781, 3198, 3123, 1247, 28747, 22557, 32000, 420, 6316, 28781, 3198, 3123, 21631, 28747, 15359, 32000, 420, 6316, 28781, 3198, 3123, 1247, 28747, 1602, 460, 368, 3154, 28804, 32000, 420, 6316, 28781, 3198, 3123, 21631, 28747]
```

## (Experimental) Evaluator / Feedback Capabilities

We've included evaluator capabilities in this release to advance open-source models as evaluators. You can use `Default Mode (GPT4 Correct)` with the following prompt (same as [Prometheus](https://huggingface.co/datasets/kaist-ai/Feedback-Collection)) to evaluate a response.

```
###Task Description:
An instruction (might include an Input inside it), a response to evaluate, a reference answer that gets a score of 5, and a score rubric representing a evaluation criteria are given.
1. Write a detailed feedback that assess the quality of the response strictly based on the given score rubric, not evaluating in general.
2. After writing a feedback, write a score that is an integer between 1 and 5. You should refer to the score rubric.
3. The output format should look as follows: "Feedback: (write a feedback for criteria) [RESULT] (an integer number between 1 and 5)"
4. Please do not generate any other opening, closing, and explanations.

###The instruction to evaluate:
{orig_instruction}

###Response to evaluate:
{orig_response}

###Reference Answer (Score 5):
{orig_reference_answer}

###Score Rubrics:
[{orig_criteria}]
Score 1: {orig_score1_description}
Score 2: {orig_score2_description}
Score 3: {orig_score3_description}
Score 4: {orig_score4_description}
Score 5: {orig_score5_description}

###Feedback:
```

## Benchmarks

| Model              | # Params | Average  | MT-Bench     | HumanEval       | BBH MC   | AGIEval  | TruthfulQA    | MMLU         | GSM8K        | BBH CoT     |
|--------------------|----------|----------|--------------|-----------------|----------|----------|---------------|--------------|--------------|-------------|
| OpenChat-3.5-1210  | **7B**   | **63.8** | 7.76         | **68.9**        | **49.5** | **48.0** | **61.8**      | 65.3         | **77.3**     | 61.8        |
| OpenChat-3.5       | **7B**   | 61.6     | 7.81         | 55.5            | 47.6     | 47.4     | 59.1          | 64.3         | **77.3**     | 63.5        |
| ChatGPT (March)*   | ?        | 61.5     | **7.94**     | 48.1            | 47.6     | 47.1     | 57.7          | **67.3**     | 74.9         | **70.1**    |
|                    |          |          |              |                 |          |          |               |              |              |             |
| OpenHermes 2.5     | 7B       | 59.3     | 7.54         | 48.2            | 49.4     | 46.5     | 57.5          | 63.8         | 73.5         | 59.9        |
| OpenOrca Mistral   | 7B       | 52.7     | 6.86         | 38.4            | 49.4     | 42.9     | 45.9          | 59.3         | 59.1         | 58.1        |
| Zephyr-β^          | 7B       | 34.6     | 7.34         | 22.0            | 40.6     | 39.0     | 40.8          | 39.8         | 5.1          | 16.0        |
| Mistral            | 7B       | -        | 6.84         | 30.5            | 39.0     | 38.0     | -             | 60.1         | 52.2         | -           |

Evaluation Details
```
*: ChatGPT (March) results are from [GPT-4 Technical Report](https://arxiv.org/abs/2303.08774), [Chain-of-Thought Hub](https://github.com/FranxYao/chain-of-thought-hub), and our evaluation. Please note that ChatGPT is not a fixed baseline and evolves rapidly over time.

^: Zephyr-β often fails to follow few-shot CoT instructions, likely because it was aligned with only chat data but not trained on few-shot data.

**: Mistral and Open-source SOTA results are taken from reported results in instruction-tuned model papers and official repositories.

All models are evaluated in chat mode (e.g. with the respective conversation template applied). All zero-shot benchmarks follow the same setting as in the AGIEval paper and Orca paper. CoT tasks use the same configuration as Chain-of-Thought Hub, HumanEval is evaluated with EvalPlus, and MT-bench is run using FastChat. To reproduce our results, follow the instructions in [our repository](https://github.com/imoneoi/openchat/#benchmarks).
```

### HumanEval+

| Model                       | Size     | HumanEval+ pass@1 |
|-----------------------------|----------|------------|
| ChatGPT (December 12, 2023) | -        | 64.6       |
| WizardCoder-Python-34B-V1.0 | 34B      | 64.6       |
| **OpenChat 3.5 (Dec 10)**   | **7B**   | **63.4**   |
| OpenHermes 2.5              | 7B       | 41.5       |

### OpenChat-3.5-1210 vs. Grok

|                   | License     | # Param | Average  | MMLU | HumanEval | MATH     | GSM8k    |
|-------------------|-------------|---------|----------|------|-----------|----------|----------|
| OpenChat 3.5 1210 | Apache-2.0  | **7B**  | **60.1** | 65.3 | **68.9**  | **28.9** | **77.3** |
| OpenChat 3.5      | Apache-2.0  | **7B**  | 56.4     | 64.3 | 55.5      | 28.6     | **77.3** |
| Grok-0            | Proprietary | 33B     | 44.5     | 65.7 | 39.7      | 15.7     | 56.8     |
| Grok-1            | Proprietary | ???B    | 55.8     | 73   | 63.2      | 23.9     | 62.9     |

*: Grok results are reported by [X.AI](https://x.ai/).

## 中文评估结果 / Chinese Evaluations

⚠️ Note that this model was not explicitly trained in Chinese (only < 0.1% of the data is in Chinese). 请注意本模型没有针对性训练中文（中文数据占比小于0.1%）。

### Multi-Level Multi-Discipline Chinese Evaluation Suite (CEVAL)


| Model    | Avg   | STEM  | Social Science | Humanities | Others |
|----------|-------|-------|----------------|------------|--------|
| ChatGPT  | 54.4  | 52.9  | 61.8           | 50.9       | 53.6   |
| OpenChat | 47.29 | 45.22 | 52.49          | 48.52      | 45.08  |

### Massive Multitask Language Understanding in Chinese (CMMLU, 5-shot)

| Models   | STEM  | Humanities | SocialSciences | Other | ChinaSpecific | Avg   |
|----------|-------|------------|----------------|-------|---------------|-------|
| ChatGPT  | 47.81 | 55.68      | 56.5           | 62.66 | 50.69         | 55.51 |
| OpenChat | 38.7  | 45.99      | 48.32          | 50.23 | 43.27         | 45.85 |


## Limitations

**Foundation Model Limitations**
Despite its advanced capabilities, OpenChat is still bound by the limitations inherent in its foundation models. These limitations may impact the model's performance in areas such as:

- Complex reasoning
- Mathematical and arithmetic tasks
- Programming and coding challenges

**Hallucination of Non-existent Information**
OpenChat may sometimes generate information that does not exist or is not accurate, also known as "hallucination". Users should be aware of this possibility and verify any critical information obtained from the model.

**Safety**
OpenChat may sometimes generate harmful, hate speech, biased responses, or answer unsafe questions. It's crucial to apply additional AI safety measures in use cases that require safe and moderated responses.

## License

Our OpenChat 3.5 code and models are distributed under the Apache License 2.0.

## Dataset Details

OpenChat 3.5 was trained with C-RLFT on a collection of publicly available high-quality instruction data, with a custom processing pipeline. We detail some notable subsets included here:

- [OpenChat ShareGPT](https://huggingface.co/datasets/openchat/openchat_sharegpt4_dataset)
- [Open-Orca with FLAN answers](https://huggingface.co/datasets/imone/OpenOrca_FLAN)
- [Feedback-Collection](https://huggingface.co/datasets/kaist-ai/Feedback-Collection)
- Capybara [1](https://huggingface.co/datasets/LDJnr/Pure-Dove) [2](https://huggingface.co/datasets/LDJnr/Verified-Camel) [3](https://huggingface.co/datasets/LDJnr/LessWrong-Amplify-Instruct)
- [GOAT](https://huggingface.co/datasets/tiedong/goat)
- [Glaive](https://huggingface.co/datasets/glaiveai/glaive-code-assistant)
- [MetaMathQA](https://huggingface.co/datasets/meta-math/MetaMathQA)
- [MathInstruct](https://huggingface.co/datasets/TIGER-Lab/MathInstruct)
- [OpenAssistant](https://huggingface.co/datasets/OpenAssistant/oasst_top1_2023-08-25)

## Citation

```
@article{wang2023openchat,
  title={OpenChat: Advancing Open-source Language Models with Mixed-Quality Data},
  author={Wang, Guan and Cheng, Sijie and Zhan, Xianyuan and Li, Xiangang and Song, Sen and Liu, Yang},
  journal={arXiv preprint arXiv:2309.11235},
  year={2023}
}
```

## Acknowledgments 

We extend our heartfelt gratitude to AutoMeta and caesus from Alignment Lab AI, LDJ and Teknium from Nous Research, alpin and TearGosling from Pygmalion AI for their substantial contributions to data collection and model training.

Special thanks go to Changling Liu from GPT Desk Pte. Ltd., Qiying Yu at Tsinghua University, Baochang Ma, and Hao Wan from 01.AI company for their generous provision of resources. We are also deeply grateful to Jianxiong Li and Peng Li at Tsinghua University for their insightful discussions.

Furthermore, we appreciate the developers behind the following projects for their significant contributions to our research: [Mistral](https://mistral.ai/), [Chain-of-Thought Hub](https://github.com/FranxYao/chain-of-thought-hub), [Llama 2](https://ai.meta.com/llama/), [Self-Instruct](https://arxiv.org/abs/2212.10560), [FastChat (Vicuna)](https://github.com/lm-sys/FastChat), [Alpaca](https://github.com/tatsu-lab/stanford_alpaca.git), and [StarCoder](https://github.com/bigcode-project/starcoder). Their work has been instrumental in driving our research forward.

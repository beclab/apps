# Yarn Mistral 7B 128K - GGUF
- Model creator: [NousResearch](https://huggingface.co/NousResearch)
- Model card: [Yarn-Mistral-7B-128k-GGUF](https://huggingface.co/TheBloke/Yarn-Mistral-7B-128k-GGUF)
- Original model card: [Yarn Mistral 7B 128K](https://huggingface.co/NousResearch/Yarn-Mistral-7b-128k)

## Description

This repo contains GGUF format model files for [NousResearch's Yarn Mistral 7B 128K](https://huggingface.co/NousResearch/Yarn-Mistral-7b-128k).

These files were quantised using hardware kindly provided by [Massed Compute](https://massedcompute.com/).


## Prompt template: None

```
{prompt}
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

**Patreon special mentions**: Brandon Frisco, LangChain4j, Spiking Neurons AB, transmissions 11, Joseph William Delisle, Nitin Borwankar, Willem Michiel, Michael Dempsey, vamX, Jeffrey Morgan, zynix, jjj, Omer Bin Jawed, Sean Connelly, jinyuan sun, Jeromy Smith, Shadi, Pawan Osman, Chadd, Elijah Stavena, Illia Dulskyi, Sebastain Graf, Stephen Murray, terasurfer, Edmond Seymore, Celu Ramasamy, Mandus, Alex, biorpg, Ajan Kanaga, Clay Pascal, Raven Klaugh, 阿明, K, ya boyyy, usrbinkat, Alicia Loh, John Villwock, ReadyPlayerEmma, Chris Smitley, Cap'n Zoog, fincy, GodLy, S_X, sidney chen, Cory Kujawski, OG, Mano Prime, AzureBlack, Pieter, Kalila, Spencer Kim, Tom X Nguyen, Stanislav Ovsiannikov, Michael Levine, Andrey, Trailburnt, Vadim, Enrico Ros, Talal Aujan, Brandon Phillips, Jack West, Eugene Pentland, Michael Davis, Will Dee, webtim, Jonathan Leane, Alps Aficionado, Rooh Singh, Tiffany J. Kim, theTransient, Luke @flexchar, Elle, Caitlyn Gatomon, Ari Malik, subjectnull, Johann-Peter Hartmann, Trenton Dambrowitz, Imad Khwaja, Asp the Wyvern, Emad Mostaque, Rainer Wilmers, Alexandros Triantafyllidis, Nicholas, Pedro Madruga, SuperWojo, Harry Royden McLaughlin, James Bentley, Olakabola, David Ziegler, Ai Maven, Jeff Scroggin, Nikolai Manek, Deo Leter, Matthew Berman, Fen Risland, Ken Nordquist, Manuel Alberto Morcote, Luke Pendergrass, TL, Fred von Graf, Randy H, Dan Guido, NimbleBox.ai, Vitor Caleffi, Gabriel Tamborski, knownsqashed, Lone Striker, Erik Bjäreholt, John Detwiler, Leonard Tan, Iucharbius


Thank you to all my generous patrons and donaters!

And thank you again to a16z for their generous grant.


# Original model card: Nous-Yarn-Mistral-7b-128k

[Preprint (arXiv)](https://arxiv.org/abs/2309.00071)
[GitHub](https://github.com/jquesnelle/yarn)
![yarn](https://raw.githubusercontent.com/jquesnelle/yarn/mistral/data/proofpile-long-small-mistral.csv.png)

## Model Description

Nous-Yarn-Mistral-7b-128k is a state-of-the-art language model for long context, further pretrained on long context data for 1500 steps using the YaRN extension method.
It is an extension of [Mistral-7B-v0.1](https://huggingface.co/mistralai/Mistral-7B-v0.1) and supports a 128k token context window.

To use, pass `trust_remote_code=True` when loading the model, for example

```python
model = AutoModelForCausalLM.from_pretrained("NousResearch/Yarn-Mistral-7b-128k",
  use_flash_attention_2=True,
  torch_dtype=torch.bfloat16,
  device_map="auto",
  trust_remote_code=True)
```

In addition you will need to use the latest version of `transformers` (until 4.35 comes out)
```sh
pip install git+https://github.com/huggingface/transformers
```

## Benchmarks

Long context benchmarks:
| Model | Context Window | 8k PPL | 16k PPL | 32k PPL | 64k PPL | 128k PPL |
|-------|---------------:|------:|----------:|-----:|-----:|------------:|
| [Mistral-7B-v0.1](https://huggingface.co/mistralai/Mistral-7B-v0.1) | 8k | 2.96 | - | - | - | - |
| [Yarn-Mistral-7b-64k](https://huggingface.co/NousResearch/Yarn-Mistral-7b-64k) | 64k | 3.04 | 2.65 | 2.44 | 2.20 | - |
| [Yarn-Mistral-7b-128k](https://huggingface.co/NousResearch/Yarn-Mistral-7b-128k) | 128k | 3.08 | 2.68 | 2.47 | 2.24 | 2.19 |

Short context benchmarks showing that quality degradation is minimal:
| Model | Context Window | ARC-c | Hellaswag | MMLU | Truthful QA |
|-------|---------------:|------:|----------:|-----:|------------:|
| [Mistral-7B-v0.1](https://huggingface.co/mistralai/Mistral-7B-v0.1) | 8k | 59.98 | 83.31 | 64.16 | 42.15 |
| [Yarn-Mistral-7b-64k](https://huggingface.co/NousResearch/Yarn-Mistral-7b-64k) | 64k | 59.38 | 81.21 | 61.32 | 42.50 |
| [Yarn-Mistral-7b-128k](https://huggingface.co/NousResearch/Yarn-Mistral-7b-128k) | 128k | 58.87 | 80.58 | 60.64 | 42.46 |

## Collaborators

 - [bloc97](https://github.com/bloc97): Methods, paper and evals
 - [@theemozilla](https://twitter.com/theemozilla): Methods, paper, model training, and evals
 - [@EnricoShippole](https://twitter.com/EnricoShippole): Model training
 - [honglu2875](https://github.com/honglu2875): Paper and evals

The authors would like to thank LAION AI for their support of compute for this model.
It was trained on the [JUWELS](https://www.fz-juelich.de/en/ias/jsc/systems/supercomputers/juwels) supercomputer.

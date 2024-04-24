# Phi 2 - GGUF
- Model creator: [Microsoft](https://huggingface.co/microsoft)
- Model card: [phi-2-GGUF](https://huggingface.co/TheBloke/phi-2-GGUF)
- Original model card: [Phi 2](https://huggingface.co/microsoft/phi-2)

## Description

This repo contains GGUF format model files for [Microsoft's Phi 2](https://huggingface.co/microsoft/phi-2).


## Prompt template: Phi

```
Instruct: {prompt}
Output:
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

# Original model card: Microsoft's Phi 2
## Model Summary

Phi-2 is a Transformer with **2.7 billion** parameters. It was trained using the same data sources as [Phi-1.5](https://huggingface.co/microsoft/phi-1.5), augmented with a new data source that consists of various NLP synthetic texts and filtered websites (for safety and educational value). When assessed against benchmarks testing common sense, language understanding, and logical reasoning, Phi-2 showcased a nearly state-of-the-art performance among models with less than 13 billion parameters.

Our model hasn't been fine-tuned through reinforcement learning from human feedback. The intention behind crafting this open-source model is to provide the research community with a non-restricted small model to explore vital safety challenges, such as reducing toxicity, understanding societal biases, enhancing controllability, and more.

## Intended Uses

Phi-2 is intended for research purposes only. Given the nature of the training data, the Phi-2 model is best suited for prompts using the QA format, the chat format, and the code format.

### QA Format:

You can provide the prompt as a standalone question as follows:

```markdown
Write a detailed analogy between mathematics and a lighthouse.
```
where the model generates the text after "." .
To encourage the model to write more concise answers, you can also try the following QA format using "Instruct: \<prompt\>\nOutput:"
```markdown
Instruct: Write a detailed analogy between mathematics and a lighthouse.
Output: Mathematics is like a lighthouse. Just as a lighthouse guides ships safely to shore, mathematics provides a guiding light in the world of numbers and logic. It helps us navigate through complex problems and find solutions. Just as a lighthouse emits a steady beam of light, mathematics provides a consistent framework for reasoning and problem-solving. It illuminates the path to understanding and helps us make sense of the world around us.
```
where the model generates the text after "Output:".

### Chat Format:

```markdown
Alice: I don't know why, I'm struggling to maintain focus while studying. Any suggestions?
Bob: Well, have you tried creating a study schedule and sticking to it?
Alice: Yes, I have, but it doesn't seem to help much.
Bob: Hmm, maybe you should try studying in a quiet environment, like the library.
Alice: ...
```

where the model generates the text after the first "Bob:".

### Code Format:

```python
def print_prime(n):
   """
   Print all primes between 1 and n
   """
   primes = []
   for num in range(2, n+1):
       is_prime = True
       for i in range(2, int(math.sqrt(num))+1):
           if num % i == 0:
               is_prime = False
               break
       if is_prime:
           primes.append(num)
   print(primes)
```
where the model generates the text after the comments.

**Notes:**
* Phi-2 is intended for research purposes. The model-generated text/code should be treated as a starting point rather than a definitive solution for potential use cases. Users should be cautious when employing these models in their applications.
* Direct adoption for production tasks is out of the scope of this research project. As a result, the Phi-2 model has not been tested to ensure that it performs adequately for any production-level application. Please refer to the limitation sections of this document for more details.
* If you are using `transformers>=4.36.0`, always load the model with `trust_remote_code=True` to prevent side-effects.

## Limitations of Phi-2

* Generate Inaccurate Code and Facts: The model may produce incorrect code snippets and statements. Users should treat these outputs as suggestions or starting points, not as definitive or accurate solutions.

* Limited Scope for code: Majority of Phi-2 training data is based in Python and use common packages such as "typing, math, random, collections, datetime, itertools". If the model generates Python scripts that utilize other packages or scripts in other languages, we strongly recommend users manually verify all API uses.

* Unreliable Responses to Instruction: The model has not undergone instruction fine-tuning. As a result, it may struggle or fail to adhere to intricate or nuanced instructions provided by users.

* Language Limitations: The model is primarily designed to understand standard English. Informal English, slang, or any other languages might pose challenges to its comprehension, leading to potential misinterpretations or errors in response.

* Potential Societal Biases: Phi-2 is not entirely free from societal biases despite efforts in assuring trainig data safety. There's a possibility it may generate content that mirrors these societal biases, particularly if prompted or instructed to do so. We urge users to be aware of this and to exercise caution and critical thinking when interpreting model outputs.

* Toxicity: Despite being trained with carefully selected data, the model can still produce harmful content if explicitly prompted or instructed to do so. We chose to release the model for research purposes only -- We hope to help the open-source community develop the most effective ways to reduce the toxicity of a model directly after pretraining.

* Verbosity: Phi-2 being a base model often produces irrelevant or extra text and responses following its first answer to user prompts within a single turn. This is due to its training dataset being primarily textbooks, which results in textbook-like responses.

## Training

### Model

* Architecture: a Transformer-based model with next-word prediction objective

* Context length: 2048 tokens

* Dataset size: 250B tokens, combination of NLP synthetic data created by AOAI GPT-3.5 and filtered web data from Falcon RefinedWeb and SlimPajama, which was assessed by AOAI GPT-4.

* Training tokens: 1.4T tokens

* GPUs: 96xA100-80G

* Training time: 14 days

### Software

* [PyTorch](https://github.com/pytorch/pytorch)

* [DeepSpeed](https://github.com/microsoft/DeepSpeed)

* [Flash-Attention](https://github.com/HazyResearch/flash-attention)

### License

The model is licensed under the [microsoft-research-license](https://huggingface.co/microsoft/phi-2/resolve/main/LICENSE).

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft’s Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-party’s policies.

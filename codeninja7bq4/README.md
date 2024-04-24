# CodeNinja: Your Advanced Coding Assistant

## Overview

CodeNinja is an enhanced version of the renowned model [openchat/openchat-3.5-1210](https://huggingface.co/openchat/openchat-3.5-1210). It having been fine-tuned through Supervised Fine Tuning on two expansive datasets, encompassing over 400,000 coding instructions. Designed to be an indispensable tool for coders, CodeNinja aims to integrate seamlessly into your daily coding routine.


### Key Features

- **Expansive Training Database**: CodeNinja has been refined with datasets from [glaiveai/glaive-code-assistant-v2](https://huggingface.co/datasets/glaiveai/glaive-code-assistant-v2) and [TokenBender/code_instructions_122k_alpaca_style](https://huggingface.co/datasets/TokenBender/code_instructions_122k_alpaca_style), incorporating around 400,000 coding instructions across various languages including Python, C, C++, Rust, Java, JavaScript, and more.

- **Flexibility and Scalability**: Available in a 7B model size, CodeNinja is adaptable for local runtime environments.

- **Advanced Code Completion**: With a substantial context window size of 8192, it supports comprehensive project-level code completion.

## Prompt Format

CodeNinja maintains the same prompt structure as OpenChat 3.5. Effective utilization requires adherence to this format:

```
GPT4 Correct User: Hello<|end_of_turn|>GPT4 Correct Assistant: Hi<|end_of_turn|>GPT4 Correct User: How are you today?<|end_of_turn|>GPT4 Correct Assistant:
```

Important: Ensure the use of `<|end_of_turn|>` as the end-of-generation token.

**Adhering to this format is crucial for optimal results.**


## License
CodeNinja is licensed under the MIT License, with model usage subject to the Model License.

## Contact
For queries or support, please open an issue in the repository.
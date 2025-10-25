WBGen is a highly adaptable bot that automatically makes MediaWiki wiki articles based on structured data found in a Wikibase repository.

## Getting started
Edit sample_config.py according to your needs and rename it to config.py.

Then run:
```Bash
pip install -r requirements.txt
python wbgen.py --model=moonshotai/kimi-k2:free --temperature=0.7
```
if you have an OpenRouter API key (you do not need to set up billing to use this model), otherwise set the model argument to ``ds`` to use the latest DeepSeek model from the official DeepSeek API if you have an API key for that. Please note that Kimi-K2 is known to follow the prompt better when told to generate articles that do not have more information than provided in the data. Any other model available on OpenRouter will work as well. If you want, you can also use any other model from any inference provider that supports the OpenAI API format including the likes of Ollama and llama.cpp.

## Features
* Supports DeepSeek, OpenRouter, or any local model being served from an API following the OpenAI API format
* Automatically skips existing pages, logs progress, and handles errors gracefully
* Allows specifying how many articles should be made at a time and where they should be made
* Allows specifying the model temperature
* Allows specifying what, if anything, all articles should begin with
* Allows specifying which namespace the items are found in the repository
* Can be made to follow the wiki's editorial conventions thanks to custom prompts without source code changes

Run ``python wbgen.py --help`` to get a help message that explains how to use all the features.

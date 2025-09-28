WBGen is a bot that automatically makes wiki articles based on data found in a Wikibase repository.

## Getting started
Edit sample_config.py according to your needs and rename it to config.py.

Then run:
```Bash
pip install -r requirements.txt
python wbgen.py --model=moonshotai/kimi-k2:free --temperature=0.7
```
if you have an OpenRouter API key (you do not need to set up billing to use this model), otherwise set the model argument to ``ds`` to use the latest DeepSeek model from the official DeepSeek API if you have an API key for that. Please note that Kimi-K2 is known to follow the prompt better when told to generate articles that do not have more information than provided in the data. Any other model available on OpenRouter will work as well. If you want, you can also use any other model from any inference provider that supports the 
OpenAI API format including the likes of Ollama and llama.cpp.

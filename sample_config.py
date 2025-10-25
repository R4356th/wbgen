REPO_API_URL = "" # This is the API endpoint of the Wikibase repository.
WIKI_API_URL = "" # This is the API endpoint of the wiki where the articles are to be made.
USERAGENT = ""
USERNAME = ""
PASSWORD = ""
DEEPSEEK_API_KEY = ""
OPENROUTER_API_KEY = ""
CUSTOM_API_KEY = 'sk-local' # This is required by the openai library even if it is not actually required by the inference provider.
CUSTOM_API_URL = 'http://localhost:8080/v1' # This is for llama.cpp. The port can be changed.
DBName = "wiki" # This is the database name that would be found in the API response telling us whether a page is already linked to the wiki with this database name.
def custom_sys_prompt() -> str:
    return "Avoid using disambiguation-style links and external links. Remember that the wiki is about <topic> only."
def summary(item: str) -> str:
    return f"Bot: Making an article based on data from item {item}"
def user_prompt(label: str, description: str, claims: str) -> str:
    return "Write a wiki article with the given data. Subject: " + label + "Brief description of the subject: " + description + "Data about the subject: " + claims

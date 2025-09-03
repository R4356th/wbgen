
REPO_API_URL = ""
WIKI_API_URL = ""
USERAGENT = ""
USERNAME = ""
PASSWORD = ""
DEEPSEEK_API_KEY = ""
OPENROUTER_API_KEY = ""
DBName = "wiki"
def custom_sys_prompt() -> str:
    return "Avoid using disambiguation-style links and external links. Remember that the wiki is about <topic>."
def summary(item: str) -> str:
    return f"Bot: Making an article based on data from item {item}"
def user_prompt(label: str, description: str, claims: str) -> str:
    return "Write a wiki article with the given data. Subject: " + label + "Brief description of the subject: " + description + "Data about the subject: " + claims

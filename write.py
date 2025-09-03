#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from requests import get
from config import USERAGENT, WIKI_API_URL, REPO_API_URL, USERNAME, PASSWORD, DEEPSEEK_API_KEY, OPENROUTER_API_KEY, DBName, custom_sys_prompt, user_prompt, summary
from mw_api_client import Wiki, excs
from openai import OpenAI
from itertools import islice
from argparse import ArgumentParser
from sys import maxsize
# @TODO: Implement concurrency: from concurrent.futures import ThreadPoolExecutor, as_completed
repo = Wiki(REPO_API_URL, USERAGENT)
wiki = Wiki(WIKI_API_URL, USERAGENT)
wiki.login(USERNAME, PASSWORD)
headers = {
    "User-Agent": USERAGENT
}
common_params = {
    "redirects": "yes",
    "format": "json"
}

def messages(label, description, claims):
    return [
        {"role": "system", "content": "You are an expert wiki editor. You write encyclopedic articles in proper English based on "
        "given JSON data in Wikitext (NOT Markdown) without adding any information based on external knowledge or assumptions even "
        "if you know them from elsewhere. Do not include anything irrelevant such as comments about what you did or the process you "
        "followed, lack of data about the given topic or something related to it; you should only ever write the article itself. Refrain "
        "from using too many bullet points; instead, put what you would like to put in bullet points as complete sentences as is the "
        "convention on wikis. Do not include references or anything that seems irrelevant to the specified topic because what you write will"
        " be pasted verbatim to make a new article. " + "Do not try to use templates or categorise any page. " + custom_sys_prompt()},
        {"role": "user", "content": user_prompt(label, description, claims)}, # user_prompt() is the function that generates the user prompt
    ]

def get_data_for_item(item_id: str):
    """Fetch label and descripton for a Wikibase item"""
    params = {
        "action": "wbgetentities",
        "ids": item_id,
        "props": "labels|claims|descriptions" # We do not want aliases as they are usually less useful for the main wiki.
    }
    params.update(common_params)
    response = get(REPO_API_URL, params=params, headers=headers)
    data = response.json()
    if not has_sitelinks(item_id):
        item = data.get("entities").get(item_id)
        try:
            label = item.get("labels").get("en").get("value")
        except AttributeError:
            print(f"{item_id} has no label!")
        try:
            claims = item.get("claims")
        except AttributeError:
            return "Unsuitable" # If an item has no claim, we cannot write any meaningful or meaningfully contentful article with it.
        try:
            description = data.get("entities").get(item_id).get("descriptions").get("en").get("value")
        except AttributeError:
            print(f"{item_id} has no description!")
            description = ""
        return make_claims_readable(claims), label, description

def has_sitelinks(item_id: str) -> bool:
    """Check if the entity has sitelinks to the main wiki"""
    params = {
        "action": "wbgetentities",
        "ids": item_id,
        "props": "sitelinks"
    }
    params.update(common_params)
    response = get(REPO_API_URL, params=params, headers=headers)
    data = response.json()
    sitelinks = data.get("entities", {}).get(item_id, {}).get("sitelinks", {})
    return DBName in sitelinks
    
def get_labels(ids: list):
    """Fetch English labels for a list of item or property IDs."""
    if not ids:
        return {}
    joined_ids = "|".join(ids)
    params = {
        "action": "wbgetentities",
        "ids": joined_ids,
        "props": "labels",
        "languages": "en",
        "format": "json"
    }
    response = get(REPO_API_URL, params=params, headers=headers)
    labels = {}
    for eid, data in response.json().get("entities", {}).items():
        lbl = data.get("labels", {}).get("en", {}).get("value")
        labels[eid] = lbl if lbl else eid
    return labels

def make_claims_readable(claims_dict: dict) -> dict:
    """Replace property/item IDs inside the claims with English labels."""
    ids = set()
    # collect all P and Q referenced
    for prop, claim_list in claims_dict.items():
        ids.add(prop)
        for claim in claim_list:
            dv = claim.get("mainsnak", {}).get("datavalue", {})
            if dv.get("type") == "wikibase-entityid":
                num = dv["value"]["numeric-id"]
                ids.add("Q" + str(num))

    labels = get_labels(list(ids))
    readable = {}
    for prop, claim_list in claims_dict.items():
        readable_prop = labels.get(prop, prop)
        readable[readable_prop] = []
        for claim in claim_list:
            dv = claim.get("mainsnak", {}).get("datavalue", {})
            if dv.get("type") == "wikibase-entityid":
                qid = "Q" + str(dv["value"]["numeric-id"])
                val_label = labels.get(qid, qid)
            else:
                val_label = dv.get("value", "")
            readable[readable_prop].append(val_label)
    return readable
    
def generate(model: str, label, claims, description, temp: float) -> str:
    """Generate article content with an LLM from the official DeepSeek API or from OpenRouter"""
    if model == 'ds':
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        model="deepseek-chat" # This is the latest non-reasoning LLM from DeepSeek
        extra_headers = {}
    else:
        client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
        extra_headers = {
            'HTTP-Referer': 'https://github.com/R4356th/wbgen',
            'X-Title': 'WBGen'
        }
    response = client.chat.completions.create(
        model=model,
        messages=messages(label, description, claims),
        stream=False,
        temperature=temp,
        extra_headers=extra_headers
    )
    return response.choices[0].message.content

def main():
    parser = ArgumentParser(prog='wbgen', description='A bot that automatically makes new wiki articles based on structured data found in a Wikibase repository')
    parser.add_argument("--prefix", default="", help="Article title prefix")
    parser.add_argument("--temperature", type=float, default=0.5, help="Model temperature (default: 0.5)")
    parser.add_argument("--ns", type=int, default=0, help="ID of the namespace where the Wikibase items are stored (default: 0)")
    parser.add_argument("--model", default="ds", help="Model: 'ds' for DeepSeek's non-reasoning model, otherwise OpenRouter model ID")
    parser.add_argument("--begin", default="", help="Wikitext that should be added to the start of the page (default: nothing)")
    parser.add_argument("--count", type=int, default=maxsize, help="Number of pages to process (default: unlimited)")
    args = parser.parse_args()

    try:
        with open('cache/processed.txt', 'r', encoding='utf-8') as f:
            already_made = set(line.strip() for line in f)
    except FileNotFoundError: # This means there is no cache to fetch labels from at the moment.
        already_made = set()

    pages = repo.allpages('max', args.ns)
    if not args.count == maxsize:
        pages = islice(pages, args.count)

    with open('cache/processed.txt', 'a', encoding='utf-8') as processed:
        for page in repo.allpages():
            if not page.title.startswith("Q") and page.title not in already_made:
                continue
            item = page.title
            data = get_data_for_item(item)
            if data == "Unsuitable":
                print(f"Skipping {item} because it has no claim")
            elif data is not None:
                claims, label, description = data
                article = args.begin
                if args.model == 'ds':
                    article = article + generate(args.model, label, str(claims), description, args.temperature)
                else:
                    article = article + generate(args.model, label, str(claims), description, args.temperature)
                # @TODO: Strip the first section header if it is the same as the title of the article
                try:
                    wiki.page(args.prefix + label).edit(article, summary(item), createonly=True)
                except excs.articleexists:
                    print("Skipping" + label + "because it has been created in the meantime. Please check if it is yet to be connected to the Wikibase wiki." )
            processed.write(item + '\n') # Save the file on each iteration to allow abruptly exiting the process
            

if __name__ == "__main__":
    main()

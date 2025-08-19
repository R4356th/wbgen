#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
from config import USERAGENT, WIKI_API_URL, REPO_API_URL, USERNAME, PASSWORD, DEEPSEEK_API_KEY, DBName, user_prompt
from mw_api_client import Wiki
from openai import OpenAI
import sys

repo = Wiki(REPO_API_URL, USERAGENT)
wiki = Wiki(WIKI_API_URL, USERAGENT)
wiki.clientlogin(USERNAME, PASSWORD)
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
headers = {
    "User-Agent": USERAGENT
}
common_params = {
    "redirects": "yes",
    "format": "json"
}

def get_data_for_item(item_id: str):
    """Fetch label and descripton for a Wikibase item"""
    params = {
        "action": "wbgetentities",
        "ids": item_id,
        "props": "labels|claims|descriptions" # We do not want aliases as they are usually less useful for the main wiki.
    }
    params.update(common_params)
    response = requests.get(REPO_API_URL, params=params, headers=headers)
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
        "props": "labels|aliases|claims|descriptions"
    }
    params.update(common_params)
    response = requests.get(REPO_API_URL, params=params, headers=headers)
    data = response.json()
    try:
        data.get("entities").get(item_id).get("sitelinks").get(DBName)
        return True
    except AttributeError:
        return False
    
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
    response = requests.get(REPO_API_URL, params=params, headers=headers)
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

def deepseek_generate(label, claims, description):
    """Generate article content with DeepSeek-v3"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are an expert wiki editor. You write encyclopedic articles in proper English based on given JSON data without adding any information based on external knowledge or assumptions even if you know them from elsewhere."},
            {"role": "user", "content": user_prompt(label, description, claims)}, # user_prompt() is the function that generates the user prompt
        ],
        stream=False
    )
    return response.choices[0].message.content

def main():
    prefix = ""
    if sys.argv[1]:
        prefix = sys.argv[1]
    for page in repo.allpages():
        if not page.title.startswith("Q"):
            continue
        item = page.title
        data = get_data_for_item(item)
        if data == "Unsuitable":
            print(f"Skipping {item} because it has no claim")
        else:
            claims, label, description = data
            article = deepseek_generate(label, str(claims), description)
            wiki.page(prefix + label).edit(article, f'Bot: Making an article based on data from Snap! Data item {item}', createonly=True)

if __name__ == "__main__":
    main()

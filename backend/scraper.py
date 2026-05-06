# scraper.py
import requests
from bs4 import BeautifulSoup
import json
import re


def scrape_recipe(url: str) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
        "DNT": "1",
    }

    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch page: HTTP {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")

    recipe = _extract_from_jsonld(soup)
    if recipe:
        return normalize_recipe(recipe, url)

    recipe = _extract_from_html(soup, url)
    if recipe:
        return recipe

    raise Exception("No structured recipe data found on this page.")




def _extract_from_jsonld(soup: BeautifulSoup) -> dict | None:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        candidates = []
        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict):
    
            if data.get("@type") == "Recipe":
                return data
            candidates = data.get("@graph", [])

        for item in candidates:
            if isinstance(item, dict) and item.get("@type") == "Recipe":
                return item

    return None



def _extract_from_html(soup: BeautifulSoup, url: str) -> dict | None:

  
    title = None
    for sel in ["h1.article-heading", "h1", "h1.headline"]:
        tag = soup.select_one(sel)
        if tag:
            title = tag.get_text(strip=True)
            break

    if not title:
        return None  

   
    ingredients = []

    for li in soup.select(
        "li.mm-recipes-structured-ingredients__list-item, "
        "li[class*='ingredient']"
    ):
        qty  = li.select_one("[data-ingredient-quantity]")
        unit = li.select_one("[data-ingredient-unit]")
        name = li.select_one("[data-ingredient-name]")
        if name:
            ingredients.append({
                "quantity": qty.get_text(strip=True)  if qty  else "",
                "unit":     unit.get_text(strip=True) if unit else "",
                "item":     name.get_text(strip=True),
            })


    if not ingredients:
        section = soup.find(id=re.compile(r"recipe-ingredients|ingredients", re.I))
        if section:
            for li in section.find_all("li"):
                text = li.get_text(strip=True)
                if text:
                    ingredients.append({"quantity": "", "unit": "", "item": text})

    if not ingredients:
        for li in soup.find_all("li"):
            parent_classes = " ".join(
                li.parent.get("class", []) if li.parent else []
            )
            if "ingredient" in parent_classes.lower():
                text = li.get_text(strip=True)
                if text:
                    ingredients.append({"quantity": "", "unit": "", "item": text})

    
    steps = []

    for step in soup.select(
        "li.comp.mntl-sc-block-compoundlistitem, "
        "li[class*='instruction'], "
        "div[class*='instructions-section'] li"
    ):
        text = step.get_text(separator=" ", strip=True)
        if text:
            steps.append(text)


    if not steps:
        for section_id in ["recipe-directions", "recipe-steps", "directions"]:
            section = soup.find(id=re.compile(section_id, re.I))
            if section:
                for li in section.find_all("li"):
                    text = li.get_text(strip=True)
                    if text:
                        steps.append(text)
                break

    if not steps:
        for p in soup.select("div[class*='direction'] p, div[class*='step'] p"):
            text = p.get_text(strip=True)
            if text:
                steps.append(text)

    
    def _get_meta(label: str) -> str:
        tag = soup.find(string=re.compile(label, re.I))
        if tag and tag.parent:
            sibling = tag.parent.find_next_sibling()
            if sibling:
                return sibling.get_text(strip=True)
        return ""

    prep_time  = _get_meta("Prep Time")
    cook_time  = _get_meta("Cook Time")
    total_time = _get_meta("Total Time")
    servings   = _get_meta("Servings")
    nutrition = {}
    nutrition_section = soup.select_one(
        "div[class*='nutrition-facts'], "
        "section[class*='nutrition'], "
        "table[class*='nutrition']"
    )
    if nutrition_section:
        for row in nutrition_section.find_all(["tr", "li", "div"]):
            text = row.get_text(separator=" ", strip=True).lower()
            for key in ("calories", "fat", "carbs", "carbohydrate", "protein"):
                if key in text:
                    match = re.search(r"[\d.]+\s*g?", text)
                    if match:
                        canonical = "carbs" if key == "carbohydrate" else key
                        nutrition[canonical] = match.group().strip()
    return {
        "title":      title,
        "ingredients": ingredients,
        "steps":      steps,
        "prep_time":  prep_time,
        "cook_time":  cook_time,
        "total_time": total_time,
        "servings":   servings,
        "nutrition":  nutrition,
        "source_url": url,
    }


def normalize_recipe(data: dict, url: str) -> dict:

    raw_instructions = data.get("recipeInstructions", [])
    steps = []
    for step in raw_instructions:
        if isinstance(step, dict):
            # HowToSection contains itemListElement
            if step.get("@type") == "HowToSection":
                for sub in step.get("itemListElement", []):
                    t = sub.get("text", "") if isinstance(sub, dict) else str(sub)
                    if t:
                        steps.append(t)
            else:
                t = step.get("text", step.get("name", ""))
                if t:
                    steps.append(t)
        elif isinstance(step, str) and step.strip():
            steps.append(step.strip())

    # Ingredients – plain strings from JSON-LD; we keep them raw here
    # (the LLM will later parse quantity / unit / item)
    raw_ingredients = data.get("recipeIngredient", [])
    ingredients = [{"quantity": "", "unit": "", "item": ing} for ing in raw_ingredients]

    # Nutrition block from JSON-LD
    raw_nutrition = data.get("nutrition", {})
    nutrition = {
        "calories": raw_nutrition.get("calories", ""),
        "protein":  raw_nutrition.get("proteinContent", ""),
        "carbs":    raw_nutrition.get("carbohydrateContent", ""),
        "fat":      raw_nutrition.get("fatContent", ""),
    }

    return {
        "title":      data.get("name", ""),
        "cuisine":    _listify(data.get("recipeCuisine", "")),
        "category":   _listify(data.get("recipeCategory", "")),
        "prep_time":  _iso_to_human(data.get("prepTime", "")),
        "cook_time":  _iso_to_human(data.get("cookTime", "")),
        "total_time": _iso_to_human(data.get("totalTime", "")),
        "servings":   _listify(data.get("recipeYield", "")),
        "ingredients": ingredients,
        "steps":      steps,
        "nutrition":  nutrition,
        "source_url": url,
    }


# ── Tiny utilities ────────────────────────────────────────────────────────────

def _listify(value) -> str:
    """Flatten a value that may be a list or a string."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value) if value else ""


def _iso_to_human(iso: str) -> str:
    """
    Convert ISO 8601 duration (PT5M, PT1H30M) to a readable string.
    Falls back to returning the original string unchanged.
    """
    if not iso or not iso.startswith("P"):
        return iso
    match = re.match(
        r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso
    )
    if not match:
        return iso
    days, hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    parts = []
    if days:    parts.append(f"{days} day{'s' if days > 1 else ''}")
    if hours:   parts.append(f"{hours} hr{'s' if hours > 1 else ''}")
    if minutes: parts.append(f"{minutes} min{'s' if minutes > 1 else ''}")
    if seconds: parts.append(f"{seconds} sec{'s' if seconds > 1 else ''}")
    return " ".join(parts) or iso
import re
from typing import Dict


def clean_recipe_text(raw_text: str) -> Dict:
    """
    Parse raw scraped text and organize into recipe sections.
    Handles messy HTML text extraction by looking for patterns.
    """
    
    sections = {
        "title": "",
        "ingredients": [],
        "instructions": [],
        "nutrition": [],
    }
    
    text_lower = raw_text.lower()
    
    # ---------- TITLE ----------
    title_match = re.search(r"^(.*?)\s+Recipe", raw_text)
    if title_match:
        sections["title"] = title_match.group(1).strip()
    else:
        words = raw_text.split()
        if words:
            sections["title"] = " ".join(words[:5])

    # ---------- INGREDIENTS ----------
    ing_start = max(text_lower.find("ingredient"), 0)
    ing_end_candidates = [text_lower.find("direction", ing_start), text_lower.find("instruction", ing_start)]
    ing_end = min([x for x in ing_end_candidates if x != -1] or [len(raw_text)])
    if ing_end == float('inf'):
        ing_end = len(raw_text)
    
    ing_block = raw_text[ing_start:ing_end]
    
    ing_lines = ing_block.split("\n")
    for line in ing_lines:
        line = line.strip()
        
        if not line or line.lower().startswith("ingredient"):
            continue
        
        # Filter: look for measurement units or patterns that indicate ingredients
        measurement_units = ["cup", "tablespoon", "teaspoon", "ounce", "pound", "gram", "ml", "l", "mg", "g", "tsp", "tbsp", "oz"]
        fractions = ["¼", "½", "¾", "1/2", "1/3", "1/4", "3/4"]
        
        has_unit = any(unit in line.lower() for unit in measurement_units)
        has_fraction = any(frac in line for frac in fractions)
        starts_with_number = re.match(r"^\d", line)
        
        # Include line if it has measurements or starts with a number
        if has_unit or has_fraction or starts_with_number:
            line = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", line)
            line = re.sub(r"\s+", " ", line)
            
            if not any(x in line.lower() for x in ["oops", "error", "scroll", "ingredient"]):
                if line and line not in sections["ingredients"] and len(line) > 3:
                    sections["ingredients"].append(line)

    # ---------- INSTRUCTIONS ----------
    inst_start_candidates = [text_lower.find("direction"), text_lower.find("instruction")]
    inst_start = max([x for x in inst_start_candidates if x != -1] or [0])
    
    inst_end_keywords = ["nutrition", "did you make", "save rate print", "photos", "most-saved"]
    inst_end = len(raw_text)
    for keyword in inst_end_keywords:
        pos = text_lower.find(keyword, inst_start)
        if pos != -1:
            inst_end = min(inst_end, pos)
    
    inst_block = raw_text[inst_start:inst_end]
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', inst_block)
    for sentence in sentences:
        sentence = sentence.strip()
        
        # Keep substantial sentences with action words
        if len(sentence) > 15 and any(action in sentence.lower() for action in 
                                     ["heat", "cook", "add", "mix", "stir", "bake", "simmer", "reduce", "serve", "garnish", "cover"]):
            sentence = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", sentence)
            sentence = re.sub(r"\s+", " ", sentence)
            
            if not any(x in sentence.lower() for x in ["rating", "review", "recipe", "save", "print"]):
                if sentence and sentence not in sections["instructions"]:
                    if not sentence.endswith("."):
                        sentence += "."
                    sections["instructions"].append(sentence)

    # ---------- NUTRITION ----------
    nutr_start = text_lower.find("nutrition facts")
    if nutr_start == -1:
        nutr_start = text_lower.find("nutrition")
    
    if nutr_start != -1:
        nutr_end_keywords = ["photos", "most-saved", "you'll also love"]
        nutr_end = len(raw_text)
        for keyword in nutr_end_keywords:
            pos = text_lower.find(keyword, nutr_start)
            if pos != -1:
                nutr_end = min(nutr_end, pos)
        
        nutr_block = raw_text[nutr_start:nutr_end]
        nutr_lines = nutr_block.split()
        
        for i, word in enumerate(nutr_lines):
            if re.match(r"^\d+$", word) and i + 1 < len(nutr_lines):
                next_word = nutr_lines[i + 1]
                if any(x in next_word.lower() for x in ["calorie", "fat", "carb", "protein", "fiber", "sugar", "sodium", "g", "mg"]):
                    nutrition_item = f"{word} {next_word}"
                    if nutrition_item not in sections["nutrition"]:
                        sections["nutrition"].append(nutrition_item)
    
    return sections

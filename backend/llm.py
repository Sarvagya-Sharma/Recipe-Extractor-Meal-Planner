"""
llm_processor.py
────────────────
Takes raw scraped recipe data and sends it to Gemini (via LangChain)
to produce the fully structured API output:
  • cleaned / normalised recipe fields
  • difficulty level
  • nutritional estimate
  • 3 ingredient substitutions
  • categorised shopping list
  • 3 related recipe suggestions
"""

import json
import re
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv 


load_dotenv()


def _get_llm() -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GOOGLE_API_KEY is not set. "
            "Export it with:  export GOOGLE_API_KEY=your_key_here"
        )
    return ChatGoogleGenerativeAI(
        model="gemma-4-26b-a4b-it",   
        google_api_key=api_key,
        temperature=0.2,          
    )



RECIPE_PROMPT = PromptTemplate(
    input_variables=["raw_recipe"],
    template="""
You are a professional recipe analyst. You will receive raw scraped recipe data
and must return a single, valid JSON object — nothing else. No markdown, no
explanation, no code fences. Just the JSON object.

RAW RECIPE DATA:
{raw_recipe}

Produce a JSON object with EXACTLY these keys:

{{
  "title":       "<string>  – clean recipe title",
  "cuisine":     "<string>  – e.g. American, Italian, Indian",
  "prep_time":   "<string>  – e.g. '5 mins' (use data if available, else estimate)",
  "cook_time":   "<string>  – e.g. '10 mins'",
  "total_time":  "<string>  – e.g. '15 mins'",
  "servings":    <integer>  – number of servings,
  "difficulty":  "<easy|medium|hard>  – based on steps and technique",

  "ingredients": [
    {{"quantity": "<string>", "unit": "<string>", "item": "<string>"}},
    ...
  ],

  "instructions": [
    "<step 1>",
    "<step 2>",
    ...
  ],

  "nutrition_estimate": {{
    "calories": <integer per serving>,
    "protein":  "<string e.g. 12g>",
    "carbs":    "<string e.g. 30g>",
    "fat":      "<string e.g. 20g>"
  }},

  "substitutions": [
    "<substitution 1 with reason>",
    "<substitution 2 with reason>",
    "<substitution 3 with reason>"
  ],

  "shopping_list": {{
    "<category e.g. dairy>":   ["<item>", ...],
    "<category e.g. produce>": ["<item>", ...],
    "<category e.g. pantry>":  ["<item>", ...]
  }},

  "related_recipes": [
    "<recipe name 1>",
    "<recipe name 2>",
    "<recipe name 3>"
  ]
}}

Rules:
- Base ALL fields strictly on the raw data provided; do NOT invent ingredients
  or steps that are not present in the raw data.
- For nutrition_estimate, use general nutritional knowledge to make a reasonable
  estimate grounded in the actual ingredients.
- For substitutions, suggest practical, real-world swaps relevant to THIS recipe.
- For shopping_list, group every ingredient under one of: dairy, produce,
  meat, seafood, bakery, pantry, spices, frozen, beverages, or other.
- For related_recipes, suggest dishes that pair well or are similar in style.
- Return ONLY the JSON object. No preamble, no explanation, no markdown fences.
""",
)


def enrich_recipe(scraped_data: dict) -> dict:
    llm = _get_llm()
    raw_text = json.dumps(scraped_data, ensure_ascii=False, indent=2)
    prompt_text = RECIPE_PROMPT.format(raw_recipe=raw_text)
    response = llm.invoke([HumanMessage(content=prompt_text)])

    raw_output = ""
    if isinstance(response.content, list):

        for block in response.content:
            if isinstance(block, dict) and block.get("type") == "text":
                raw_output = block.get("text", "")
                break
    else:
        raw_output = response.content.strip()

    return _parse_llm_json(raw_output)



def _parse_llm_json(raw: str) -> dict:
    """
    Safely parse the LLM's response.
    Handles accidental markdown fences (```json … ```) that some models add.
    """
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned invalid JSON.\n"
            f"Parse error: {exc}\n"
            f"Raw output (first 500 chars):\n{raw[:500]}"
        ) from exc

    _validate_structure(data)
    return data


def _validate_structure(data: dict) -> None:
    required = {
        "title", "cuisine", "prep_time", "cook_time", "total_time",
        "servings", "difficulty", "ingredients", "instructions",
        "nutrition_estimate", "substitutions", "shopping_list", "related_recipes",
    }
    missing = required - set(data.keys())
    if missing:
        raise ValueError(
            f"LLM response is missing required keys: {sorted(missing)}"
        )
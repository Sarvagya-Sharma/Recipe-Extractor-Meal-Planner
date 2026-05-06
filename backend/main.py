
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, HttpUrl
import uvicorn
from scraper import scrape_recipe
from llm import enrich_recipe
from db import save_recipe, get_all_recipes, get_recipe_by_id, init_db
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Recipe Extractor & Meal Planner",
    description="Scrapes recipe URLs, enriches them with Gemini LLM, stores in PostgreSQL.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
 


@app.on_event("startup")
def on_startup():
    """Create DB tables if they don't exist yet."""
    init_db()



class URLRequest(BaseModel):
    url: str 


class RecipeResponse(BaseModel):
    id: int
    url: str
    title: str
    cuisine: str
    prep_time: str
    cook_time: str
    total_time: str
    servings: int
    difficulty: str
    ingredients: list
    instructions: list
    nutrition_estimate: dict
    substitutions: list
    shopping_list: dict
    related_recipes: list


@app.get("/", tags=["Health"])
def home():
    return {"message": "Recipe Extractor API is running.", "status": "ok"}


@app.post(
    "/recipe",
    response_model=RecipeResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Recipe"],
    summary="Extract, enrich, and store a recipe from a URL",
)
def extract_recipe(request: URLRequest):
    """
    Full pipeline:
      1. Scrape the recipe page (JSON-LD → HTML fallback)
      2. Send scraped data to Gemini LLM for enrichment
      3. Store result in PostgreSQL
      4. Return the enriched recipe JSON
    """
    url = request.url

    try:
        scraped = scrape_recipe(url)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Scraping failed: {exc}",
        )

 
    try:
        enriched = enrich_recipe(scraped)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM processing error: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM service unavailable: {exc}",
        )


    try:
        record_id = save_recipe(url=url, data=enriched)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {exc}",
        )

    
    return {
        "id": record_id,
        "url": url,
        **enriched,
    }


@app.get(
    "/recipes",
    tags=["History"],
    summary="List all previously processed recipes",
)
def list_recipes():

    try:
        recipes = get_all_recipes()
        return {"count": len(recipes), "recipes": recipes}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {exc}",
        )


@app.get(
    "/recipes/{recipe_id}",
    response_model=RecipeResponse,
    tags=["History"],
    summary="Get full detail for a stored recipe",
)
def get_recipe(recipe_id: int):
    try:
        recipe = get_recipe_by_id(recipe_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {exc}",
        )

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No recipe found with id={recipe_id}",
        )

    return recipe


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
#  Recipe Extractor & Meal Planner

A full-stack application that accepts a recipe blog URL, scrapes the page, and uses an LLM (Gemma via Google AI Studio) to extract structured recipe data, estimate nutrition, generate substitutions, and suggest related recipes. All data is stored in PostgreSQL and displayed in a clean two-tab frontend.


## Output

### Tab 1 — Extract Recipe
<img width="1919" height="913" alt="Screenshot 2026-05-06 055232" src="https://github.com/user-attachments/assets/5fe2ce23-1922-4968-9c49-f0ab4b66f5cd" />



### Tab 2 — History
<img width="1906" height="906" alt="Screenshot 2026-05-06 054858" src="https://github.com/user-attachments/assets/6fd8c10d-f12b-4ff5-a3fc-0fe23aef3d66" />



### Details Modal
<img width="1033" height="920" alt="Screenshot 2026-05-06 054910" src="https://github.com/user-attachments/assets/7d12b56b-2b5e-48e5-8ae1-3dc3156aa43a" />
<img width="1008" height="859" alt="Screenshot 2026-05-06 054923" src="https://github.com/user-attachments/assets/b4a02f97-8414-4d8d-a8f5-1cf3475805bc" />





## Features

- Accepts any recipe blog URL as input
- Scrapes page content using BeautifulSoup (JSON-LD + HTML fallback)
- Sends scraped data to Gemma LLM via LangChain for:
  - Structured recipe extraction (title, cuisine, times, servings, difficulty)
  - Ingredients list with quantity, unit, and item separated
  - Step-by-step instructions
  - Nutritional estimate per serving
  - 3 ingredient substitutions
  - Shopping list grouped by category
  - 3 related recipe suggestions
- Stores all data in PostgreSQL
- Clean two-tab HTML frontend

---

## Project Structure

```
Project2/
├── backend/
│   ├── main.py          # FastAPI app, API endpoints
│   ├── scraper.py       # BeautifulSoup scraper (JSON-LD + HTML fallback)
│   ├── llm.py           # LangChain + Gemma LLM enrichment
│   ├── database.py      # PostgreSQL connection and queries
│   ├── requirements.txt # Python dependencies
│   ├── .env.example     # Environment variable template
│   └── prompts/
│       └── recipe_extraction.txt  # LangChain prompt templates
└── frontend/
    └── index.html       # Two-tab frontend (vanilla HTML + React via CDN)
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Sarvagya-Sharma/Recipe-Extractor-Meal-Planner.git
cd Recipe-Extractor-Meal-Planner
```

### 2. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```
GOOGLE_API_KEY=your_google_aistudio_api_key
DB_HOST=localhost
DB_PORT=5432
DB_NAME=recipes_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password
```

Get a free API key at [aistudio.google.com](https://aistudio.google.com)

### 4. Set up PostgreSQL

Create the database in pgAdmin or terminal:

```sql
CREATE DATABASE recipes_db;
```

The table is created automatically when the server starts.

### 5. Run the backend

```bash
python main.py
```

API will be running at `http://127.0.0.1:8000`

### 6. Open the frontend

Double-click `frontend/index.html` in your file explorer — no extra server needed.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/recipe` | Extract, enrich, and store a recipe from a URL |
| GET | `/recipes` | List all previously processed recipes |
| GET | `/recipes/{id}` | Get full detail for a stored recipe |

### Example Request

```bash
curl -X POST http://127.0.0.1:8000/recipe \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.allrecipes.com/recipe/23891/grilled-cheese-sandwich/"}'
```

### Example Response

```json
{
  "id": 1,
  "url": "https://www.allrecipes.com/recipe/23891/grilled-cheese-sandwich/",
  "title": "Classic Grilled Cheese Sandwich",
  "cuisine": "American",
  "prep_time": "5 mins",
  "cook_time": "10 mins",
  "total_time": "15 mins",
  "servings": 2,
  "difficulty": "easy",
  "ingredients": [
    { "quantity": "4", "unit": "slices", "item": "white bread" },
    { "quantity": "2", "unit": "slices", "item": "cheddar cheese" },
    { "quantity": "3", "unit": "tbsp",   "item": "butter" }
  ],
  "instructions": ["Butter one side of each slice...", "..."],
  "nutrition_estimate": { "calories": 400, "protein": "11g", "carbs": "26g", "fat": "28g" },
  "substitutions": ["Replace butter with olive oil...", "..."],
  "shopping_list": { "dairy": ["cheddar cheese", "butter"], "bakery": ["white bread"] },
  "related_recipes": ["Tomato Soup", "French Onion Grilled Cheese", "Caprese Sandwich"]
}
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python |
| Scraping | BeautifulSoup4, Requests |
| LLM | Gemma (Google AI Studio) via LangChain |
| Database | PostgreSQL, psycopg2 |
| Frontend | HTML, CSS, React (CDN) |

---

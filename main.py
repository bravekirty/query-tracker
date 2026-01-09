from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
import json
import os
from typing import Dict, List, Any
from pydantic import BaseModel
import uuid

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

app = FastAPI(title="Query Tracker API")
templates = Jinja2Templates(directory="templates")

DATA_FILE = "data/queries.json"


class QueryData(BaseModel):
    query: str = ""
    timestamp: str
    headers: Dict[str, str]
    body: Dict[str, Any] = {}
    method: str
    path: str
    query_id: str


def load_queries() -> List[Dict[str, Any]]:
    """Load saved queries from JSON file"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    return []


def save_query(query_data: Dict[str, Any]) -> None:
    """Save a new query to the JSON file"""
    queries = load_queries()
    queries.append(query_data)

    # Keep only last 100 queries to prevent file from growing too large
    if len(queries) > 100:
        queries = queries[-100:]

    with open(DATA_FILE, "w") as f:
        json.dump(queries, f, indent=2, default=str)


@app.middleware("http")
async def log_queries(request: Request, call_next):
    """Middleware to log all GET requests to the first endpoint"""
    if request.url.path == "/track-query" and request.method == "GET":
        # Generate unique ID for this query
        query_id = str(uuid.uuid4())

        # Get request data
        timestamp = datetime.now().isoformat()

        # Parse query parameters
        query_params = dict(request.query_params)

        # Try to parse body if present (for other HTTP methods)
        body = {}
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
            except:
                try:
                    body = dict(await request.form())
                except:
                    body = {"raw_body": await request.body()}

        # Prepare query data
        query_data = {
            "query_id": query_id,
            "timestamp": timestamp,
            "method": request.method,
            "path": request.url.path,
            "headers": dict(request.headers),
            "query_params": query_params,
            "body": body,
            "client_ip": request.client.host if request.client else None,
            "url": str(request.url),
        }

        # Save the query
        save_query(query_data)

        # Return response
        return JSONResponse(
            {
                "message": "Query tracked successfully",
                "query_id": query_id,
                "timestamp": timestamp,
                "query_params": query_params,
            }
        )

    return await call_next(request)


@app.get("/track-query")
async def track_query_get(request: Request):
    """
    First endpoint - GET request to save query information.
    Query parameters will be automatically saved via middleware.
    """
    # This endpoint's logic is handled by the middleware
    pass


@app.post("/track-query")
async def track_query_post(request: Request):
    """Handle POST requests to track queries with body"""
    # Generate unique ID for this query
    query_id = str(uuid.uuid4())

    # Get request data
    timestamp = datetime.now().isoformat()

    # Parse query parameters
    query_params = dict(request.query_params)

    # Parse body
    body = {}
    try:
        body = await request.json()
    except:
        try:
            body = dict(await request.form())
        except:
            body = {"raw_body": (await request.body()).decode("utf-8", errors="ignore")}

    # Prepare query data
    query_data = {
        "query_id": query_id,
        "timestamp": timestamp,
        "method": request.method,
        "path": request.url.path,
        "headers": dict(request.headers),
        "query_params": query_params,
        "body": body,
        "client_ip": request.client.host if request.client else None,
        "url": str(request.url),
    }

    # Save the query
    save_query(query_data)

    return JSONResponse(
        {
            "message": "Query tracked successfully",
            "query_id": query_id,
            "timestamp": timestamp,
            "query_params": query_params,
            "body": body,
        }
    )


@app.put("/track-query")
async def track_query_put(request: Request):
    """Handle PUT requests to track queries with body"""
    return await track_query_post(request)


@app.patch("/track-query")
async def track_query_patch(request: Request):
    """Handle PATCH requests to track queries with body"""
    return await track_query_post(request)


@app.get("/queries", response_class=HTMLResponse)
async def get_queries_html(request: Request):
    """
    Second endpoint - HTML page to display all saved queries
    """
    queries = load_queries()
    return templates.TemplateResponse(
        "queries.html",
        {"request": request, "queries": queries, "queries_count": len(queries)},
    )


@app.get("/api/queries")
async def get_queries_api():
    """
    API endpoint to get all queries in JSON format
    """
    queries = load_queries()
    return {"queries": queries, "count": len(queries)}


@app.post("/clear-queries")
async def clear_queries():
    """Clear all saved queries"""
    with open(DATA_FILE, "w") as f:
        json.dump([], f)
    return {"message": "All queries cleared successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

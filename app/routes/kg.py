"""Knowledge graph routes."""
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from app.services.kg_service import kg_service

router = APIRouter(prefix="/api/kg", tags=["kg"])


@router.get("/visualize", response_class=HTMLResponse)
def visualize(keyword: str = None, limit: int = Query(100, le=500)):
    """Return interactive pyvis HTML."""
    return kg_service.generate_pyvis_html(keyword=keyword, limit=limit)


@router.get("/search")
def search_indicators(keyword: str = Query(...), limit: int = 50):
    return kg_service.search_indicators(keyword, limit)


@router.get("/pagerank")
def pagerank(limit: int = 20):
    return kg_service.get_pagerank(limit)


@router.get("/pearson")
def pearson(limit: int = 20):
    return kg_service.get_pearson_pairs(limit)

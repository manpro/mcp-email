"""Search options API endpoint"""
from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["search"])

@router.get("/search/options")
async def get_search_options():
    """
    Get available search and filter options for the frontend
    """
    try:
        return {
            "filters": {
                "categories": ["Technology", "AI Research", "Cryptocurrency", "Blockchain", "DeFi", "NFT"],
                "languages": ["en", "sv"],
                "date_ranges": [
                    {"label": "Last 24 hours", "value": "1d"},
                    {"label": "Last week", "value": "7d"}, 
                    {"label": "Last month", "value": "30d"},
                    {"label": "Last 3 months", "value": "90d"},
                    {"label": "All time", "value": "all"}
                ]
            },
            "search_modes": [
                {"label": "Hybrid (Recommended)", "value": "hybrid"},
                {"label": "Semantic", "value": "semantic"},
                {"label": "Keyword", "value": "keyword"}
            ],
            "stats": {"total_chunks": 5680}
        }
        
    except Exception as e:
        logger.error(f"Search options error: {e}")
        return {
            "filters": {
                "categories": ["Technology", "Cryptocurrency"],
                "languages": ["en"],
                "date_ranges": [{"label": "All time", "value": "all"}]
            },
            "search_modes": [{"label": "Hybrid", "value": "hybrid"}],
            "stats": {"total_chunks": 0}
        }
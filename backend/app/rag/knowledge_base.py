"""
Static-ish knowledge base of substitution rules and savings tips.
In production this would be scraped/curated from supermarket catalogues
and nutrition databases -- kept small and hardcoded here so the RAG
pipeline is demoable without external scraping dependencies.
"""

KNOWLEDGE_BASE = [
    {
        "id": "kb-1",
        "text": "Home-brand pasta, rice, and canned goods are typically 20-40% cheaper than "
        "name-brand equivalents with near-identical nutritional profiles.",
        "category": "substitution",
    },
    {
        "id": "kb-2",
        "text": "Frozen vegetables retain similar nutritional value to fresh and are often "
        "30-50% cheaper per kilogram, with a much longer shelf life reducing waste.",
        "category": "substitution",
    },
    {
        "id": "kb-3",
        "text": "Buying meat and bread in bulk and freezing portions reduces per-unit cost "
        "and food waste for single or small households.",
        "category": "savings",
    },
    {
        "id": "kb-4",
        "text": "Store-brand dairy (milk, cheese, yoghurt) is produced in the same "
        "facilities as many name brands in Australia and is a low-risk substitution.",
        "category": "substitution",
    },
    {
        "id": "kb-5",
        "text": "Prices for fresh produce fluctuate seasonally; buying in-season produce "
        "can cut costs by 15-25% versus out-of-season equivalents.",
        "category": "savings",
    },
    {
        "id": "kb-6",
        "text": "Canned or dried legumes are a cheaper protein source than red meat, "
        "with comparable protein content per dollar spent.",
        "category": "substitution",
    },
]

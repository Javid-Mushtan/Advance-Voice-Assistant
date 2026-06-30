import requests
from datetime import datetime
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from src.utils.config import OPENROUTER_API_KEY, TAVILY_API_KEY
from src.utils.logger import logger


@tool
def get_world_news() -> str:
    """
    Get today's top world news headlines.
    Use for: 'world news', 'what's happening today', 'today's news',
    'latest news', 'news around the world', 'current events'.
    """
    if not TAVILY_API_KEY:
        return "News search isn't configured (missing TAVILY_API_KEY in .env)."

    today = datetime.now().strftime("%B %d, %Y")

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": f"world news today {today}",
                "topic": "news",
                "max_results": 6,
                "search_depth": "basic",
                "days": 1,
            },
            timeout=12,
        )
        data = response.json()
        results = data.get("results", [])

        if not results:
            return "No news results found right now. Try again in a moment."

        lines = [f"🌍 Top world news for {today}:\n"]
        for i, r in enumerate(results[:6], 1):
            title = r.get("title", "Untitled")
            snippet = r.get("content", "")[:180].strip()
            lines.append(f"{i}. {title}\n   {snippet}...")

        return "\n\n".join(lines)

    except Exception as e:
        return f"News fetch error: {e}"


@tool
def get_news_by_topic(topic: str) -> str:
    """
    Get latest news on a specific topic or category.
    Use for: 'news about technology', 'sports news', 'news on Sri Lanka',
    'business news today'.
    Example topics: 'technology', 'sports', 'business', 'science', 'politics'
    """
    if not TAVILY_API_KEY:
        return "News search isn't configured (missing TAVILY_API_KEY in .env)."

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": f"{topic} news today",
                "topic": "news",
                "max_results": 5,
                "search_depth": "basic",
                "days": 2,
            },
            timeout=12,
        )
        data = response.json()
        results = data.get("results", [])

        if not results:
            return f"No recent news found about '{topic}'."

        lines = [f"📰 Latest {topic} news:\n"]
        for i, r in enumerate(results[:5], 1):
            title = r.get("title", "Untitled")
            snippet = r.get("content", "")[:180].strip()
            lines.append(f"{i}. {title}\n   {snippet}...")

        return "\n\n".join(lines)

    except Exception as e:
        return f"News fetch error: {e}"


def _scrape_url(url: str) -> str:
    """Fetch and extract readable text content from a URL."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (JARVIS-VoiceAgent/1.0)"}
        r = requests.get(url, headers=headers, timeout=8)
        r.raise_for_status()

        # Try trafilatura first (best text extraction)
        try:
            import trafilatura
            text = trafilatura.extract(r.text)
            if text:
                return text[:3000]
        except ImportError:
            pass

        # Fallback: BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = " ".join(soup.get_text(separator=" ").split())
            return text[:3000]
        except ImportError:
            return r.text[:2000]

    except Exception as e:
        logger.debug(f"Scrape failed for {url}: {e}")
        return ""


def _tavily_search(query: str, max_results: int = 6, depth: str = "advanced") -> list[dict]:
    """Run a Tavily search and return raw results."""
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": max_results,
                "search_depth": depth,
                "include_raw_content": False,
            },
            timeout=15,
        )
        return response.json().get("results", [])
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return []


@tool
def deep_search(query: str) -> str:
    """
    Perform an advanced, thorough web research on a topic or person.
    Use this when the user explicitly asks to 'search hard', 'do an advanced search',
    'dig deeper', 'research thoroughly', 'find detailed information', or when a
    normal web_search wouldn't give enough depth (e.g. biography questions like
    'who is Ronaldo', 'tell me everything about X', 'give me full details on Y').

    This tool:
    1. Runs a high-depth multi-source search
    2. Scrapes the full content of the top results (not just snippets)
    3. Synthesizes a comprehensive, well-organized answer using AI

    Takes longer than web_search but gives much more complete information.
    """
    if not TAVILY_API_KEY:
        return "Deep search isn't configured (missing TAVILY_API_KEY in .env)."

    logger.info(f"Deep search initiated: {query!r}")

    # Step 1: broad high-depth search
    results = _tavily_search(query, max_results=6, depth="advanced")

    if not results:
        return f"No results found for '{query}'. Try rephrasing your question."

    # Step 2: scrape full content from top 3-4 sources
    scraped_sources = []
    for r in results[:4]:
        url = r.get("url", "")
        title = r.get("title", "Untitled")
        snippet = r.get("content", "")

        full_text = _scrape_url(url) if url else ""
        content = full_text if len(full_text) > len(snippet) else snippet

        if content:
            scraped_sources.append({
                "title": title,
                "url": url,
                "content": content[:2500],
            })
        logger.info(f"Scraped: {title[:60]} ({len(content)} chars)")

    if not scraped_sources:
        # Fall back to snippets only
        lines = [f"🔍 Search results for '{query}' (snippets only):\n"]
        for i, r in enumerate(results[:5], 1):
            lines.append(f"{i}. {r.get('title', '')}: {r.get('content', '')[:200]}")
        return "\n\n".join(lines)

    # Step 3: synthesize with LLM
    sources_text = "\n\n---\n\n".join(
        f"SOURCE {i + 1}: {s['title']}\n{s['content']}"
        for i, s in enumerate(scraped_sources)
    )

    prompt = f"""You are a research assistant. Based on the following sources,
write a comprehensive, well-organized, factual answer to this question: "{query}"

Rules:
- Synthesize information from ALL sources, don't just summarize one
- Be specific: include names, dates, numbers, facts where available
- Organize into 2-4 short paragraphs
- Write in a natural spoken style since this will be read aloud
- Do not mention "according to source 1/2/3" — just present the facts naturally
- If sources disagree on something, mention that briefly
- Keep it informative but concise (150-250 words)

SOURCES:
{sources_text}
"""

    try:
        llm = ChatOpenAI(
            model="openai/gpt-oss-120b:free",
            temperature=0.3,
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            max_retries=3,
        )
        response = llm.invoke(prompt)
        answer = response.content.strip()

        # Append source list at the end
        source_list = "\n".join(f"  • {s['title']}" for s in scraped_sources)
        return f"{answer}\n\n📚 Sources:\n{source_list}"

    except Exception as e:
        logger.error(f"LLM synthesis failed: {e}")
        # Fallback: just concatenate snippets
        lines = [f"Research results for '{query}':\n"]
        for s in scraped_sources:
            lines.append(f"• {s['title']}: {s['content'][:200]}...")
        return "\n\n".join(lines)


@tool
def search_person(name: str) -> str:
    """
    Get detailed biographical information about a person using deep research.
    Use for: 'who is X', 'tell me about X', 'who is Ronaldo', 'search for X'.
    Automatically does advanced multi-source research and scraping for accuracy.
    """
    query = f"{name} biography who is profile career achievements"
    return deep_search.invoke({"query": query})
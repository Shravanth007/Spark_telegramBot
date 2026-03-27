import re
import requests


def web_search(query):
    if not query:
        return {"success": False, "error": "No search query provided."}

    try:
        r = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=10,
        )

        if not r.ok:
            return {"success": False, "error": f"Search failed: HTTP {r.status_code}"}

        html = r.text

        results = []
        titles = re.findall(
            r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        snippets = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )

        for i, (url, title) in enumerate(titles):
            clean_title = re.sub(r'<[^>]+>', '', title).strip()
            clean_snippet = ""
            if i < len(snippets):
                clean_snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()

            url = url.replace('&amp;', '&')

            if not url or 'duckduckgo.com' in url:
                continue

            results.append({
                "title": clean_title.replace('&amp;', '&'),
                "url": url,
                "snippet": clean_snippet.replace('&amp;', '&'),
            })

            if len(results) >= 5:
                break

        if not results:
            return {"success": True, "count": 0, "results": [], "note": "No results found."}

        return {"success": True, "count": len(results), "results": results}

    except Exception as e:
        return {"success": False, "error": f"Search error: {str(e)}"}


def fetch_url(url):
    
    if not url:
        return {"success": False, "error": "No URL provided."}

    try:
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=10,
        )

        if not r.ok:
            return {"success": False, "error": f"Failed to fetch URL: HTTP {r.status_code}"}

        html = r.text

        for tag in ['script', 'style', 'nav', 'header', 'footer', 'aside']:
            html = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.DOTALL | re.IGNORECASE)

        text = re.sub(r'<[^>]+>', ' ', html)

        text = re.sub(r'\s+', ' ', text).strip()

        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')

        if len(text) > 3000:
            text = text[:3000] + "... (truncated)"

        if not text:
            return {"success": False, "error": "Could not extract text from the page."}

        return {"success": True, "url": url, "text": text}

    except Exception as e:
        return {"success": False, "error": f"Fetch error: {str(e)}"}


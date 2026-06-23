import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36",
    "Content-Type": "application/json"
}

def extract_slug_from_url(url: str) -> str | None:
    """Extract question title slug from LeetCode URL."""
    url = url.strip()
    # Normalize URL (remove trailing slashes, query parameters, etc.)
    url = url.split("?")[0]
    match = re.search(r"leetcode\.com/problems/([^/]+)", url)
    if match:
        return match.group(1)
    return None

def fetch_problems_by_tag(tag_slug: str, difficulty: str, skip: int = 0, limit: int = 20) -> list[dict]:
    """
    Fetch questions by tag and difficulty from LeetCode public GraphQL endpoint.
    Difficulty should be 'Easy', 'Medium', or 'Hard'.
    Returns list of dicts: [{'title': str, 'leetcode_url': str, 'difficulty': str}]
    """
    graphql_url = "https://leetcode.com/graphql"
    diff_upper = difficulty.upper()
    
    query = """
    query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
      problemsetQuestionList(
        categorySlug: $categorySlug
        limit: $limit
        skip: $skip
        filters: $filters
      ) {
        questions: data {
          title
          titleSlug
          difficulty
        }
      }
    }
    """
    
    variables = {
        "categorySlug": "",
        "skip": skip,
        "limit": limit,
        "filters": {
            "tags": [tag_slug],
            "difficulty": diff_upper
        }
    }
    
    payload = {
        "query": query,
        "variables": variables
    }
    
    try:
        response = requests.post(graphql_url, json=payload, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check for errors in response
        if "errors" in data and data["errors"]:
            raise Exception(f"GraphQL Errors: {data['errors']}")
            
        questions = data.get("data", {}).get("problemsetQuestionList", {}).get("questions", [])
        
        result = []
        for q in questions:
            # Map difficulty back to capitalized format e.g. Easy, Medium, Hard
            q_diff = q["difficulty"].capitalize()
            # If LeetCode returns something else, fall back to what we passed
            if q_diff not in ["Easy", "Medium", "Hard"]:
                q_diff = difficulty
                
            result.append({
                "title": q["title"],
                "leetcode_url": f"https://leetcode.com/problems/{q['titleSlug']}/",
                "difficulty": q_diff
            })
        return result
        
    except Exception as e:
        raise RuntimeError(f"Failed to fetch problems from LeetCode GraphQL: {e}")

def scrape_leetcode_problem(url: str) -> tuple[str | None, str | None]:
    """
    Retrieve problem title and difficulty from URL using a hybrid approach:
    1. Parse slug and query LeetCode GraphQL.
    2. If GraphQL fails, perform requests + BeautifulSoup HTML scrapings.
    """
    slug = extract_slug_from_url(url)
    if not slug:
        return None, None
        
    # Attempt 1: GraphQL Query
    graphql_url = "https://leetcode.com/graphql"
    query = """
    query questionTitle($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        title
        difficulty
      }
    }
    """
    variables = {"titleSlug": slug}
    payload = {"query": query, "variables": variables}
    
    try:
        response = requests.post(graphql_url, json=payload, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            data = response.json()
            q = data.get("data", {}).get("question")
            if q and q.get("title") and q.get("difficulty"):
                return q["title"], q["difficulty"].capitalize()
    except Exception:
        pass  # Fall back to HTML scraping
        
    # Attempt 2: HTML Scraping
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            title = None
            
            # Find title from <title> tag
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.text.replace("- LeetCode", "").strip()
                
            # Attempt to find difficulty from page content or metadata
            # Often, SPA metadata is inside JSON tags or scripts
            difficulty = None
            
            # Look for common difficulty classes / strings in HTML
            html_text = response.text
            if "Easy" in html_text and "text-difficulty-easy" in html_text:
                difficulty = "Easy"
            elif "Medium" in html_text and "text-difficulty-medium" in html_text:
                difficulty = "Medium"
            elif "Hard" in html_text and "text-difficulty-hard" in html_text:
                difficulty = "Hard"
            else:
                # Try to search with regex
                for d in ["Easy", "Medium", "Hard"]:
                    if re.search(r'\b' + d + r'\b', html_text):
                        difficulty = d
                        break
                        
            return title, difficulty
    except Exception:
        pass
        
    return None, None

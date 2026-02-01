# Provider Implementation Reference (OpenCode)

## 1. Reddit Scraper (PRAW)
- **Endpoint:** `subreddit.stream.submissions()` for real-time or `subreddit.new()` for batch.
- **Filtering:** Filter out `[removed]` or `[deleted]` content immediately.
- **Rate Limiting:** Respect the 60 requests per minute limit.
- **Extraction:** Target `title`, `selftext`, `score`, and `num_comments`.

## 2. LLM Providers (Decoupled)
- **Base Interface:**
  ```python
  class LLMProvider(ABC):
      def classify_pain(self, text: str) -> PainScore: ...
      def generate_report(self, data: List[dict]) -> str: ...
  ```
- **Groq:** Use for ultra-fast, high-volume filtering (Reflex layer).
- **GLM-4.7:** Use for deep synthesis and complex validation (Analysis layer).
- **Ollama:** Local fallback for zero-cost execution.

## 3. Storage Layer (SQLAlchemy)
- Use a `SessionManager` to handle local SQLite (`founder.db`).
- Schema must support:
    - `RawPosts`: Raw data from scrapers.
    - `Signals`: AI-filtered pain points with intensity scores.
    - `Leads`: Qualified prospects for outreach.

## 4. CLI Framework (Typer)
- Command groups for clean organization.
- Use `Rich` for progress bars during long-running scrapes.
- JSON output support for every command (for Skill interoperability).

## 5. Circuit Breaker Logic
- Wrap every external API call:
  ```python
  @circuit_breaker(threshold=5, timeout=60)
  def fetch_data(): ...
  ```

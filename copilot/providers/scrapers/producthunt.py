import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set
from ..base import ScraperProvider, ScraperCapability
from ...models.schemas import ScrapedPost


class ProductHuntScraper(ScraperProvider):
    """Product Hunt scraper using GraphQL API."""

    def __init__(self):
        self._api_token: Optional[str] = None
        self._api_url = "https://api.producthunt.com/v2/api/graphql"

    @property
    def name(self) -> str:
        return "producthunt"

    @property
    def platform(self) -> str:
        return "Product Hunt"

    @property
    def capabilities(self) -> Set[ScraperCapability]:
        return {
            ScraperCapability.REALTIME,
            ScraperCapability.COMMENTS,
            ScraperCapability.SORT_NEW,
            ScraperCapability.SORT_TOP,
        }

    def configure(self, config: Dict[str, Any]) -> None:
        self._api_token = config.get("api_token") or config.get("producthunt_api_token")

    def _make_graphql_request(
        self, query: str, variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make a GraphQL request to Product Hunt API."""
        if not self._api_token:
            raise RuntimeError("Product Hunt API token not configured")

        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            self._api_url,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Product Hunt API error: {response.status_code} - {response.text}"
            )

        data = response.json()
        if "errors" in data:
            raise RuntimeError(f"Product Hunt GraphQL error: {data['errors']}")

        return data.get("data", {})

    def scrape(self, target: str, limit: int = 100, **kwargs) -> List[ScrapedPost]:
        """
        Scrape Product Hunt posts.

        Args:
            target: Can be 'latest' for today's posts, 'top' for top posts, or a specific date (YYYY-MM-DD)
            limit: Maximum items to return
            **kwargs: Additional options like 'days_ago' (for relative date)
        """
        if not self._api_token:
            raise RuntimeError("ProductHuntScraper not configured")

        posts = []

        if target == "latest":
            posts = self._fetch_today_posts(limit)
        elif target == "top":
            posts = self._fetch_top_posts(limit)
        elif target.startswith("days_ago:"):
            days = int(target.split(":")[1])
            posts = self._fetch_posts_by_days_ago(days, limit)
        else:
            posts = self._fetch_posts_by_date(target, limit)

        if kwargs.get("fetch_comments", False):
            posts = self._enrich_with_comments(
                posts, comments_limit=kwargs.get("comments_limit", 10)
            )

        return posts

    def _fetch_today_posts(self, limit: int = 100) -> List[ScrapedPost]:
        """Fetch today's posts from Product Hunt."""
        query = """
        query getPosts($after: String) {
            posts(first: %d, after: $after, order: RANKING) {
                nodes {
                    id
                    name
                    tagline
                    description
                    url
                    website
                    votesCount
                    commentsCount
                    featuredAt
                    createdAt
                    productState
                    makers {
                        nodes {
                            name
                            username
                            url
                        }
                    }
                    topics {
                        nodes {
                            name
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """ % (min(limit, 50))

        posts = []
        has_next_page = True
        cursor = None

        while has_next_page and len(posts) < limit:
            variables = {"after": cursor} if cursor else {}
            data = self._make_graphql_request(query, variables)

            posts_data = data.get("posts", {})
            nodes = posts_data.get("nodes", [])

            for node in nodes:
                post = self._parse_product_node(node)
                if post:
                    posts.append(post)
                    if len(posts) >= limit:
                        break

            page_info = posts_data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

        return posts

    def _fetch_top_posts(self, limit: int = 100) -> List[ScrapedPost]:
        """Fetch top posts from Product Hunt (sorted by votes)."""
        query = """
        query getPosts($after: String) {
            posts(first: %d, after: $after, order: VOTES) {
                nodes {
                    id
                    name
                    tagline
                    description
                    url
                    website
                    votesCount
                    commentsCount
                    featuredAt
                    createdAt
                    productState
                    makers {
                        nodes {
                            name
                            username
                            url
                        }
                    }
                    topics {
                        nodes {
                            name
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """ % (min(limit, 50))

        posts = []
        has_next_page = True
        cursor = None

        while has_next_page and len(posts) < limit:
            variables = {"after": cursor} if cursor else {}
            data = self._make_graphql_request(query, variables)

            posts_data = data.get("posts", {})
            nodes = posts_data.get("nodes", [])

            for node in nodes:
                post = self._parse_product_node(node)
                if post:
                    posts.append(post)
                    if len(posts) >= limit:
                        break

            page_info = posts_data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

        return posts

    def _fetch_posts_by_days_ago(
        self, days_ago: int, limit: int = 100
    ) -> List[ScrapedPost]:
        """Fetch posts from N days ago."""
        target_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime(
            "%Y-%m-%d"
        )
        return self._fetch_posts_by_date(target_date, limit)

    def _fetch_posts_by_date(
        self, date_str: str, limit: int = 100
    ) -> List[ScrapedPost]:
        """Fetch posts from a specific date (YYYY-MM-DD format)."""
        query = """
        query getPosts($postedAfter: ISO8601DateTime!, $postedBefore: ISO8601DateTime!, $after: String) {
            posts(first: %d, after: $after, postedAfter: $postedAfter, postedBefore: $postedBefore) {
                nodes {
                    id
                    name
                    tagline
                    description
                    url
                    website
                    votesCount
                    commentsCount
                    featuredAt
                    createdAt
                    productState
                    makers {
                        nodes {
                            name
                            username
                            url
                        }
                    }
                    topics {
                        nodes {
                            name
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """ % (min(limit, 50))

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            posted_after = dt.replace(
                hour=0, minute=0, second=0, tzinfo=timezone.utc
            ).isoformat()
            posted_before = dt.replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            ).isoformat()
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD.")

        posts = []
        has_next_page = True
        cursor = None

        while has_next_page and len(posts) < limit:
            variables = {
                "postedAfter": posted_after,
                "postedBefore": posted_before,
                "after": cursor,
            }
            data = self._make_graphql_request(query, variables)

            posts_data = data.get("posts", {})
            nodes = posts_data.get("nodes", [])

            for node in nodes:
                post = self._parse_product_node(node)
                if post:
                    posts.append(post)
                    if len(posts) >= limit:
                        break

            page_info = posts_data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

        return posts

    def _parse_product_node(self, node: Dict[str, Any]) -> Optional[ScrapedPost]:
        """Parse a Product Hunt product node into a ScrapedPost."""
        try:
            makers = node.get("makers", {}).get("nodes", [])
            author = makers[0]["username"] if makers else "unknown"

            topics = node.get("topics", {}).get("nodes", [])
            topic_names = [t["name"] for t in topics]

            title = node.get("name", "")
            tagline = node.get("tagline", "")
            full_title = f"{title} - {tagline}" if tagline else title

            body = node.get("description", "")

            created_at_str = node.get("createdAt") or node.get("featuredAt")
            if created_at_str:
                created_at = datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00")
                )
            else:
                created_at = datetime.now(timezone.utc)

            return ScrapedPost(
                id=node["id"],
                source="producthunt",
                title=full_title,
                body=body,
                author=author,
                url=node.get("url", ""),
                upvotes=node.get("votesCount", 0),
                comments_count=node.get("commentsCount", 0),
                created_at=created_at,
                channel=f"topic:{','.join(topic_names[:3])}"
                if topic_names
                else "featured",
                metadata={
                    "website": node.get("website", ""),
                    "makers": [
                        {"name": m["name"], "username": m["username"]} for m in makers
                    ],
                    "topics": topic_names,
                    "product_state": node.get("productState"),
                    "tagline": tagline,
                },
            )
        except Exception:
            return None

    def _enrich_with_comments(
        self, posts: List[ScrapedPost], comments_limit: int = 10
    ) -> List[ScrapedPost]:
        """Enrich posts with top comments."""
        for post in posts:
            try:
                comments = self._fetch_comments_for_post(post.id, comments_limit)
                if comments:
                    post.metadata["top_comments"] = comments
            except Exception:
                pass

        return posts

    def _fetch_comments_for_post(
        self, post_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch comments for a specific post."""
        query = (
            """
        query getComments($postId: ID!) {
            post(id: $postId) {
                comments(first: %d, order: RANKING) {
                    nodes {
                        id
                        body
                        createdAt
                        votesCount
                        user {
                            name
                            username
                            url
                        }
                    }
                }
            }
        }
        """
            % limit
        )

        variables = {"postId": post_id}
        data = self._make_graphql_request(query, variables)

        post_data = data.get("post", {})
        comments_data = post_data.get("comments", {})
        nodes = comments_data.get("nodes", [])

        comments = []
        for node in nodes:
            user = node.get("user", {})
            comments.append(
                {
                    "id": node["id"],
                    "body": node.get("body", ""),
                    "created_at": node.get("createdAt"),
                    "votes_count": node.get("votesCount", 0),
                    "author": user.get("username", "unknown"),
                    "author_name": user.get("name", ""),
                }
            )

        return comments

    def health_check(self) -> bool:
        """Verify API connectivity."""
        if not self._api_token:
            return False

        try:
            query = """
            query healthCheck {
                posts(first: 1) {
                    nodes {
                        id
                    }
                }
            }
            """
            data = self._make_graphql_request(query, {})
            return "posts" in data
        except Exception:
            return False

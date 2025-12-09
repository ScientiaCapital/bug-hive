"""Example usage of the BugHive API.

This script demonstrates how to interact with the BugHive API
using the requests library.
"""

import asyncio
import time
from uuid import UUID

import httpx


class BugHiveClient:
    """Client for interacting with BugHive API."""

    def __init__(self, base_url: str, api_key: str):
        """
        Initialize BugHive client.

        Args:
            base_url: API base URL (e.g., http://localhost:8000)
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }

    async def health_check(self) -> dict:
        """Check API health."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def detailed_health(self) -> dict:
        """Get detailed health status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health/detailed")
            response.raise_for_status()
            return response.json()

    async def start_crawl(
        self,
        base_url: str,
        max_pages: int = 100,
        max_depth: int = 5,
        auth_method: str = "none",
        credentials: dict | None = None,
    ) -> dict:
        """
        Start a new crawl session.

        Args:
            base_url: URL to crawl
            max_pages: Maximum number of pages
            max_depth: Maximum crawl depth
            auth_method: Authentication method
            credentials: Authentication credentials

        Returns:
            Crawl session information
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/crawl/start",
                headers=self.headers,
                json={
                    "base_url": base_url,
                    "max_pages": max_pages,
                    "max_depth": max_depth,
                    "auth_method": auth_method,
                    "credentials": credentials,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_crawl_status(self, session_id: UUID | str) -> dict:
        """
        Get crawl session status.

        Args:
            session_id: Session ID

        Returns:
            Session status and progress
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/crawl/{session_id}/status",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_session_bugs(
        self,
        session_id: UUID | str,
        priority: str | None = None,
        category: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> dict:
        """
        Get bugs found in a session.

        Args:
            session_id: Session ID
            priority: Filter by priority
            category: Filter by category
            status: Filter by status
            skip: Number to skip
            limit: Maximum to return

        Returns:
            List of bugs with statistics
        """
        params = {"skip": skip, "limit": limit}
        if priority:
            params["priority"] = priority
        if category:
            params["category"] = category
        if status:
            params["status_filter"] = status

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/crawl/{session_id}/bugs",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def stop_crawl(self, session_id: UUID | str) -> dict:
        """
        Stop a running crawl session.

        Args:
            session_id: Session ID

        Returns:
            Stop confirmation
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/crawl/{session_id}/stop",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_bug(self, bug_id: UUID | str) -> dict:
        """
        Get bug details.

        Args:
            bug_id: Bug ID

        Returns:
            Bug details with evidence
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/bugs/{bug_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def validate_bug(
        self,
        bug_id: UUID | str,
        is_valid: bool,
        notes: str | None = None,
    ) -> dict:
        """
        Validate or dismiss a bug.

        Args:
            bug_id: Bug ID
            is_valid: Whether bug is valid
            notes: Optional notes

        Returns:
            Validation result
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/bugs/{bug_id}/validate",
                headers=self.headers,
                json={
                    "is_valid": is_valid,
                    "notes": notes,
                },
            )
            response.raise_for_status()
            return response.json()

    async def report_bug(self, bug_id: UUID | str) -> dict:
        """
        Report bug to Linear.

        Args:
            bug_id: Bug ID

        Returns:
            Linear issue information
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/bugs/{bug_id}/report",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def wait_for_crawl(
        self,
        session_id: UUID | str,
        poll_interval: int = 5,
        timeout: int = 3600,
    ) -> dict:
        """
        Wait for crawl to complete.

        Args:
            session_id: Session ID
            poll_interval: Seconds between polls
            timeout: Maximum seconds to wait

        Returns:
            Final session status

        Raises:
            TimeoutError: If crawl doesn't complete in time
        """
        start_time = time.time()

        while True:
            status = await self.get_crawl_status(session_id)

            if status["status"] in ["completed", "failed"]:
                return status

            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Crawl did not complete within {timeout} seconds"
                )

            print(
                f"Crawl in progress: {status['pages_crawled']}/{status['pages_discovered']} "
                f"pages, {status['bugs_found']} bugs found"
            )

            await asyncio.sleep(poll_interval)


async def main():
    """Example usage of BugHive client."""
    # Initialize client
    client = BugHiveClient(
        base_url="http://localhost:8000",
        api_key="your-api-key-here",
    )

    print("=== BugHive API Example Usage ===\n")

    # 1. Health check
    print("1. Checking API health...")
    health = await client.health_check()
    print(f"   Status: {health['status']}\n")

    # 2. Start crawl
    print("2. Starting crawl session...")
    crawl = await client.start_crawl(
        base_url="https://example.com",
        max_pages=50,
        max_depth=3,
    )
    session_id = crawl["session_id"]
    print(f"   Session ID: {session_id}")
    print(f"   Status: {crawl['status']}\n")

    # 3. Monitor crawl progress
    print("3. Monitoring crawl progress...")
    try:
        final_status = await client.wait_for_crawl(
            session_id,
            poll_interval=5,
            timeout=300,
        )
        print("   Crawl completed!")
        print(f"   Pages crawled: {final_status['pages_crawled']}")
        print(f"   Bugs found: {final_status['bugs_found']}")
        print(f"   Total cost: ${final_status['total_cost']:.2f}\n")

    except TimeoutError:
        print("   Crawl taking too long, stopping...\n")
        await client.stop_crawl(session_id)

    # 4. Get bugs
    print("4. Fetching bugs...")
    bugs_response = await client.get_session_bugs(
        session_id,
        priority="critical",  # Only critical bugs
    )
    print(f"   Total bugs: {bugs_response['total']}")
    print(f"   By priority: {bugs_response['by_priority']}")
    print(f"   By category: {bugs_response['by_category']}\n")

    # 5. Review first bug
    if bugs_response["bugs"]:
        bug = bugs_response["bugs"][0]
        bug_id = bug["id"]

        print(f"5. Reviewing bug: {bug['title']}")
        print(f"   Priority: {bug['priority']}")
        print(f"   Confidence: {bug['confidence']:.2%}")
        print(f"   Category: {bug['category']}\n")

        # 6. Validate bug
        print("6. Validating bug...")
        validation = await client.validate_bug(
            bug_id,
            is_valid=True,
            notes="Confirmed as real issue",
        )
        print(f"   Status: {validation['new_status']}\n")

        # 7. Report to Linear
        print("7. Reporting to Linear...")
        report = await client.report_bug(bug_id)
        print(f"   Linear issue: {report['linear_issue_url']}\n")

    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())

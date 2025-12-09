"""Quick test script to verify the FastAPI application works.

Run this after starting the server with:
    uvicorn src.api.main:app --reload
"""

import asyncio

import httpx


async def test_api():
    """Test basic API functionality."""
    base_url = "http://localhost:8000"

    print("Testing BugHive API...")
    print("-" * 50)

    async with httpx.AsyncClient() as client:
        # 1. Test root endpoint
        print("\n1. Testing root endpoint...")
        try:
            response = await client.get(f"{base_url}/")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")

        # 2. Test health check
        print("\n2. Testing health check...")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")

        # 3. Test detailed health
        print("\n3. Testing detailed health...")
        try:
            response = await client.get(f"{base_url}/health/detailed")
            print(f"   Status: {response.status_code}")
            data = response.json()
            print(f"   Overall Status: {data['status']}")
            print(f"   Services:")
            for service in data.get('services', []):
                print(f"     - {service['service']}: {service['status']} "
                      f"({service.get('latency_ms', 0):.2f}ms)")
        except Exception as e:
            print(f"   Error: {e}")

        # 4. Test API without auth (should fail)
        print("\n4. Testing API without authentication...")
        try:
            response = await client.post(
                f"{base_url}/api/v1/crawl/start",
                json={"base_url": "https://example.com"},
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")

        # 5. Test OpenAPI docs
        print("\n5. Testing OpenAPI docs...")
        try:
            response = await client.get(f"{base_url}/docs")
            print(f"   Status: {response.status_code}")
            print(f"   Docs available: {response.status_code == 200}")
        except Exception as e:
            print(f"   Error: {e}")

    print("\n" + "-" * 50)
    print("Test complete!")


if __name__ == "__main__":
    asyncio.run(test_api())

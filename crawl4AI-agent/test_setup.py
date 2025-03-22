import os
import sys
import asyncio
from dotenv import load_dotenv
import httpx

async def test_setup():
    print("\n=== Testing Environment Setup ===\n")
    
    # 1. Test environment variables
    print("Testing environment variables...")
    load_dotenv()
    required_vars = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing environment variables:", missing_vars)
        return
    print("✅ Environment variables loaded successfully")

    # 2. Test Supabase connection
    print("\nTesting Supabase connection...")
    try:
        from supabase import create_client, Client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        print(f"Supabase URL: {supabase_url}")  # Let's see the full URL
        
        # Test basic HTTP connection to Supabase first
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{supabase_url}/rest/v1/site_pages?select=count", 
                                     headers={
                                         "apikey": supabase_key,
                                         "Authorization": f"Bearer {supabase_key}"
                                     })
            print(f"HTTP Status: {response.status_code}")
            print(f"Response: {response.text}")

        # Now try the Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        response = supabase.table("site_pages").select("count").execute()
        print("✅ Supabase connection and query successful")
        
    except httpx.RequestError as e:
        print(f"❌ HTTP Connection Error: {str(e)}")
        print("Please check if the Supabase URL is correct and accessible")
        return
    except Exception as e:
        print(f"❌ Supabase error: {str(e)}")
        print(f"Error type: {type(e)}")
        return

    # Rest of your test code...
    # 3. Test Crawl4AI setup
    print("\nTesting Crawl4AI setup...")
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )
        crawler = AsyncWebCrawler(config=browser_config)
        await crawler.start()
        print("✅ Crawl4AI initialization successful")
        await crawler.close()
    except ImportError as e:
        print(f"❌ Crawl4AI import failed: {str(e)}")
        return
    except Exception as e:
        print(f"❌ Crawl4AI initialization failed: {str(e)}")
        return

    # 4. Test OpenAI connection
    print("\nTesting OpenAI connection...")
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input="Test embedding"
        )
        print("✅ OpenAI connection successful")
    except Exception as e:
        print(f"❌ OpenAI connection failed: {str(e)}")
        return

    print("\n=== All tests completed successfully! ===")

if __name__ == "__main__":
    asyncio.run(test_setup())

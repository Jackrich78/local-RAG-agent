import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client
from openai import AsyncOpenAI
import urllib3
import json

urllib3.disable_warnings()
load_dotenv()

# Initialize clients
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

async def test_pydantic_specific_query():
    """Test retrieval with a Pydantic-specific question."""
    print("\n=== Testing Pydantic AI Documentation Retrieval ===\n")
    
    # First, get the correct source name
    sources_query = supabase.table("site_pages").select(
        "metadata"
    ).execute()
    
    sources = set()
    for row in sources_query.data:
        if 'source' in row['metadata']:
            sources.add(row['metadata']['source'])
    
    source = next((s for s in sources if 'pydantic' in s.lower()), None)
    if not source:
        print("No Pydantic-related source found in metadata")
        return
        
    print(f"Using source: {source}\n")
    
    # A very specific question about Pydantic AI
    query = """
    Show me how to implement a custom model using Pydantic AI's Model Context Protocol (MCP). 
    What are the required methods and attributes?
    """
    print(f"Query: {query}\n")
    
    # Get embedding for our search query
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    embedding_response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    query_embedding = embedding_response.data[0].embedding
    
    # Use the match_site_pages function with the correct source
    response = supabase.rpc(
        'match_site_pages',
        {
            'query_embedding': query_embedding,
            'match_count': 3,
            'filter': {'source': source}
        }
    ).execute()
    
    print("Top 3 most relevant chunks:")
    for i, row in enumerate(response.data, 1):
        print(f"\n{i}. Title: {row['title']}")
        print(f"URL: {row['url']}")
        print(f"Summary: {row['summary']}")
        
        # Clean and display content
        content = row['content']
        # Remove navigation elements and markdown links
        content = re.sub(r'\[ Skip to content \].*?\n', '', content)
        content = re.sub(r'\[ ![.*?\n', '', content)
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        
        print(f"Content Preview: {content[:500].strip()}...")
        print(f"Similarity Score: {row['similarity']:.3f}")



async def check_specific_pages():
    """Check if specific important pages are in the database."""
    print("\n=== Checking Key Documentation Pages ===\n")
    
    key_pages = [
        "https://ai.pydantic.dev/mcp/overview/",
        "https://ai.pydantic.dev/getting_started/",
        "https://ai.pydantic.dev/examples/weather/",
        "https://ai.pydantic.dev/mcp/",  # Main MCP page
        "https://ai.pydantic.dev/api/mcp/",  # API reference
        "https://ai.pydantic.dev/api/models/base/"  # Base model documentation
    ]
    
    for page in key_pages:
        response = supabase.table("site_pages").select(
            "url, title, chunk_number"
        ).eq("url", page).execute()
        
        if response.data:
            chunks = len(response.data)
            print(f"✅ Found: {page}")
            print(f"   Number of chunks: {chunks}")
            print(f"   First chunk title: {response.data[0]['title']}\n")
        else:
            print(f"❌ Missing: {page}\n")


# Update main to include this check
async def main():
    await test_pydantic_specific_query()
    await verify_coverage()
    await check_specific_pages()


async def verify_coverage():
    """Verify we have good coverage of the documentation."""
    print("\n=== Verifying Documentation Coverage ===\n")
    
    # First, let's see what sources we have
    print("Checking available sources in metadata:")
    sources_query = supabase.table("site_pages").select(
        "metadata"
    ).execute()
    
    sources = set()
    for row in sources_query.data:
        if 'source' in row['metadata']:
            sources.add(row['metadata']['source'])
    
    print(f"\nFound sources: {sources}\n")
    
    # Now get URLs for Pydantic docs (using the correct source name)
    if sources:
        source = next((s for s in sources if 'pydantic' in s.lower()), None)
        if source:
            response = supabase.table("site_pages").select(
                "url"
            ).eq(
                "metadata->>source", source  # Note the ->> operator for JSONB
            ).execute()
            
            urls = set(row['url'] for row in response.data)
            print(f"Total unique URLs crawled: {len(urls)}")
            print("\nSample of crawled URLs:")
            for url in list(urls)[:5]:
                print(f"- {url}")
        else:
            print("No Pydantic-related source found in metadata")


async def main():
    await test_pydantic_specific_query()
    await verify_coverage()

if __name__ == "__main__":
    asyncio.run(main())

import os
import asyncio
from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from supabase import create_client
from openai import AsyncOpenAI
from datetime import datetime, timezone
import urllib3

# Disable SSL warnings
urllib3.disable_warnings()

# Load environment variables
load_dotenv()

# Initialize clients
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

async def get_embedding(text: str) -> list[float]:
    """Generate embedding for text using OpenAI."""
    try:
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

async def get_title_and_summary(chunk: str) -> dict:
    """Generate title and summary for a chunk using OpenAI."""
    system_prompt = """You are an AI that extracts titles and summaries from document chunks.
    Return a JSON object with 'title' and 'summary' keys.
    For the title: Create a descriptive title that reflects the main topic of this chunk.
    For the summary: Create a concise summary (2-3 sentences) of the main points."""
    
    try:
        response = await openai_client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chunk}
            ],
            response_format={ "type": "json_object" }
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating title and summary: {e}")
        return {"title": "Error processing title", "summary": "Error processing summary"}

def chunk_text(text: str, chunk_size: int = 4000) -> list[str]:
    """Split text into chunks, respecting paragraph boundaries."""
    chunks = []
    current_chunk = []
    current_size = 0
    
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        paragraph_size = len(paragraph)
        
        if current_size + paragraph_size > chunk_size and current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = []
            current_size = 0
            
        current_chunk.append(paragraph)
        current_size += paragraph_size
    
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks

async def process_and_store_chunk(chunk: str, url: str, chunk_number: int):
    """Process a single chunk and store it in Supabase."""
    try:
        # Get title and summary
        metadata = await get_title_and_summary(chunk)
        metadata_dict = eval(metadata) if isinstance(metadata, str) else metadata
        
        # Get embedding
        embedding = await get_embedding(chunk)
        
        if not embedding:
            print(f"Skipping chunk {chunk_number} due to embedding error")
            return
        
        # Prepare data for storage
        data = {
            "url": url,
            "chunk_number": chunk_number,
            "title": metadata_dict["title"],
            "summary": metadata_dict["summary"],
            "content": chunk,
            "metadata": {
                "source": "anthropic_engineering_blog",
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "chunk_size": len(chunk)
            },
            "embedding": embedding
        }
        
        # Store in Supabase
        result = supabase.table("site_pages").insert(data).execute()
        print(f"✅ Stored chunk {chunk_number}: {metadata_dict['title']}")
        
    except Exception as e:
        print(f"❌ Error processing chunk {chunk_number}: {e}")

async def main():
    url = "https://www.anthropic.com/engineering/building-effective-agents"
    print(f"\nCrawling: {url}")
    
    # Initialize crawler
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    crawler = AsyncWebCrawler(config=browser_config)
    
    try:
        await crawler.start()
        
        # Crawl the page
        result = await crawler.arun(
            url=url,
            config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS),
            session_id="test_session"
        )
        
        if result.success:
            print("✅ Successfully crawled page")
            
            # Get the markdown content
            content = result.markdown_v2.raw_markdown
            
            # Split into chunks
            chunks = chunk_text(content)
            print(f"Split content into {len(chunks)} chunks")
            
            # Process and store each chunk
            tasks = [
                process_and_store_chunk(chunk, url, i) 
                for i, chunk in enumerate(chunks)
            ]
            await asyncio.gather(*tasks)
            
            print("\n✅ Completed processing all chunks")
            
        else:
            print(f"❌ Failed to crawl page: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await crawler.close()

if __name__ == "__main__":
    asyncio.run(main())

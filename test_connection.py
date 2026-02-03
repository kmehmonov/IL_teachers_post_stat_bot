import os
import asyncio
import httpx
from dotenv import load_dotenv

async def test_connection():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    proxy = os.getenv("PROXY_URL")
    
    print("=== Telegram Connection Test (using httpx) ===")
    print(f"Token: {token[:10]}...{token[-5:]}" if token else "Token: MISSING")
    print(f"Proxy: {proxy or 'NONE'}")
    print("-" * 30)
    
    url = f"https://api.telegram.org/bot{token}/getMe"
    
    # Configure client with proxy if provided
    client_kwargs = {"timeout": 10.0}
    if proxy:
        client_kwargs["proxy"] = proxy

    async with httpx.AsyncClient(**client_kwargs) as client:
        try:
            print("Connecting to Telegram...")
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    bot_info = data.get("result")
                    print("\n✅ SUCCESS!")
                    print(f"Bot Name: {bot_info.get('first_name')}")
                    print(f"Username: @{bot_info.get('username')}")
                else:
                    print(f"\n❌ API Error: {data.get('description')}")
            else:
                print(f"\n❌ HTTP Error {response.status_code}")
                print(response.text)
                
        except httpx.ProxyError:
            print("\n❌ PROXY ERROR: Could not connect to your proxy server.")
            print("1. Check if your proxy app (V2Ray/Clash/VPN) is running.")
            print("2. Verify the IP and PORT in .env are correct.")
        except httpx.ConnectTimeout:
            print("\n❌ TIMEOUT: Connection timed out.")
            print("Your network is blocking Telegram. You MUST use a proxy or VPN.")
        except Exception as e:
            print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
            if "socks" in str(e).lower():
                print("\n💡 TIP: Try running 'pip install \"httpx[socks]\"' to enable SOCKS support.")

if __name__ == "__main__":
    asyncio.run(test_connection())

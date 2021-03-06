from proxylib import *
from datetime import datetime
import  re

class DefaultChecker(ProxyChecker):

    default_url = "https://www.google.com/"
    default_pattern = "google"
    
    @classmethod  
    def description(cls) -> str:
        return "Default"
        
    @classmethod     
    async def check(
                    cls, 
                    session : aiohttp.ClientSession,  
                    proxy: Proxy,
                    min_speed_s: int = 15,
                    max_retries: int = 1,
                    url_override: str = "",
                    pattern_override: str = "",
                    ) -> None:
        url = url_override if len(url_override) > 3 else cls.default_url
        pattern = pattern_override if len(pattern_override) > 3 else cls.default_pattern    
        now = datetime.now()
        while max_retries:
            try:
                async with session.get(url, proxy=proxy.proxy_string.replace('https', 'http'),
                                       timeout=min_speed_s) as response:
                    text = await response.text()
                if re.search(pattern, text):
                    proxy.status = ProxyStatus.GOOD
                    proxy.runtime_data['check_elapsed'] = round((datetime.now() - now).total_seconds(), 2)
                else:
                    proxy.status = ProxyStatus.BAD
                return
            except Exception:
                proxy.status = ProxyStatus.ERROR
                max_retries -= 1




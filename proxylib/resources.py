import re
import aiohttp

from typing import List

from proxylib.types import ProxyType, AnonymityLevel, Proxy, ProxyResouse


class SpysMe(ProxyResouse):

    url = "http://spys.me/proxy.txt"
    proxy_pattern: re.Pattern = re.compile("(\d+.\d+.\d+.\d+):(\d+) (\w?\w?)-?(\w?)-?(\w?)")

    @classmethod
    def description(cls) -> str:
        return "spys.me"

    @classmethod
    async def parse(
            cls,
            session: aiohttp.ClientSession,
            max_count: int = 200,
            min_anonymity_level: AnonymityLevel = AnonymityLevel.NONE,
            types=[t for t in ProxyType],
            country: str = "",
            timeout_s: int = 10
    ) -> List[Proxy]:
        proxies = []
        async with session.get(cls.url, timeout=timeout_s) as response:
            text = await response.text()
        results = re.findall(cls.proxy_pattern, text)
        for result in results:
            type = ProxyType.HTTPS if result[4] == 'S' else ProxyType.HTTP
            level = AnonymityLevel.UNKNOWN
            if result[3] == 'H':
                level = AnonymityLevel.HIGH
            elif result[3] == 'A':
                level = AnonymityLevel.MEDIUM
            elif result[3] == 'N':
                level = AnonymityLevel.NONE
            if level.value < min_anonymity_level.value \
                    or country not in result[2] \
                    or type not in types \
                    or len(proxies) >= max_count:
                continue
            proxy = Proxy(
                result[0],
                int(result[1]),
                type,
                country=result[2],
                anonymity=level,
                source='spys.me'
            )
            proxies.append(proxy)
        return proxies

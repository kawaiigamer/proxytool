import json
import re
import math
import asyncio
import aiohttp

from threading import Thread
from typing import List, Set, Callable, Any, Union

from aiosocksy.connector import ProxyConnector, ProxyClientRequest

from proxylib.types import ProxyStatus, Proxy, ProxyType, AnonymityLevel


class ProxiesContainer:
    proxy_pattern: re.Pattern = re.compile("(\d+.\d+.\d+.\d+):(\d+).?(\w?\w?\w?\w?\w?\w?)")

    def __init__(self):
        self.proxy_list: Set[Proxy] = set()

    def get_status(self) -> str:
        statuses_list = self.get_count_all_by_status()
        return "All: {0}  Working: {1}({2}%)  Bad: {3}  Banned: {4}  Error: {5}  Unknown: {6}  Ready: 0".format(
            len(self.proxy_list),
            statuses_list[ProxyStatus.GOOD.value],
            math.floor(statuses_list[ProxyStatus.GOOD.value] / len(self.proxy_list) * 100) if self.proxy_list else 0,
            statuses_list[ProxyStatus.BAD.value],
            statuses_list[ProxyStatus.BANNED.value],
            statuses_list[ProxyStatus.ERROR.value],
            statuses_list[ProxyStatus.UNKNOWN.value])

    def get_count_all_by_status(self) -> List[int]:
        statuses_count = [0] * len(ProxyStatus)
        for proxy in self.proxy_list:
            statuses_count[proxy.status.value] += 1
        return statuses_count

    def get_all_with_status(self, status_list: List[int]) -> List[Proxy]:
        result_list = []
        for proxy in self.proxy_list:
            if proxy.status in status_list:
                result_list.append(proxy)
        return result_list

    def add_new_list(self, new_list: List[Proxy]) -> int:
        last_count = len(self.proxy_list)
        self.proxy_list.update(new_list)
        return len(self.proxy_list) - last_count

    def delete_all_with_status(self, status_list: List[int]) -> int:
        delete_list = self.get_all_with_status(status_list)
        for d in delete_list:  # all!!
            self.proxy_list.remove(d)
        return len(delete_list)

    def dump_all_with_status_json(self, status_list: List[int]) -> str:
        output_string = ""
        output_string += "["
        for proxy in self.get_all_with_status(status_list):
            raw_json = proxy.json()
            del raw_json['runtime_data']
            output_string += (json.dumps(raw_json))
            output_string += (",")
        output_string = output_string[:-1]
        output_string += "]"
        return output_string

    def dump_all_with_status_txt(self, status_list: List[int]) -> str:
        output_string = ""
        for proxy in self.get_all_with_status(status_list):
            output_string += proxy.host + ":" + str(proxy.port) + " " + proxy.proxy_type.name + "\n"
        return output_string

    def add_from_txt(self, raw: str, on_missing_type: Callable[[], ProxyType]) -> int:
        add_list = []
        default_type = None
        results = re.findall(self.proxy_pattern, raw)
        for result in results:
            try:
                this_type = ProxyType[result[2]]
            except KeyError:
                if default_type is None:
                    default_type = on_missing_type()
                this_type = default_type
            add_list.append(Proxy(result[0], int(result[1]), this_type))
        return self.add_new_list(add_list)

    def add_from_json(self, raw: str) -> int:
        add_list = []
        proxies = json.loads(raw)
        for proxy in proxies:
            add_list.append(Proxy(
                proxy['host'],
                int(proxy['port']),
                ProxyType[proxy['proxy_type']],
                AnonymityLevel[proxy['anonymity']],
                ProxyStatus[proxy['status']],
                proxy['country'],
                proxy['source'],
                proxy['login'],
                proxy['password']
            ))
        return self.add_new_list(add_list)


class EventLoopThread:

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.t = Thread(target=self.start_background_loop, args=(self.loop,), daemon=True)
        self.t.start()

    def start_background_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def multiple_http_works(self, on_start: Callable[[None], None], on_end: Callable[[List[Any]], None],
                            elements: List[Union[Proxy, Any]], max_concurrent_workers: int,
                            worker: Callable[[aiohttp.ClientSession, Union[Proxy, Any], ...], Any], *worker_args,
                            **worker_kwargs) -> None:
        async def __work():
            semaphore = asyncio.Semaphore(max_concurrent_workers)
            session = aiohttp.ClientSession(connector=ProxyConnector(), request_class=ProxyClientRequest)

            async def __task(element: Union[Proxy, Any]):
                async with semaphore:
                    return await worker(session, element, *worker_args, **worker_kwargs)

            on_start()
            tasks = [self.loop.create_task(__task(element)) for element in elements]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            await session.close()
            on_end(results)

        asyncio.run_coroutine_threadsafe(__work(), self.loop)

    def single_http_work(self, on_start: Callable[[None], None], on_end: Callable[[Any], None],
                         worker: Callable[[aiohttp.ClientSession, ...], Any], *worker_args, **worker_kwargs) -> None:
        async def __work():
            session = aiohttp.ClientSession(connector=ProxyConnector(), request_class=ProxyClientRequest)
            on_start()
            results = await asyncio.gather(self.loop.create_task(worker(session, *worker_args, **worker_kwargs)),
                                           return_exceptions=True)
            on_end(results[0])
            await session.close()

        asyncio.run_coroutine_threadsafe(__work(), self.loop)

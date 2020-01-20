import json, re, math, asyncio, aiohttp
from proxylib import *
from threading import Thread
from aiosocksy.connector import ProxyConnector, ProxyClientRequest

class UiData: 
    
    def __init__(self):
        self.proxy_list = set()
        
    def get_status(self):
        statuses_list = self.get_count_all_by_status()
        return "All: {0}  Working: {1}({2}%)  Bad: {3}  Banned: {4}  Error: {5}  Unknown: {6}  Ready: 0".format(
                   len(self.proxy_list), statuses_list[4],math.floor(statuses_list[4]/len(self.proxy_list)*100) if len(self.proxy_list) > 0 else 0 , statuses_list[2], statuses_list[3],statuses_list[1], statuses_list[0]  )
    
    def get_count_all_by_status(self) -> list:
        statuses_count = [0] * len(ProxyStatus)
        for proxy in self.proxy_list: statuses_count[proxy.status.value] += 1
        return statuses_count
        
    def get_all_with_status(self, status_list : list) -> list:
        result_list = []
        for proxy in self.proxy_list:
            if proxy.status in status_list:
                 result_list.append(proxy)
        return result_list
        
    def add_new_list(self, new_list : list) -> int:
        last_count =  len(self.proxy_list ) 
        self.proxy_list.update(new_list)
        return len(self.proxy_list ) - last_count   
        
    def delete_all_with_status(self, status_list : list) -> int:
        delete_list = self.get_all_with_status(status_list)    
        for d in delete_list:
            self.proxy_list.remove(d)
        return len(delete_list)
        
    def dump_all_with_status_json(self, status_list : list) -> int:
            output_string = ""
            output_string += "["
            for proxy in self.get_all_with_status(status_list):
                    raw_json = proxy.json()
                    del raw_json['runtime_data']
                    output_string +=(json.dumps(raw_json))
                    output_string +=(",")
            output_string = output_string[:-1]
            output_string += "]"
            return output_string
           
    def dump_all_with_status_txt(self, status_list : list) -> str:
            output_string = ""
            for proxy in self.get_all_with_status(status_list):
                   output_string += proxy.host + ":" + str(proxy.port) + " " + proxy.proxy_type.name + "\n"
            return output_string        
            
    def add_from_txt(self, raw : str, on_missing_type) -> int:
        add_list = []
        default_type = None
        results = re.findall(re.compile("(\d+.\d+.\d+.\d+):(\d+).?(\w?\w?\w?\w?\w?\w?)"), raw)
        for result in results:
            try:
                this_type = ProxyType[result[2]]
            except KeyError:
                if default_type is None:
                 default_type = on_missing_type()
                this_type = default_type
            add_list.append(Proxy(result[0], int(result[1]), this_type))
        return self.add_new_list(add_list)
        
    def add_from_json(self, raw : str) -> int:
        add_list = []
        proxies = json.loads(raw)
        for proxy in proxies:
            add_list.append(                Proxy(
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
                
        
class UiThreading: 
    
    def __init__(self):
     self.loop = asyncio.new_event_loop()
     self.t = Thread(target=self.start_background_loop, args=(self.loop,), daemon=True)
     self.t.start()
        
    def start_background_loop(self, loop: asyncio.AbstractEventLoop) -> None:
     asyncio.set_event_loop(loop)
     loop.run_forever()
     
    def async_http_works(self, on_start_callback, on_end_callback, elements : list, threads : int,  worker,  *worker_args, **worker_kwargs) -> None:
        async def __work():
         semaphore = asyncio.Semaphore(threads)
         session = aiohttp.ClientSession(connector=ProxyConnector(), request_class=ProxyClientRequest)
         async def __task(element):
              async with semaphore:
                  return await worker(session, element, *worker_args, **worker_kwargs)
         on_start_callback()
         tasks = [self.loop.create_task(__task(element)) for element in elements]
         results = await asyncio.gather(*tasks, return_exceptions=True)
         await session.close()
         on_end_callback(results)
        asyncio.run_coroutine_threadsafe(__work(), self.loop)

    def async_http_work(self, on_start_callback, on_end_callback, worker, *worker_args,**worker_kwargs) -> None:
        async def __work():
            session = aiohttp.ClientSession(connector=ProxyConnector(), request_class=ProxyClientRequest)
            on_start_callback()
            results = await asyncio.gather(self.loop.create_task(worker(session, *worker_args,**worker_kwargs)), return_exceptions=True)
            on_end_callback(results[0])
            await session.close()
        asyncio.run_coroutine_threadsafe(__work(), self.loop)
import aiohttp

from abc import ABC, abstractmethod
from typing import List, Dict
from enum import Enum


class ProxyStatus(Enum):
    UNKNOWN = 0
    ERROR = 1
    BAD = 2
    BANNED = 3
    GOOD = 4


class AnonymityLevel(Enum):
    UNKNOWN = 0
    NONE = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4


class ProxyType(Enum):
    HTTP = 0
    HTTPS = 1
    SOCKS4 = 2
    SOCKS5 = 3


class Proxy:
    __slots__ = (
        'host',
        'port',
        'proxy_type',
        'anonymity',
        'status',
        'country',
        'source',
        'login',
        'password',
        'proxy_string',
        'runtime_data',
    )

    def __init__(self,
                 host: str,
                 port: int,
                 proxy_type: ProxyType,
                 anonymity: AnonymityLevel = AnonymityLevel.UNKNOWN,
                 status: ProxyStatus = ProxyStatus.UNKNOWN,
                 country: str = "",
                 source: str = "",
                 user: str = "",
                 password: str = "",
                 runtime_data: Dict = None
                 ):
        self.host = host
        self.port = port
        self.login = user
        self.password = password
        self.anonymity = anonymity
        self.proxy_type = proxy_type
        self.country = country
        self.source = source
        self.status = status
        self.runtime_data = runtime_data or dict()
        self.proxy_string = "{0}://{1}:{2}@{3}:{4}".format(
            proxy_type.name.lower(), user, password, host, port
        )

    def __eq__(self, other):
        return self.proxy_string == other.proxy_string

    def __hash__(self):
        return hash(self.proxy_string)

    def to_dict(self) -> Dict[str, str]:
        dict_ = {}
        for key in self.__slots__:
            this = getattr(self, key, None)
            if isinstance(this, Enum):
                dict_[key] = this.name
            else:
                dict_[key] = str(this)
        return dict_


class ProxyResouse(ABC):
    @classmethod
    @abstractmethod
    def description(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    async def parse(
            cls,
            session: aiohttp.ClientSession,
            max_count: int = 200,
            min_anonymity_level: AnonymityLevel = AnonymityLevel.NONE,
            types=[t for t in ProxyType],
            country: str = '',
            timeout_s: int = 10
    ) -> List[Proxy]:
        pass


class ProxyChecker(ABC):
    @classmethod
    @abstractmethod
    def description(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    async def check(
            cls,
            session: aiohttp.ClientSession,
            proxy: Proxy,
            min_speed_s: int = 15,
            max_retries: int = 1,
            url_override: str = "",
            pattern_override: str = "",
    ) -> None:
        pass

import os
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()
bearer_token = os.getenv('BEARER_TOKEN')


def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """

    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2LikedTweetsPython"
    return r


class Bridge:
    def __init__(
        self,
        retries=3,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504),
    ):
        self.session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('https://', adapter)

    def request(self, url, params={}, timeout=15):
        try:
            return self.session.get(url,
                                    params=params,
                                    auth=bearer_oauth,
                                    timeout=timeout)
        except Exception as e:
            raise e

    def close(self):
        self.session.close()

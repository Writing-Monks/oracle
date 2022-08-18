from pdb import set_trace as pdb
import os
from datetime import datetime

import requests
from requests_oauthlib import OAuth1
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

MEDIA_ENDPOINT_URL = 'https://upload.twitter.com/1.1/media/upload.json'
POST_TWEET_URL = 'https://api.twitter.com/1.1/statuses/update.json'


class TweetPoster:
    def __init__(self, content: str, media_url: str, total_bytes: int, media_type: str,
                 in_reply_to_status_id: int, oauth: OAuth1):
        """
        Defines video tweet properties
        """
        self.content = content
        self.media_url = media_url
        self.total_bytes = total_bytes
        self.media_type = media_type
        self.in_reply_to_status_id = in_reply_to_status_id
        self.oauth = oauth
        self.media_id = None
        self.processing_info = None

        self.session = requests.Session()
        retry = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=(500, 502, 504, 506, 508),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('https://', adapter)

    def post(self) -> dict:
        if self.media_url is not None:
            self.upload_init()
            self.upload_append()
            self.upload_finalize()
        data = self.tweet()
        self.session.close()
        return data

    def upload_init(self):
        """
        Initializes Upload
        """
        print('INIT')

        request_data = {
            'command': 'INIT',
            'media_type': self.media_type,
            'total_bytes': self.total_bytes,
            'media_category': _get_media_category(self.media_type)
        }

        req = self.session.post(url=MEDIA_ENDPOINT_URL, data=request_data, auth=self.oauth)
        media_id = req.json()['media_id']

        self.media_id = media_id

        print('Media ID: %s' % str(media_id))

    def upload_append(self):
        """
        Uploads media in chunks and appends to chunks uploaded
        """
        segment_id = 0

        with requests.get(self.media_url, stream=True) as stream:
            stream.raise_for_status()
            for chunk in stream.iter_content(chunk_size=131072):
                print('APPEND')

                request_data = {
                    'command': 'APPEND',
                    'media_id': self.media_id,
                    'segment_index': segment_id
                }

                files = {
                    'media': chunk
                }

                req = self.session.post(url=MEDIA_ENDPOINT_URL, data=request_data, files=files, auth=self.oauth)

                if req.status_code < 200 or req.status_code > 299:
                    print(req.status_code)
                    print(req.text)
                    raise Exception('Error uploading the file.')

                segment_id = segment_id + 1

                print('%s of %s bytes uploaded' % (str(segment_id * 131072), str(self.total_bytes)))

        print('Upload chunks complete.')

    def upload_finalize(self):
        """
        Finalizes uploads and starts video processing
        """
        print('FINALIZE')

        request_data = {
            'command': 'FINALIZE',
            'media_id': self.media_id
        }

        req = self.session.post(url=MEDIA_ENDPOINT_URL, data=request_data, auth=self.oauth)
        print(req.json())

        self.processing_info = req.json().get('processing_info', None)

    def tweet(self):
        """
        Publishes Tweet with attached video
        """
        request_data = {
            'status': self.content,
            'media_ids': self.media_id
        }
        if self.in_reply_to_status_id is not None:
            request_data.update({
                'in_reply_to_status_id': self.in_reply_to_status_id,
                'auto_populate_reply_metadata': True
            })

        req = self.session.post(url=POST_TWEET_URL, data=request_data, auth=self.oauth)
        req.raise_for_status()
        data = req.json()
        created_at = int(datetime.strptime(data['created_at'], "%a %b %d %H:%M:%S %z %Y").timestamp())
        tweet_id = data['id']
        return {'createdAt': created_at, 'tweetId': tweet_id}


def _get_media_category(media_type: str) -> str:
    if 'jpg' in media_type or 'jpeg' in media_type or 'png' in media_type:
        return 'tweet_image'
    elif 'gif' in media_type:
        return 'tweet_gif'
    else:
        raise Exception(f'Unknown media type {media_type}')


if __name__ == '__main__':
    from requests_oauthlib import OAuth1
    from dotenv import load_dotenv
    from secret import keys

    keys = keys['monkstest']
    load_dotenv()
    oauth = OAuth1(os.environ['API_KEY'], client_secret=os.environ['API_SECRET'],
                   resource_owner_key=keys['oauth_token'], resource_owner_secret=keys["oauth_token_secret"])

    tweetPoster = TweetPoster("this is the content",
                             'https://firebasestorage.googleapis.com/v0/b/writing-monks.appspot.com/o/images%2Fposts%2FyZLsWYUICaijqjfSosW0%2F0.png?alt=media&token=8a0e1965-28ee-4047-b249-f28844e07b36',
                              55898, 'image/png', None, oauth)
    print(tweetPoster.post())

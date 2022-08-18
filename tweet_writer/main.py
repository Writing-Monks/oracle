from pdb import set_trace as pdb
import os
import json

from google.cloud import firestore
from requests_oauthlib import OAuth1
from dotenv import load_dotenv

from secret import keys
from tweet_writer.tweet import Tweet
from tweet_writer.tweet_poster import TweetPoster


load_dotenv()
fs = firestore.Client()


def validate_request_data(data):
    if data is None or data == {}:
        return False
    if 'postId' not in data:
        return False
    return True


def result_success(job_id, data):
    return json.dumps({
        'jobRunID': job_id,
        'data': data,
        'result': [data['createdAt'], data['tweetId']],
        'statusCode': 200,
    })


def result_error(job_id, error):
    return json.dumps({
        'jobRunID': job_id,
        'status': 'errored',
        'error': f'There was an error: {error}',
        'statusCode': 500,
    })


def _get_post_data(post_id: str) -> dict:
    doc = fs.collection('posts').document(post_id).get()
    if not doc.exists:
        raise Exception(f'post id {post_id} not found.')
    data = doc.to_dict()
    data['id'] = post_id
    return data


def _get_handle(post_data: dict) -> str:
    doc = fs.collection('publications').document(post_data['pubId']).get()
    if not doc.exists:
        raise Exception(f'publication id {post_data["pubId"]} not found.')
    pub = doc.to_dict()
    return pub['twitterInfo']['handle']


def _get_oauth(handle: str) -> OAuth1:
    account_keys = keys[handle]
    return OAuth1(
        os.environ['API_KEY'], client_secret=os.environ['API_SECRET'],
        resource_owner_key=account_keys['oauth_token'],
        resource_owner_secret=account_keys['oauth_token_secret']
    )


def _get_tweets(post: dict) -> list[Tweet]:
    result = list()
    result.append(Tweet(post['content'], post['mediaUrl'], post['mediaMeta']))
    if post['isThread']:
        sub_tweets = fs.collection('posts').document(post['id']).collection('subTweets').document(post['id'])\
            .get().to_dict()
        for content, media_url, media_meta in zip(sub_tweets['contents'], sub_tweets['mediaUrls'],
                                                  sub_tweets['mediaMetas']):
            result.append(Tweet(content, media_url, media_meta))
    return result


def _tweet(tweets: list[Tweet], oauth: OAuth1) -> dict:
    tweet = tweets[0]
    poster = TweetPoster(tweet.content, tweet.media_url, tweet.total_bytes, tweet.mime_type, None, oauth)
    first_tweet_data = poster.post()
    if len(tweets) > 1:
        parent_id = first_tweet_data['tweetId']
        for tweet in tweets[1:]:
            poster = TweetPoster(tweet.content, tweet.media_url, tweet.total_bytes, tweet.mime_type, parent_id, oauth)
            parent_id = poster.post()['tweetId']
    return first_tweet_data


def create_request(job_id, req_data):
    try:
        post_data = _get_post_data(req_data['postId'])
        handle = _get_handle(post_data)
        if handle not in keys:
            raise Exception(f'Unknown handle {handle}')
        tweets = _get_tweets(post_data)
        oauth = _get_oauth(handle)
        result = _tweet(tweets, oauth)
        return result_success(job_id, result)
    except Exception as e:
        return result_error(job_id, e)


def handle_request(request):
    job_id = request.get('id', '1')
    try:
        req_data = request['data']
        if validate_request_data(req_data):
            return create_request(job_id, req_data)
        else:
            return result_error(job_id, 'Invalid input')
    except KeyError:
        return result_error(job_id, 'Invalid input')

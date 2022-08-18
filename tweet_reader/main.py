from datetime import datetime
import json

from bridge import Bridge


def validate_request_data(data):
    if data is None or data == {}:
        return False
    if 'tweet_fields' not in data or 'tweetId' not in data or 'path' not in data:
        return False
    return True


def result_success(job_id, data):
    return json.dumps({
        'jobRunID': job_id,
        'data': data,
        'result': data['result'],
        'statusCode': 200,
    })


def result_error(job_id, error):
    return json.dumps({
        'jobRunID': job_id,
        'status': 'errored',
        'error': f'There was an error: {error}',
        'statusCode': 500,
    })


def create_request(job_id, url, req_data):
    bridge = Bridge()
    try:
        params = {'tweet.fields': req_data['tweet_fields']}
        response = bridge.request(url, params)
        data = response.json()['data']
        result = data
        for key in req_data['path'].split(','):
            result = result[key]
        if key == 'created_at':  # translate iso-string to timestamp
            result = int(datetime.fromisoformat(result.replace('Z', '+00:00')).timestamp())
        data['result'] = result
        return result_success(job_id, data)
    except Exception as e:
        return result_error(job_id, e)
    finally:
        bridge.close()


def handle_request(request):
    job_id = request.get('id', '1')
    try:
        req_data = request['data']
        if validate_request_data(req_data):
            url = f"https://api.twitter.com/2/tweets/{req_data['tweetId']}"
            return create_request(job_id, url, req_data)
        else:
            return result_error(job_id, 'Invalid input')
    except KeyError:
        return result_error(job_id, 'Invalid input')

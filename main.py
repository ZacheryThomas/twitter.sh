__author__ = 'Zachery Thomas'

import time

import docker
import tweepy

from config import CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET

CLIENT = docker.from_env()
SLEEP_TIMER = 10

def fetch_mentions(api):
    """Fetch mentions from twitter"""
    return api.mentions_timeline()


def fav_tweet(api, reply):
    """Attempt to fav a tweet and return True if successful"""

    # sometimes this raises TweepError even if reply.favorited
    # was False
    try:
        api.create_favorite(id=reply.id)
    except tweepy.TweepError:
        return False

    return True


def clean_tweet_text(tweet):
    """Removes user mentions from tweet"""
    tweet_text = tweet.text

    for user_mentioned in tweet.entities['user_mentions']:
        screen_name = user_mentioned['screen_name']
        tweet_text = tweet_text.replace(('@{}').format(screen_name), '')

    return tweet_text.strip()


def start_container(name):
    """Starts container with a given container name"""
    container = CLIENT.containers.run('alpine', ['tail', '-f', '/dev/null'],
                                      name=str(name), detach=True)
    return container


def run_command(container, cmd):
    """Runs command given container obj and cmd string"""
    cmd = 'sh -c "{}"'.format(str(cmd))

    try:
        res = container.exec_run(cmd)
        print('exit_code: {}, output: {}'.format(res.exit_code, res.output.decode('utf-8')))
        return res.output.decode('utf-8'), res.exit_code
    except Exception as exc:
        return str(exc), 1


def response_formatter(text, username, max_length=140):
    """Formats response to keep tweet under 140 chars"""
    while len('{} @{}'.format(text, username)) > max_length:
        text = text[:-1]

    return '{} @{}'.format(text, username)


def main():
    """Main function"""
    auth = tweepy.OAuthHandler(consumer_key=CONSUMER_KEY, consumer_secret=CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)

    api = tweepy.API(auth_handler=auth, retry_count=3)

    while 1:
        results = fetch_mentions(api)
        for tweet in results:
            if tweet.favorited:
                continue
            fav_tweet(api, tweet)


            username = tweet.user.screen_name
            tweet_text = clean_tweet_text(tweet)

            print('text: {}'.format(tweet_text))
            print('container username: {}'.format(username))
            try:
                container = CLIENT.containers.get(username)

            except docker.errors.NotFound:
                print('Container not found, starting one...')
                container = start_container(username)
                print('Done!')

            res_text, res_code = run_command(container, tweet_text)
            res_text = response_formatter(res_text, username, max_length=140)
            print(res_text, res_code)

            api.update_status(res_text, in_reply_to_status_id=tweet.id)


        time.sleep(SLEEP_TIMER)


if __name__ == "__main__":
    main()

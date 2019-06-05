__author__ = 'Zachery Thomas'

import time
import re
import threading

import docker
import tweepy

from config import CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET

CLIENT = docker.from_env()
AUTH = tweepy.OAuthHandler(consumer_key=CONSUMER_KEY, consumer_secret=CONSUMER_SECRET)
AUTH.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
API = tweepy.API(auth_handler=AUTH, retry_count=3)

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

    return re.sub(r'@\S*', '', tweet_text).strip()


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
    while len('{} @{}'.format(text, username)) > max_length:
        text = text[:-1]

    return '{} @{}'.format(text, username)


class WorkerThread (threading.Thread):
    def __init__(self, tweet):
        threading.Thread.__init__(self)
        self.tweet = tweet

    def run(self):
        if self.tweet.favorited:
            return

        print('tweet not fav, continue')
        fav_tweet(API, self.tweet)

        user_id = str(self.tweet.user.id)
        username = str(self.tweet.user.screen_name)
        tweet_text = clean_tweet_text(self.tweet)

        print('text: {}'.format(tweet_text))
        print('container name: {}'.format(user_id))
        try:
            container = CLIENT.containers.get(user_id)

        except docker.errors.NotFound:
            print('Container not found for {}, starting one...'.format(username))
            container = start_container(username)
            print('Started container for {} as {}'.format(username, user_id))

        res_text, res_code = run_command(container, tweet_text)
        res_text = response_formatter(res_text, username, max_length=140)
        print(res_text, res_code)

        API.update_status(res_text, in_reply_to_status_id=self.tweet.id)


class StreamHelper (tweepy.streaming.StreamListener):
    def on_status(self, status):
        wt = WorkerThread(status)
        wt.start()

    def on_error(self, status_code):
        if status_code == 420:
            print('Hit rate limit :(')

            #returning False in on_data disconnects the stream
            return False


def main():
    """Main function"""
    sh = StreamHelper()
    stream = tweepy.Stream(AUTH, sh, timeout=None)

    screen_name = API.me().screen_name
    stream.filter(track=[screen_name])


if __name__ == "__main__":
    main()
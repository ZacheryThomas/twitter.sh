__author__ = 'Zachery Thomas'

import docker
import tweepy

from config import CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET

CLIENT = docker.from_env()


def fetch_mentions(api):
    """Fetch mentions from twitter"""
    return api.mentions_timeline()


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
    cmd = str(cmd)

    try:
        res = container.exec_run(cmd)
        print('exit_code: {}, output: {}'.format(res.exit_code, res.output.decode('utf-8')))
        return res.output.decode('utf-8'), res.exit_code
    except Exception as exc:
        return str(exc), 1


def main():
    """Main function"""
    auth = tweepy.OAuthHandler(consumer_key=CONSUMER_KEY, consumer_secret=CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)

    api = tweepy.API(auth_handler=auth, retry_count=3)

    results = fetch_mentions(api)

    for tweet in results:
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
        print(res_text, res_code)

        api.update_status(res_text, in_reply_to_status_id=tweet.id)


if __name__ == "__main__":
    main()

__author__ = 'Zachery Thomas'

import subprocess
import docker
import threading
import datetime

from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
from tweepy import API

client = docker.from_env()

def main():
    container = client.containers.run('alpine', ['tail', '-f',  '/dev/null'], detach=True)
    res = container.exec_run(['ls'])
    print('exit_code: {}, output: {}'.format(res.exit_code, res.output.decode('utf-8')))
    cId = container.id
    container.stop()


if __name__ == "__main__":
    main()
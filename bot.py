import os
import time
from datetime import datetime

import wget
import tweepy
from PIL import Image

from mondrianify.MondrianPipeline import MondrianPipeline
import twitter_secrets

class Bot:
    # rate limits
    MAX_TWEETS_SEARCH = 1000
    SECONDS_PER_TWEET = 36

    def __init__(self,
        output_dir='output/',
        tmp_image_in='tmp-image-in.jpg',
        id_file = 'latest_id.txt'
    ):
        self.last_reponse_time = None
        self.output_dir = output_dir
        self.tmp_image_in = tmp_image_in
        self.id_file = id_file

        if os.path.exists(id_file):
            with open(id_file) as f:
                self.latest_id = int(f.read())
        else:
            self.latest_id = None

        consumer_key = twitter_secrets.CONSUMER_KEY
        consumer_secret = twitter_secrets.CONSUMER_SECRET
        access_token = twitter_secrets.ACCESS_TOKEN
        access_token_secret = twitter_secrets.ACCESS_TOKEN_SECRET

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        
        self.twitter = tweepy.API(auth)

        self.latest_tweets_raw = None
        self.latest_tweets = None

    def find_latest_tweets(self):
        """Get all tweets that mention the bot since last checking"""
        latest_tweets = [
            status for status in tweepy.Cursor(
                self.twitter.search,
                q="to:PietMondrianAI",
                result_type="recent",
                count=100,
                since_id=self.latest_id
            ).items(Bot.MAX_TWEETS_SEARCH)
        ]

        self.latest_tweets_raw = [t._json for t in latest_tweets]

        print(f'There are {len(latest_tweets)} tweets in the inbox.')

    
    def store_latest_id(self, tweet):
        """given the latest tweets, store the most recent"""
        with open(self.id_file, 'w') as f:
            f.write(str(tweet['id']))
            self.latest_id = tweet['id']


    def handle_errors(self):
        introduction_tweets = [x for x in self.latest_tweets_raw if self.is_introduction(x)]
        # remove tweets with only text
        filtered_tweets = [x for x in self.latest_tweets_raw if 'media' in x['entities']]
        # ensure proper media formats
        filtered_tweets = [
            t for t in filtered_tweets 
            if any([
                t['entities']['media'][0]['media_url'].endswith(file_format) for file_format in ['.png', '.jpg', '.jpeg']
            ])
        ]
        self.latest_tweets = filtered_tweets + introduction_tweets

        print(f'There are {len(filtered_tweets)} tweets to analyze')

    # -------------------------RESPONSE--------------------------- #

    def is_introduction(self, tweet):
        return ('media' not in tweet['entities']) and (tweet['in_reply_to_status_id'] is None)


    def respond(self, tweet):
        if self.is_introduction(tweet):
            self.wait_if_necessary()
            self.send_tweet(tweet, introduction=True)
            self.last_reponse_time = time.time()
        else:
            self.download_tweet_image(tweet)
            self.apply_image_transform()
            self.wait_if_necessary()
            self.send_tweet(tweet)
            self.last_reponse_time = time.time()


    def wait_if_necessary(self):
        if self.last_reponse_time is not None:
            time_since_last_tweet = time.time() - self.last_reponse_time
            if time_since_last_tweet < Bot.SECONDS_PER_TWEET:
                wait_time = Bot.SECONDS_PER_TWEET - time_since_last_tweet
                print(f'Waiting for {wait_time} seconds...')
                time.sleep(wait_time)


    def download_tweet_image(self, tweet):
        # grab only the first image
        m = tweet['entities']['media'][0]

        # wget has some weird overwrite permissions
        #   for now just remove the file if it exists
        if os.path.exists(self.tmp_image_in):
            os.remove(self.tmp_image_in)

        url = m['media_url']

        wget.download(url, self.tmp_image_in)
        print() # for cleaner shell logs

        # handle pngs
        if url.endswith('.png'):
            im = Image.open(self.tmp_image_in)
            im = im.convert('RGB')
            im.save(self.tmp_image_in)


    def apply_image_transform(self, random=False):
        mp = MondrianPipeline(self.tmp_image_in, output_dir=self.output_dir, random=random)
        mp.apply_image_transform()


    def send_tweet(self, tweet, reply=True, introduction=False):
        if not introduction:
            select_filenames = [
                '0-resize.jpg',
                '3-find-structure.jpg',
                '4-create-painting.jpg',
                '5-create-overlay.jpg'
            ]

            filenames = sorted([self.output_dir+x for x in select_filenames])

            media_ids = [self.twitter.media_upload(filename).media_id for filename in filenames]
            assert len(media_ids) <= 4

            # Tweet with multiple images
            if reply:
                sent = self.twitter.update_status(
                    status=f"@{tweet['user']['screen_name']}",
                    media_ids=media_ids,
                    in_reply_to_status_id=tweet['id']
                )

            else:
                sent = self.twitter.update_status(
                    status=f"",
                    media_ids=media_ids,
                )
        else:
            sent = self.twitter.update_status(
                status=f"@{tweet['user']['screen_name']} Hello! Reply with an image and I'll paint it for you 🎨😁",
                in_reply_to_status_id=tweet['id']
            )

        print(f'Sent tweet! ID: {sent.id}')


    def tweet_random_photo(self):
        self.apply_image_transform(random=True)
        self.send_tweet(None, reply=False)


    def respond_to_latest_tweets(self):
        self.last_reponse_time = None
        for tweet in reversed(self.latest_tweets):
            self.respond(tweet)
            self.store_latest_id(tweet) 


    def start(self):
        while True:
            try:
                self.find_latest_tweets()
                self.handle_errors()

                if len(self.latest_tweets) == 0 and datetime.now().minute % 10 == 0:
                    self.tweet_random_photo()
                else:
                    self.respond_to_latest_tweets()

                if len(self.latest_tweets) == 0:
                    time.sleep(60)
            except Exception as err:
                print('Something went wrong: ')
                print(err)
                if 'Twitter' in str(err):
                    time.sleep(900)
            
# -------------------------------------------------------------------- #
    
def main():
    bot = Bot()
    bot.start()

if __name__ == '__main__':
    main()
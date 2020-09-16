import os
import time
from datetime import datetime

import wget
import tweepy
from PIL import Image

from mondrianify.MondrianPipeline import MondrianPipeline


class Bot:
    # Twitter rate limits
    MAX_TWEETS_SEARCH = 1000
    SECONDS_PER_TWEET = 36

    def __init__(self,
        output_dir='output/',
        tmp_image_in='tmp-image-in.jpg',
        id_file='latest_id.txt'
    ):
        self.output_dir = output_dir
        self.tmp_image_in = tmp_image_in
        self.id_file = id_file

        # find where the bot left off on startup
        if os.path.exists(id_file):
            with open(id_file) as f:
                item = f.read()
                self.latest_id = None if item == '' else int(item)
        else:
            self.latest_id = None

        # configure twitter API
        consumer_key = os.environ['CONSUMER_KEY']
        consumer_secret = os.environ['CONSUMER_SECRET']
        access_token = os.environ['ACCESS_TOKEN']
        access_token_secret = os.environ['ACCESS_TOKEN_SECRET']
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.twitter = tweepy.API(auth)

        # vars to be set later
        self.last_reponse_time = None
        self.latest_tweets_raw = None
        self.latest_tweets = None

    def find_latest_tweets(self):
        """Get all tweets that mention the bot"""

        # If no latest_id, don't send any tweets, and just store the latest one
        if self.latest_id is None:
            latest_tweet = self.twitter.search(
                q="@PietMondrianAI",
                result_type="recent",
                count=1
            )[0]

            self.store_id(latest_tweet._json)

            self.latest_tweets_raw = []

            print('Collected latest tweet. Will not respond.')

        else:
            latest_tweets = [
                status for status in tweepy.Cursor(
                    self.twitter.search,
                    q="@PietMondrianAI",
                    result_type="recent",
                    count=100,
                    since_id=self.latest_id,
                    tweet_mode='extended'
                ).items(Bot.MAX_TWEETS_SEARCH)
            ]

            self.latest_tweets_raw = [t._json for t in latest_tweets]

            print(f'There are {len(latest_tweets)} tweets in the inbox.')

    
    def store_id(self, tweet):
        """Store the id of the given tweet into the id file"""
        with open(self.id_file, 'w') as f:
            f.write(str(tweet['id']))
            self.latest_id = tweet['id']


    def filter_tweets(self):
        """Of the tweets that mention the bot, which should it respond to?"""
        introduction_tweets = [x for x in self.latest_tweets_raw if self.requires_introduction(x)]
        
        # Remove tweets with only text
        media_tweets = [x for x in self.latest_tweets_raw if 'media' in x['entities']]
        # Ensure proper media formats
        media_tweets = [
            t for t in media_tweets 
            if any([
                t['entities']['media'][0]['media_url'].endswith(file_format) for file_format in ['.png', '.jpg', '.jpeg']
            ])
        ]
        
        # Combine the categories
        # NOTE: If expanded in the future, make sure it's a unique set.
        self.latest_tweets = media_tweets + introduction_tweets

        print(f'There are {len(self.latest_tweets)} tweets to respond to.')


    def requires_introduction(self, tweet):
        """Define what tweets should receive an introduction"""
        return ('media' not in tweet['entities']) and (tweet['in_reply_to_status_id'] is None)


    def prepare_and_send_response_tweet(self, tweet):
        """Categorize the different responses the bot makes and prepare the tweet"""
        if self.requires_introduction(tweet):
            self.send_tweet(tweet, tweet_type='introduction')
        else:
            try:
                self.download_tweet_image(tweet)
                self.apply_image_transform()
                self.send_tweet(tweet)
            except Exception as err:
                self.send_tweet(tweet, tweet_type='error')
                print('Error tweet sent. This was the error: ')
                print(err)
        

    def wait_if_necessary(self):
        """Use twitter's rate limits to best pace tweets"""
        if self.last_reponse_time is not None:
            time_since_last_tweet = time.time() - self.last_reponse_time
            if time_since_last_tweet < Bot.SECONDS_PER_TWEET:
                wait_time = Bot.SECONDS_PER_TWEET - time_since_last_tweet
                print(f'Waiting for {wait_time} seconds...')
                time.sleep(wait_time)
        self.last_reponse_time = time.time()


    def download_tweet_image(self, tweet):
        """Download the first image in the given tweet"""
        media_dict = tweet['entities']['media'][0]

        # wget has some weird overwrite permissions
        #   for now just remove the file if it exists
        if os.path.exists(self.tmp_image_in):
            os.remove(self.tmp_image_in)

        url = media_dict['media_url']

        wget.download(url, self.tmp_image_in)
        print() # for cleaner shell logs

        # handle pngs
        if url.endswith('.png'):
            im = Image.open(self.tmp_image_in)
            im = im.convert('RGB')
            im.save(self.tmp_image_in)


    def apply_image_transform(self, random=False):
        """Implement the Mondrian pipeline to transform image"""
        mp = MondrianPipeline(self.tmp_image_in, output_dir=self.output_dir, random=random)
        mp.apply_image_transform()


    def send_tweet(self, tweet, tweet_type="reply_transform"):
        """Given the message category, configure media and text and send tweet.
        
        Types of tweets
            random: tweet a random photo from unsplash to own timeline.
            reply_transform: reply with the user's image having gone through the pipeline
            introduction: reply to user who mentions the bot asking for a photo.
            error: reply to user if there was an issue processing their photo.
        """

        self.wait_if_necessary()

        if tweet_type != 'random':
            self.store_id(tweet)

        if tweet_type in ['reply_transform', 'random']:
            # Prepare the files to be used in tweet and upload them.
            select_filenames = [ '0-resize.jpg', '3-find-structure.jpg', 
                '4-create-painting.jpg', '5-create-overlay.jpg']
            filenames = sorted([self.output_dir+x for x in select_filenames])
            media_ids = [self.twitter.media_upload(f).media_id for f in filenames]

            sent = self.twitter.update_status(
                status=(f"@{tweet['user']['screen_name']}" if tweet_type == 'reply_transform' else ""),
                media_ids=media_ids,
                in_reply_to_status_id=(tweet['id'] if tweet_type == 'reply_transform' else None)
            )
        
        elif tweet_type == 'introduction':
            sent = self.twitter.update_status(
                status=f"@{tweet['user']['screen_name']} Hello! Reply with an image and I'll paint it for you 🎨😁",
                in_reply_to_status_id=tweet['id']
            )

        elif tweet_type == 'error':
            sent = self.twitter.update_status(
                status=(f"@{tweet['user']['screen_name']} Hm, looks like I'm" +
                " having trouble with this one 😕 I work best on images with" + 
                " clearly-defined objects. Maybe alter the image slightly and" +
                " try again? I may also be down because of a larger issue," +
                " but hopefully that's not the case."),
                in_reply_to_status_id=tweet['id']
            )

        else:
            assert False, 'Improper tweet_type provided'

        print(f'Sent tweet! ID: {sent.id}')


    def tweet_random_photo(self):
        """Post random photo to the bot's timeline"""
        self.apply_image_transform(random=True)
        self.send_tweet(None, tweet_type='random')


    def respond_to_latest_tweets(self):
        """Grab the latest_tweets var and respond to them in reverse order"""
        for tweet in reversed(self.latest_tweets):
            self.prepare_and_send_response_tweet(tweet)


    def start(self):
        """Run entire workflow"""
        while True:
            # try:
            # Get all the tweets the bot needs to respond to
            self.find_latest_tweets()
            self.filter_tweets()
            # If bored, tweet a random photo, otherwise respond to those tweets
            if len(self.latest_tweets) == 0 and datetime.now().hour == 13 and datetime.now().minute == 0:
                self.tweet_random_photo()
            else:
                self.respond_to_latest_tweets()
            # Wait before searching again.
            if len(self.latest_tweets) < 2:
                time.sleep(60)

            # except Exception as err:
            #     print('Something went wrong: ')
            #     print(err)
            #     # If Twitter is in the error, it's likely a rate limiting problem,
            #     #  so wait 15 minutes, otherwise wait a minute.
            #     if 'Twitter' in str(err):
            #         time.sleep(900)
            #     else:
            #         time.sleep(60)
            
# -------------------------------------------------------------------- #
    
def main():
    bot = Bot()
    bot.start()

if __name__ == '__main__':
    main()
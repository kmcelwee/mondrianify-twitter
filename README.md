# mondrian-twitter

A Twitter bot wrapper for the [mondrianify repository](https://github.com/kmcelwee/mondrianify/), a pipeline for turning images into paintings by Piet Mondrian. The attached bot ([@PietMondrianAI](https://twitter.com/PietMondrianAI)) is deployed to [Heroku](https://dashboard.heroku.com/).

~ ~ ~ ADD TWITTER INTERACTION SCREENSHOT ~ ~ ~

### bot.py
A bot class to handle all requests and process the different kinds of tweets we'd like to send:
- `introduction`: If a user mentions the bot, it will introduce itself and ask for an image.
- `random`: The bot grabs a random image of a random dimension using [Unsplash](https://unsplash.com/developers) and runs the transformation on the image. It tweets the results.
- `reply_transform`: If there is an image in a tweet that mentions this bot, take the first image, apply the Mondrian tranform, and tweet the results.
- `error`: If given a blank or undistinct image the clustering algorithms will fail. The bot will respond with a brief explanation of what might have gone wrong.

### latest_id.txt
The ID of the last tweet the bot processed. On restart, we can configure what tweet we'd like the bot to continue from. This is referenced in the search "since_id" keyword argument in the search API. Twitter will fetch all tweets that fit our query and occur after (but not including) the given tweet id.

### Procfile
The file that runs our Heroku app. The contents are simply `python bot.py`

### Aptfile
A file that helps handle some of the unique dependencies we have with running `opencv-python` on Heroku. 

### mondrianify
The submodule that links to the [mondrianify repository](https://github.com/kmcelwee/mondrianify/), which contains all the code necessary to process an image.

## Twitter API and rate limits
Given [Twitter's rate limits](https://developer.twitter.com/en/docs/basics/rate-limits), the bot can only tweet once or twice a minute, with a backlog of about 1000 tweets. More specifically, there are only two unique Twitter API calls used: one to listen for new mentions (via search) and one to update status. In other words, it can process one request per 36 seconds, and the max queue is 1000 tweets.

## Local and remote setup

This repo is deployed to Heroku, which simply installs the packages in `requirements.txt` and launches the bot with `python bot.py`. However to run a similar bot locally or replicate this repo there are some other configurations you'll have to keep in mind.

### Configuring secrets
Twitter requires that you register as a developer in order to interact with their platform and/or request data. ([Apply to be a Twitter developer](https://developer.twitter.com/en/apply-for-access)).

For easy local setup, I recommend creating a shell script `twitter_secrets.sh` to briefly add these variables to your shell, something like:
```shell
export CONSUMER_KEY=xxxxxx
export CONSUMER_SECRET=xxxxxx
export ACCESS_TOKEN=xxxxxx
export ACCESS_TOKEN_SECRET=xxxxxx
```

If deploying to Heroku, you'll need to [add these environment variables manually](https://devcenter.heroku.com/articles/config-vars).

### Using `opencv-python`
Using `opencv-python` (the library used to apply deep learning techniques to our input images) on Heroku requires some additional setup that isn't reflected in the `Procfile`. Assuming you've properly [downloaded and configured heroku for your repository](https://devcenter.heroku.com/start), the following command needs to be run:

```shell
heroku buildpacks:add --index 1 heroku-community/apt
```

The specifics of these packages are referenced in `Aptfile`

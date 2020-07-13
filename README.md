# mondrian-twitter

A Twitter bot wrapper for the [mondrianify repository](https://github.com/kmcelwee/mondrianify/), a pipeline for turning images into paintings by Piet Mondrian. The attached bot ([@PietMondrianAI](https://twitter.com/PietMondrianAI)) is deployed to [Heroku](https://dashboard.heroku.com/) and 


<blockquote class="twitter-tweet"><p lang="und" dir="ltr"><a href="https://t.co/rMcQl4fZ4U">pic.twitter.com/rMcQl4fZ4U</a></p>&mdash; Piet Mondrian (@PietMondrianAI) <a href="https://twitter.com/PietMondrianAI/status/1282600963627524096?ref_src=twsrc%5Etfw">July 13, 2020</a></blockquote> <script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script> 


### bot.py
A bot class to handle all requests and process the different kinds of tweets we'd like to send:
- `introduction`: If a user mentions the bot, it will introduce itself and ask for an image.
	- Note: This is queried using "@PietMondrianAI", but if one wanted to simply 
- `random`: The bot grabs a random image of a random dimension using Unsplash (LINK) and runs a transformation on it. It tweets the results.
- `reply_transform`: If there is an image in the tweet that mentions this bot, take the first image, apply the Mondrian tranform, and tweet the results.
- `error`: If given a blank or undistinct image the clustering algorithms will fail. The bot will respond with a brief explanation of what might have gone wrong.

### latest_id.txt
External storage of the last tweet the bot responded to. On restart, we can configure what tweet we'd like the bot to continue from.

This is referenced in the search "since_id" keyword argument. Twitter will fetch all tweets that fit our query and occur after (but not including) the given tweet id.

## Procfile
The file that runs our Heroku app. The contents are simply `python bot.py`

## Aptfile
A file that helps handle some of the unique dependencies we have with running `opencv-python` on Heroku. See 

## mondrianify
The submodule that links to the ### mondrianify repo, which contains all the code necessary to process the image.

## Twitter API and rate limits
https://developer.twitter.com/en/docs/basics/rate-limits

Given Twitter's rate limits, the bot can only tweet once or twice a minute, with a backlog of about 1000 tweets. More specifically, there are two unique Twitter API calls used: one to listen for new mentions (via search) and one to update status. It can process one request per 36 seconds, but the max queue is 1000 tweets.

---

## Local and remote setup

This repo is deployed to Heroku, launching the simple Procfile `python bot.py` and installing the packages in `requirements.txt`. However to run a similar bot locally or replicate this repo there are some other configurations you'll have to keep in mind.

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
Using `opencv-python` (the library used to apply deep learning techniques to our input images) on Heroku requires some additional setup that isn't reflected in the `Procfile`. The following command needs to be run:

```shell
heroku buildpacks:add --index 1 heroku-community/apt
```

The specifics of these packages are referenced in `Aptfile`

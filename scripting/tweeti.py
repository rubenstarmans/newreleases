import tweepy
import configparser


def get_auth(path):
    # Open configuration.
    config = configparser.ConfigParser()
    config.read(path + "newreleases/resources/config.cfg")

    # Authentication
    auth = tweepy.OAuthHandler(config.get("TWITTER", "CONSUMER_KEY"), config.get("TWITTER", "CONSUMER_SECRET"))
    auth.set_access_token(config.get("TWITTER", "ACCESS_TOKEN"), config.get("TWITTER", "ACCESS_TOKEN_SECRET"))
    api = tweepy.API(auth)

    return api

def tweet(message, api):
    api.update_status(message)

def update_profile_image(image, api):
    api.update_profile_image(image)


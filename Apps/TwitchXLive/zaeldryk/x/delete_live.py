#!/usr/bin/env python3
import os
import tweepy

CONFIG = os.environ.get("X_CONFIG_PATH", "/home/ubuntu/x_config.env")
POST_ID_FILE = os.environ.get(
    "X_POST_ID_FILE", "/home/ubuntu/zaeldryk/state/last_x_post_id.txt"
)
LEGACY = "/home/ubuntu/last_x_post_id.txt"


def load_env(path=CONFIG):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def main():
    path = POST_ID_FILE if os.path.exists(POST_ID_FILE) else LEGACY
    if not os.path.exists(path):
        print("Aucun post à supprimer")
        return
    with open(path) as f:
        tweet_id = f.read().strip()
    if not tweet_id:
        print("ID vide")
        return
    env = load_env()
    client = tweepy.Client(
        consumer_key=env["X_API_KEY"],
        consumer_secret=env["X_API_SECRET"],
        access_token=env["X_ACCESS_TOKEN"],
        access_token_secret=env["X_ACCESS_SECRET"],
    )
    try:
        client.delete_tweet(tweet_id)
        print(f"Supprimé : {tweet_id}")
        clear_ids = True
    except tweepy.TweepyException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status == 404:
            print(f"déjà absent : {tweet_id}")
            clear_ids = True
        else:
            raise
    if clear_ids:
        for p in (POST_ID_FILE, LEGACY, path):
            try:
                os.remove(p)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    main()

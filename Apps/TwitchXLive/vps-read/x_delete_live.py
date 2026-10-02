#!/usr/bin/env python3
import os
import tweepy

def load_env(path="/home/ubuntu/x_config.env"):
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
    path = "/home/ubuntu/last_x_post_id.txt"
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

    client.delete_tweet(tweet_id)
    os.remove(path)
    print(f"Supprimé : {tweet_id}")

if __name__ == "__main__":
    main()

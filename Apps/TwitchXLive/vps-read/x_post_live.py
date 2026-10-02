#!/usr/bin/env python3
import sys
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
    title = sys.argv[1] if len(sys.argv) > 1 else "Live"
    env = load_env()

    client = tweepy.Client(
        consumer_key=env["X_API_KEY"],
        consumer_secret=env["X_API_SECRET"],
        access_token=env["X_ACCESS_TOKEN"],
        access_token_secret=env["X_ACCESS_SECRET"],
    )

    text = f"🔴 LIVE — {title}\nhttps://www.twitch.tv/zaeldryk"
    if len(text) > 280:
        prefix = "🔴 LIVE — "
        suffix = "\nhttps://www.twitch.tv/zaeldryk"
        text = f"{prefix}{title[: 280 - len(prefix) - len(suffix)].rstrip()}{suffix}"

    resp = client.create_tweet(text=text)
    tweet_id = resp.data["id"]

    with open("/home/ubuntu/last_x_post_id.txt", "w") as f:
        f.write(str(tweet_id))

    print(f"Posté : {tweet_id}")


if __name__ == "__main__":
    main()

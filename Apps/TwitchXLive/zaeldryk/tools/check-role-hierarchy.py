#!/usr/bin/env python3
import json, urllib.request
from pathlib import Path
token=[l.split('=',1)[1].strip().strip('"').strip("'") for l in Path('/home/ubuntu/zaeldryk/config/discord.env').read_text().splitlines() if l.startswith('DISCORD_BOT_TOKEN=')][0]
G='867426693286461490'
R='1541249416374259863'
h={'Authorization':'Bot '+token,'User-Agent':'check'}
g=json.load(urllib.request.urlopen(urllib.request.Request(f'https://discord.com/api/v10/guilds/{G}', headers=h)))
roles=json.load(urllib.request.urlopen(urllib.request.Request(f'https://discord.com/api/v10/guilds/{G}/roles', headers=h)))
bot=json.load(urllib.request.urlopen(urllib.request.Request('https://discord.com/api/v10/users/@me', headers=h)))
mem=json.load(urllib.request.urlopen(urllib.request.Request(f'https://discord.com/api/v10/guilds/{G}/members/{bot["id"]}', headers=h)))
bot_pos=max((r['position'] for r in roles if r['id'] in mem.get('roles',[])), default=0)
t=next(r for r in roles if r['id']==R)
print('premium_tier', g.get('premium_tier'))
print('role_name', t['name'], 'role_pos', t['position'])
print('bot_max_pos', bot_pos, 'can_edit_role', bot_pos > t['position'])
for r in sorted(roles, key=lambda x: -x['position'])[:8]:
    print(r['position'], r['name'])

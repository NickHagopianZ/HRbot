import discord
import os
import logging
import time
import asyncio
import json
import inspect
# from concurrent.futures import ThreadPoolExecutor

intents = discord.Intents.default()
intents.members = True
intents.typing = True
intents.presences = True
client = discord.Client(guild_subscriptions=True, intents=intents)

check_mark = '\u2705'
cross_mark = '\u274C'
test_channel = 'test'
gamestate = {}
channel_list = {}
webhook_list = {}


def update():
    print('update')
    print(json.dumps(gamestate))
    with open('/root/HRbot/players.json', 'w') as file:
        file.write(json.dumps(gamestate))


@client.event
async def on_ready():
    print('starting up bot')
    await index(client)


async def index(client):
    with open('/root/HRbot/players.json', 'r') as file:
        filestate = json.load(file)
        print(json.dumps(filestate))
        filestate['valid_channels']['player_channels'] = []
    print(json.dumps(filestate))

    for guild in client.guilds:
        for channel in guild.text_channels:
            if channel.category is None:
                continue
            elif channel.category.name.lower() in filestate['acceptable_sources']:
                webhooks = await channel.webhooks()
                if len(webhooks) == 0:
                    print(f'creating {channel.name.lower()} webhook')
                    webhook_list[channel.name.lower()] = await channel.create_webhook(
                        name=channel.name.lower())
                else:
                    print(f'using existing webhook for {channel.name}')
                    for web in webhooks:
                        webhook_list[channel.name.lower()] = web
                channel_list[channel.name.lower()] = channel
                if channel.name.lower() == 'test':
                    continue
                # elif channel.name.lower() in filestate['valid_channels']['eliminated_channels']:
                #   continue
                elif channel.category.name.lower() == 'terminals':
                    filestate['valid_channels']['player_channels'].append(
                        channel.name)
    print(json.dumps(filestate))

    global gamestate
    gamestate = filestate
    update()


def move(player, action):
    global gamestate
    if (action == 'activate' and
            player in gamestate['valid_channels']['eliminated_channels']):
        gamestate['valid_channels']['eliminated_channels'].remove(player.lower())
        gamestate['valid_channels']['executive_channels'].append(player.lower())
    elif (action == 'deactivate' and
            player not in gamestate['valid_channels']['eliminated_channels']):
        gamestate['valid_channels']['player_channels'].remove(player.lower())
        gamestate['valid_channels']['eliminated_channels'].append(player.lower())
        gamestate['valid_channels']['eliminated_channels'].remove(player.lower())
    else:
        print('invalid')
    update()


async def send_message(
        messageObj, message, recipient, username=None, avatar_url=None):
    eliminated_channels = gamestate['valid_channels']['eliminated_channels']
    player_channels = gamestate['valid_channels']['player_channels']
    if recipient.lower() in eliminated_channels:
        await messageObj.add_reaction(cross_mark)
        await messageObj.channel.send('This player is no longer with us...')
    elif (gamestate['sever'] == 'climbers' and
            messageObj.channel.name in player_channels and
            recipient.lower() in player_channels):
        await messageObj.add_reaction(cross_mark)
        await messageObj.channel.send('You cannot message other climbers at this time')
    elif (recipient.lower() in (
            gamestate['valid_channels']['executive_channels'] +
            gamestate['valid_channels']['player_channels'] + ['test'])):
        try:
            # channel_id = channel_list[recipient.lower()]
            # to_channel = client.get_channel(channel_id)
            to_channel = channel_list[recipient.lower()]
            print(message)
            print(messageObj.attachments)
            if messageObj.attachments == [] and message == '':
                raise Exception('Empty message')
            # attachments = None
            # result = await to_channel.send(message)
            # print(f'result is {result}')
            # if messageObj.attachments:
            #     for attachment in messageObj.attachments:
            #         await to_channel.send(attachment)
            # if messageObj.attachments:
            #     attachments = messageObj.attachments
            await impersonate(
                messageObj, to_channel, recipient, message, username,
                avatar_url, messageObj.attachments)
            await messageObj.add_reaction(check_mark)
        except Exception as e:
            print(e)
            logging.error(f'{username} - {e}')
            await messageObj.add_reaction(cross_mark)
    else:
        await messageObj.add_reaction(cross_mark)
        await messageObj.channel.send(
            f':exclamation: Incorrect target. Try !list for all targets or '
            '!help for more info :exclamation:')
        # await list_channels(messageObj)


async def impersonate(
        messageObj, channel, recipient, message, username=None,
        avatar_url=None, attachments=None):
    # webhook = await channel.create_webhook(name=username)
    webhook = webhook_list[recipient.lower()]
    await debug(messageObj, f'webhook is {webhook}')
    if message != '':
        result = await webhook.send(
            message, username=username, avatar_url=avatar_url)
        await debug(messageObj, f'result is {result}')
    if attachments:
        for attachment in attachments:
            # await to_channel.send(attachment)
            await webhook.send(
                attachment, username=username, avatar_url=avatar_url)
    # await webhook.delete()
    # webhooks = await channel.webhooks()
    # for web in webhooks:
    #     await web.delete()


async def announce(messageObj, target, message):
    target_channels = []
    if target.lower() == 'executives':
        target_channels = gamestate['valid_channels']['executive_channels']
    elif target.lower() == 'climbers':
        target_channels = gamestate['valid_channels']['player_channels']
    elif target.lower() in ['both', 'all']:
        target_channels = (
            gamestate['valid_channels']['player_channels'] +
            gamestate['valid_channels']['executive_channels'])
    else:
        await messageObj.channel.send(
            f':exclamation: Incorrect target. Try !help for more info '
            ':exclamation:')
        return
    for channel in channel_list.keys():
        if channel in target_channels:
            # await debug(messageObj, f'channel is {channel}')
            # await debug(messageObj, f'{message}')
            channel_id = channel_list[channel]
            to_channel = client.get_channel(channel_id)
            if message:
                await to_channel.send(message)
            if messageObj.attachments:
                for attachment in messageObj.attachments:
                    await to_channel.send(attachment)
            # await send_message(messageObj, message, channel)


async def help_message(messageObj):
    print_string = inspect.cleandoc('''
        > to message another terminal:
        > `!msg [recipient name] [message to send]`
        >
        > to list all permitted terminals to message:
        > `!list`
        ''')
    if (messageObj.channel.category.name.lower() == 'founders hall'):
        print_string = print_string + inspect.cleandoc(f'''>
        The following commands only work in founders-hall
        >
        > to message all climbers, all executives or all players (climbers + executives):
        > `!announce [climbers|executives|both] [message to send]`
        >
        > to disable the bot for certain interactions:
        > `!sever [all|climbers|off]`
        > This is presently **{gamestate['sever']}**
        >
        > to disable a climber:
        > `!kill [climber name]`
        >
        > to disable a climber:
        > `!revive [climber name]`''')

    await messageObj.channel.send(print_string)


async def list_channels(messageObj):
    eliminated_channels = gamestate['valid_channels']['eliminated_channels'].copy()
    executive_channels = gamestate['valid_channels']['executive_channels'].copy()
    for channel in executive_channels:
        if channel in eliminated_channels:
            executive_channels.remove(channel)

    player_channels = gamestate['valid_channels']['player_channels'].copy()
    for channel in player_channels:
        if channel in eliminated_channels:
            player_channels.remove(channel)
    executive_string = "- `" + "`\n> - `".join(executive_channels)
    player_string = "- `" + "`\n> - `".join(player_channels)
    eliminated_string = "- `" + "`\n> - `".join(eliminated_channels)
    print_string = inspect.cleandoc(f'''
        > here is a list of permitted climbers/terminals to message:
        > executive's terminals:
        > {executive_string}`
        >
        > climber's terminals:
        > {player_string}`
        ''')

    if (messageObj.channel.category.name.lower() == 'founders hall'):
        print_string = print_string + inspect.cleandoc(f'''>
            > eliminated terminals:
            > {eliminated_string}`''')
    await messageObj.channel.send(print_string)


DEBUG = True
async def debug(messageObj, message):
    if DEBUG:
        logging.warning(f'content is {messageObj.content}')
        logging.warning(f'{messageObj.author} - {message}')
        # print(f'DEBUG: {message}')
        # await messageObj.channel.send(message)


async def get_roles(user):
    try:
        guild = client.guilds[0]
        member = guild.get_member_named(user.display_name)
        roles = member.roles

        # author = guild.get_member_named(user.display_name)
        # await debug(messageObj, author.display_name)#.display_name)#.display_name)
        role_names = []
        for role in roles:
            role_names.append(role.name)
        # print(role_names)
        return role_names
    except Exception as e:
        logging.error(f'1{user.display_name} - {e}')
        # await messageObj.add_reaction(cross_mark)


async def check_perms(user, messageObj):
    try:
        user_roles = await get_roles(user)
        category = messageObj.channel.category.name
        # source_channel = messageObj.channel.name
        if (category.lower() not in gamestate['acceptable_sources']):
            return False
        role_check = False
        for acceptable_role in gamestate['acceptable_roles']:
            # print(f'{acceptable_role} in {user_roles}')
            if acceptable_role in user_roles:
                role_check = True
        return role_check
    except Exception as e:
        logging.error(f'{user.display_name} - {e}')
        # await messageObj.add_reaction(cross_mark)


async def sever_access(messageObj):
    split_message = messageObj.content.split()
    target = split_message[1]
    global gamestate
    if target not in ['all', 'climbers', 'off']:
        await messageObj.add_reaction(cross_mark)
        await messageObj.channel.send(
            f':exclamation: Incorrect Target. Try "all", "climbers" or "off" '
            ':exclamation:')
        return
    else:
        gamestate['sever'] = target
        update()
        await messageObj.add_reaction(check_mark)


async def parse_command(messageObj, split_message, user):
    split_message = messageObj.content.split()

    if messageObj.content.lower().startswith('!msg '):
        formatted_message = f'{messageObj.content.split(split_message[1],1)[1]}'
        asyncio.create_task(send_message(
            messageObj, formatted_message, split_message[1],
            user.display_name, user.avatar_url))
        # formatted_message = f'{user.display_name}: {messageObj.content.split(split_message[1],1)[1]}'
        # asyncio.create_task(send_message(messageObj, formatted_message, split_message[1], 'Internal Message', user.avatar_url))
    elif messageObj.content.lower().startswith('!announce '):
        if (messageObj.channel.category.name.lower() != 'founders hall'):
            return
        formatted_message = f'{messageObj.content.split(split_message[1],1)[1]}'
        asyncio.create_task(announce(
            messageObj, split_message[1], formatted_message))
    elif messageObj.content.lower().startswith('!kill '):
        if (messageObj.channel.category.name.lower() != 'founders hall'):
            return
        move(split_message[1], 'deactivate')
    elif messageObj.content.lower().startswith('!revive '):
        if (messageObj.channel.category.name.lower() != 'founders hall'):
            return
        move(split_message[1], 'activate')
    elif messageObj.content.lower() == '!list':
        asyncio.create_task(list_channels(messageObj))
    elif messageObj.content.lower() == '!help':
        asyncio.create_task(help_message(messageObj))
    elif messageObj.content.lower().startswith('!'):
        await messageObj.channel.send(
            f':exclamation: unknown command :exclamation:\nTry !help for '
            'more info')


def valid_message(messageObj, user) -> bool:
    if not messageObj.content.startswith('!'):
        return False
    if user == client.user:
        return False
    if client.is_ws_ratelimited():
        await debug(messageObj, f'is rate limited={client.is_ws_ratelimited()}')
    perms = await check_perms(user, messageObj)
    if not perms:
        return False

    if messageObj.content.lower().startswith('!sever '):
        if (messageObj.channel.category.name.lower() != 'founders hall'):
            return
        await sever_access(messageObj)
        return False

    if (messageObj.content.lower().startswith('!msg ') and
            gamestate['sever'] == 'all' and
            messageObj.channel.category.name.lower() != 'founders hall'):
        await messageObj.channel.send(
            f':exclamation: all messaging is disabled presently')
        await messageObj.add_reaction(check_mark)
        return False
    return True


@client.event
async def on_message(messageObj):
    user = messageObj.author
    if valid_message(messageObj, user):
        parse_command(messageObj, user)

token = os.getenv('DISCORD_TOKEN')
client.run(token)

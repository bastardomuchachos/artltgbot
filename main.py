import asyncio
import functools
import json
import logging
import re
import signal

import aiohttp
from aiosocksy.connector import ProxyConnector, ProxyClientRequest


PROXY = ...
LOG_FORMAT = '%(levelname)s:%(funcName)s:%(lineno)d: %(message)s'
LOG_DATE_FMT = '%Y-%m-%d %H:%M'
LOG_PATH = 'log.log'
LOG_LEVEL = 'ERROR'
TOKEN = ...
API = 'https://api.telegram.org/bot597103692:AAFjHm1X5MH45Iiq0ghxD0IuBW6iFDnelX4/'
sendMessage = API+'sendMessage'
getUpdate = API+'getUpdates'
BOT_NAME = ...
COMMAND = 'setagr'
COMMAND_PATTERN = re.compile('^\/{}({})?'.format(COMMAND, BOT_NAME))
TOKENIZER = re.compile('[ .,]')


def signal_handler(stop_event, signum, _):
    logging.info('terminating: %d' % signum)
    stop_event.set()
    print('terminating...')


def is_bot_command(text):
    if COMMAND_PATTERN.match(text):
        return True
    return False


def process_command(text, chat_id, agrs):
    tokens = COMMAND_PATTERN.sub('', text).split()
    if len(tokens) > 1:
        agrs[chat_id] = (tokens[0], ' '.join(tokens[1:]))
        text_to_send = '"{}" word added'.format(tokens[0])
    else:
        text_to_send = 'wrong command format'
    return text_to_send


async def msg_handler(session, stop_event):
    last_update_id = 0
    agrs = {}

    while not stop_event.is_set():
        await asyncio.sleep(2)
        try:
            req_params = {'params': {'offset': last_update_id},
                          'proxy': PROXY}
            async with session.get(getUpdate, **req_params) as response:
                update_obj = await response.json()
        except aiohttp.ClientError as e:
            logging.error(e)
            continue

        if not (update_obj['ok'] and update_obj['result']):
            continue

        logging.info(update_obj)

        last_update = update_obj['result'][-1]

        if last_update_id <= last_update['update_id']:
            last_update_id = last_update['update_id'] + 1

        if not last_update.get('message', {}).get('text', None):
            continue

        msg = last_update['message']
        chat_id = msg['chat']['id']
        text = msg['text']

        if is_bot_command(text):
            text_to_send = process_command(text, chat_id, agrs)
        elif chat_id in agrs and agrs[chat_id][0] in TOKENIZER.split(text):
            text_to_send = agrs[chat_id][1]
        else:
            continue

        try:
            req_params = {'data': {'text': text_to_send, 
                                   'chat_id': chat_id},
                          'proxy': PROXY}
            async with session.post(sendMessage, **req_params):
                pass
        except aiohttp.ClientConnectionError as e:
            logging.error(e)
            break


async def main():
    stop_event = asyncio.Event()
    signal.signal(signal.SIGINT, functools.partial(signal_handler, stop_event))
    session_params = {'connector': ProxyConnector(),
                      'request_class': ProxyClientRequest}
    async with aiohttp.ClientSession(**session_params) as session:
        await msg_handler(session, stop_event)


if __name__ == '__main__':
    logging.basicConfig(filename=LOG_PATH,
                        datefmt=LOG_DATE_FMT,
                        format=LOG_FORMAT,
                        level=logging.getLevelName(LOG_LEVEL))
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except Exception as e:
        logging.exception(e)
    finally:
        loop.close()

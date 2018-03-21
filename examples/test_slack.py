import json
from pathlib import Path

import aiohttp
import pytest

import slack
import snug
from gentools import sendreturn

live = pytest.config.getoption('--live')

CRED_PATH = Path('~/.snug/slack.json').expanduser()
token = CRED_PATH.read_text().strip()


@pytest.fixture(scope='module')
async def exec():
    async with aiohttp.ClientSession() as client:
        yield snug.async_executor(auth=slack.token_auth(token),
                                  client=client)


@pytest.mark.asyncio
async def test_channel_list(exec):
    lookup = slack.channels.list_(exclude_archived=True)

    if live:
        result = await exec(lookup)
        assert isinstance(result.content[0], slack.Channel)

    query = iter(lookup)

    req = next(query)
    assert req.url.endswith('channels.list')
    assert req.params['exclude_archived'] == 'true'

    outcome = sendreturn(query, snug.Response(200, CHANNEL_LIST_RESULT))
    assert isinstance(outcome[0], slack.Channel)
    assert len(outcome[0].members) == 2
    assert outcome.next_query.cursor == "dGVhbTpDMUg5UkVTR0w="


@pytest.mark.asyncio
async def test_channel_create(exec):
    create = slack.channels.create('test channel')

    query = iter(create)
    req = next(query)
    assert req.method == 'POST'
    assert req.url.endswith('channels.create')
    assert req.headers['Content-Type'] == 'application/json'
    assert json.loads(req.content) == {
        'name': 'test channel'
    }
    channel = sendreturn(query, snug.Response(200, CREATE_CHANNEL_RESPONSE))
    assert isinstance(channel, slack.Channel)
    assert channel.id == 'C0DEL09A5'


@pytest.mark.asyncio
async def test_post_chat_message(exec):
    post = slack.chat.post_message('#python', 'test message')

    query = iter(post)
    req = next(query)
    assert req.method == 'POST'
    assert req.url.endswith('chat.postMessage')
    assert req.headers['Content-Type'] == 'application/json'
    assert json.loads(req.content) == {
        'channel': '#python',
        'text': 'test message'
    }

    msg = sendreturn(query, snug.Response(200, POST_MESSAGE_RESPONSE))
    assert isinstance(msg, slack.Message)
    assert msg.text == 'Here\'s a message for you'


CHANNEL_LIST_RESULT = b'''\
{
    "ok": true,
    "channels": [
        {
            "id": "C0G9QF9GW",
            "name": "random",
            "is_channel": true,
            "created": 1449709280,
            "creator": "U0G9QF9C6",
            "is_archived": false,
            "is_general": false,
            "name_normalized": "random",
            "is_shared": false,
            "is_org_shared": false,
            "is_member": true,
            "is_private": false,
            "is_mpim": false,
            "members": [
                "U0G9QF9C6",
                "U0G9WFXNZ"
            ],
            "topic": {
                "value": "Other stuff",
                "creator": "U0G9QF9C6",
                "last_set": 1449709352
            },
            "purpose": {
                "value": "A place for non-work-related flimflam, faffing, \
hodge-podge or jibber-jabber you'd prefer to keep out of more focused \
work-related channels.",
                "creator": "",
                "last_set": 0
            },
            "previous_names": [],
            "num_members": 2
        },
        {
            "id": "C0G9QKBBL",
            "name": "general",
            "is_channel": true,
            "created": 1449709280,
            "creator": "U0G9QF9C6",
            "is_archived": false,
            "is_general": true,
            "name_normalized": "general",
            "is_shared": false,
            "is_org_shared": false,
            "is_member": true,
            "is_private": false,
            "is_mpim": false,
            "members": [
                "U0G9QF9C6",
                "U0G9WFXNZ"
            ],
            "topic": {
                "value": "Talk about anything!",
                "creator": "U0G9QF9C6",
                "last_set": 1449709364
            },
            "purpose": {
                "value": "To talk about anything!",
                "creator": "U0G9QF9C6",
                "last_set": 1449709334
            },
            "previous_names": [],
            "num_members": 2
        }
    ],
    "response_metadata": {
        "next_cursor": "dGVhbTpDMUg5UkVTR0w="
    }
}
'''

CREATE_CHANNEL_RESPONSE = b'''\
{
    "ok": true,
    "channel": {
        "id": "C0DEL09A5",
        "name": "endeavor",
        "is_channel": true,
        "created": 1502833204,
        "creator": "U061F7AUR",
        "is_archived": false,
        "is_general": false,
        "name_normalized": "endeavor",
        "is_shared": false,
        "is_org_shared": false,
        "is_member": true,
        "is_private": false,
        "is_mpim": false,
        "last_read": "0000000000.000000",
        "latest": null,
        "unread_count": 0,
        "unread_count_display": 0,
        "members": [
            "U061F7AUR"
        ],
        "topic": {
            "value": "",
            "creator": "",
            "last_set": 0
        },
        "purpose": {
            "value": "",
            "creator": "",
            "last_set": 0
        },
        "previous_names": []
    }
}
'''

POST_MESSAGE_RESPONSE = b'''\
{
    "ok": true,
    "channel": "C1H9RESGL",
    "ts": "1503435956.000247",
    "message": {
        "text": "Here's a message for you",
        "username": "ecto1",
        "bot_id": "B19LU7CSY",
        "attachments": [
            {
                "text": "This is an attachment",
                "id": 1,
                "fallback": "This is an attachment's fallback"
            }
        ],
        "type": "message",
        "subtype": "bot_message",
        "ts": "1503435956.000247"
    }
}
'''

from telethon import TelegramClient, errors
import asyncio

# Replace these with your own values from my.telegram.org
api_id = 26866999
api_hash = "0078471b8da9dd7c2b4658f85eebead2"
session_name = "my_session"
bot_username = "@CV_messages_counter_bot"

# List of channel IDs (as integers)
channel_ids = [
    -1001906972731,
    -1001841647054,
    -1001921954000,
    -1001701922546,
    -1001926225725,
    -1001965054324,
    -1002199401387
]

async def main():
    async with TelegramClient('user_session', api_id, api_hash) as client:
        for channel_id in channel_ids:
            try:
                # Try to get the channel entity
                entity = await client.get_entity(channel_id)
                print(f"Channel ID: {channel_id}, Name: {entity.title}")

                # Send /activate command
                await client.send_message(entity, '/activate')
                print(f"Sent /activate to {entity.title}")

            except errors.UserNotParticipantError:
                print(f"Not a participant in {channel_id}, trying to join...")
                try:
                    await client(JoinChannelRequest(channel_id))
                    entity = await client.get_entity(channel_id)
                    print(f"Joined and got name: {entity.title}")
                    await client.send_message(entity, '/activate')
                    print(f"Sent /activate to {entity.title}")
                except Exception as e:
                    print(f"Failed to join or send to {channel_id}: {e}")

            except errors.rpcerrorlist.ChannelPrivateError:
                print(f"Channel {channel_id} is private or you are banned.")
            except errors.rpcerrorlist.PeerIdInvalidError:
                print(f"Channel {channel_id} is invalid or you haven't met it yet.")
            except Exception as e:
                print(f"Error with channel {channel_id}: {e}")

if __name__ == '__main__':
    asyncio.run(main())
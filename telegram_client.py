from telethon import TelegramClient, events
from telethon.tl.types import Dialog, User, Chat, Channel

# Получите эти значения с https://my.telegram.org
API_ID = 'your_api_id'
API_HASH = 'your_api_hash'

async def get_dialogs():
    # Создаем клиент
    client = TelegramClient('session_name', API_ID, API_HASH)
    await client.start()

    # Получаем все диалоги
    dialogs = await client.get_dialogs()
    
    # Форматируем результат
    result = []
    for dialog in dialogs:
        entity = dialog.entity
        
        dialog_info = {
            'id': entity.id,
            'name': '',
            'type': '',
            'unread_count': dialog.unread_count,
            'last_message': dialog.message.message if dialog.message else None,
            'last_message_date': dialog.message.date if dialog.message else None
        }
        
        if isinstance(entity, User):
            dialog_info['name'] = f"{entity.first_name} {entity.last_name if entity.last_name else ''}"
            dialog_info['type'] = 'user'
        elif isinstance(entity, Chat):
            dialog_info['name'] = entity.title
            dialog_info['type'] = 'chat'
        elif isinstance(entity, Channel):
            dialog_info['name'] = entity.title
            dialog_info['type'] = 'channel'
            
        result.append(dialog_info)
    
    await client.disconnect()
    return result

if __name__ == '__main__':
    import asyncio
    dialogs = asyncio.get_event_loop().run_until_complete(get_dialogs())
    for dialog in dialogs:
        print(f"Name: {dialog['name']}")
        print(f"Type: {dialog['type']}")
        print(f"Unread: {dialog['unread_count']}")
        print(f"Last message: {dialog['last_message']}")
        print("---") 
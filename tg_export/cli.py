import click
import asyncio
from pathlib import Path
import os
from typing import Optional
from datetime import datetime, timedelta
import json
import time
import random

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityBold, MessageEntityItalic, MessageEntityCode, MessageEntityPre, MessageEntityTextUrl
from telethon.utils import get_peer_id
from dotenv import load_dotenv

load_dotenv()

# Safety settings to avoid bans
BATCH_SIZE = 100  # Messages per request
MIN_DELAY = 1.0   # Minimum delay between batches (seconds)
MAX_DELAY = 3.0   # Maximum delay between batches


@click.group()
def cli():
    """Telegram Group-Chat Exporter"""
    pass


@cli.command()
def login():
    """Authenticate with Telegram"""
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    
    if not api_id or not api_hash:
        click.echo("Error: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in environment", err=True)
        raise click.Abort()
    
    api_id = int(api_id)
    session_file = Path(".session")
    
    async def auth():
        session = session_file.read_text() if session_file.exists() else ""
        client = TelegramClient(StringSession(session), api_id, api_hash)
        
        await client.start()
        
        # Save session
        session_file.write_text(client.session.save())
        click.echo("Successfully authenticated and saved session!")
        
        await client.disconnect()
    
    asyncio.run(auth())


def parse_chat_url(url: str):
    """Parse Telegram chat URL to get chat ID"""
    # Handle different URL formats:
    # https://t.me/c/123456789/12345 (private supergroup with message)
    # https://t.me/c/123456789 (private supergroup)
    # https://t.me/joinchat/XXXXX
    # https://t.me/username
    
    if "/c/" in url:
        # Private supergroup link
        parts = url.split("/c/")[-1].split("/")
        chat_id = int(parts[0])
        # Private supergroups need -100 prefix
        return -1000000000000 - chat_id
    else:
        # For public groups/channels, we'll resolve by username
        return url.split("/")[-1].split("?")[0]  # Remove any query params


def get_last_message_id(output_file: Path) -> Optional[int]:
    """Get the last message ID from existing output file"""
    if not output_file.exists():
        return None
    
    try:
        # Read last line
        with open(output_file, 'rb') as f:
            f.seek(0, 2)  # Go to end
            if f.tell() == 0:  # Empty file
                return None
            
            # Find last newline
            f.seek(-2, 2)
            while f.read(1) != b'\n':
                if f.tell() == 1:  # Beginning of file
                    f.seek(0)
                    break
                f.seek(-2, 1)
            
            last_line = f.readline().decode('utf-8').strip()
            if last_line:
                data = json.loads(last_line)
                return data.get('msg_id')
    except Exception:
        return None
    
    return None


def serialize_entities(entities):
    """Convert Telegram entities to serializable format"""
    if not entities:
        return []
    
    result = []
    for entity in entities:
        if isinstance(entity, MessageEntityBold):
            result.append({"type": "bold", "offset": entity.offset, "length": entity.length})
        elif isinstance(entity, MessageEntityItalic):
            result.append({"type": "italic", "offset": entity.offset, "length": entity.length})
        elif isinstance(entity, MessageEntityCode):
            result.append({"type": "code", "offset": entity.offset, "length": entity.length})
        elif isinstance(entity, MessageEntityPre):
            result.append({"type": "pre", "offset": entity.offset, "length": entity.length})
        elif isinstance(entity, MessageEntityTextUrl):
            result.append({"type": "text_url", "offset": entity.offset, "length": entity.length, "url": entity.url})
    
    return result


async def dump_messages(client: TelegramClient, chat, output_file: Path, min_id: Optional[int] = None, since: Optional[datetime] = None):
    """Dump messages from a chat to JSONL file"""
    count = 0
    mode = 'a' if min_id else 'w'
    batch_count = 0
    reached_time_limit = False
    
    with open(output_file, mode, encoding='utf-8') as f:
        # Set up iteration parameters
        iter_params = {}
        if min_id:
            iter_params["min_id"] = min_id
            iter_params["reverse"] = True
        
        # Note: iter_messages will fetch ALL messages unless we break
        async for message in client.iter_messages(chat, **iter_params):
            # Check if before since date - if so, we're done
            if since and message.date.replace(tzinfo=None) < since:
                reached_time_limit = True
                break
            
            # Determine media type
            media_type = None
            media_file_id = None
            
            if message.photo:
                media_type = "photo"
                media_file_id = str(message.photo.id)
            elif message.video:
                media_type = "video"
                media_file_id = str(message.video.id)
            elif message.document:
                media_type = "doc"
                media_file_id = str(message.document.id)
            
            # Build message data
            data = {
                "msg_id": message.id,
                "chat_id": get_peer_id(message.peer_id),
                "date": message.date.isoformat() + "Z",
                "sender_id": message.sender_id,
                "sender_username": getattr(message.sender, 'username', None) if message.sender else None,
                "reply_to": message.reply_to.reply_to_msg_id if message.reply_to else None,
                "text": message.text or "",
                "entities": serialize_entities(message.entities),
                "media_type": media_type,
                "media_file_id": media_file_id
            }
            
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
            count += 1
            
            if count % BATCH_SIZE == 0:
                batch_count += 1
                click.echo(f"Exported {count} messages...", err=True)
                
                # Add random delay between batches to avoid rate limits
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                await asyncio.sleep(delay)
        
        if reached_time_limit:
            click.echo(f"Reached time limit (messages before {since})", err=True)
    
    return count


@cli.command()
@click.option('--chat-url', required=True, help='Telegram chat URL')
@click.option('--out', required=True, type=click.Path(), help='Output JSONL file')
@click.option('--since', type=click.DateTime(formats=['%Y-%m-%d']), help='Only export messages since this date')
@click.option('--last', help='Only export messages from last N hours/days (e.g., "24h", "7d", "48h")')
def dump(chat_url: str, out: str, since: Optional[datetime], last: Optional[str]):
    """Dump all messages from a chat"""
    output_file = Path(out)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Parse --last parameter
    if last:
        if last.endswith('h'):
            hours = int(last[:-1])
            since = datetime.now() - timedelta(hours=hours)
        elif last.endswith('d'):
            days = int(last[:-1])
            since = datetime.now() - timedelta(days=days)
        else:
            click.echo("Error: --last should be in format like '24h' or '7d'", err=True)
            raise click.Abort()
        click.echo(f"Exporting messages from last {last} (since {since.strftime('%Y-%m-%d %H:%M')})", err=True)
    
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    
    if not api_id or not api_hash:
        click.echo("Error: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in environment", err=True)
        raise click.Abort()
    
    api_id = int(api_id)
    session_file = Path(".session")
    
    if not session_file.exists():
        click.echo("Error: Not authenticated. Run 'tg_export login' first", err=True)
        raise click.Abort()
    
    async def export():
        session = session_file.read_text()
        client = TelegramClient(StringSession(session), api_id, api_hash)
        
        await client.start()
        
        # Parse chat
        chat_identifier = parse_chat_url(chat_url)
        
        try:
            if isinstance(chat_identifier, str):
                chat = await client.get_entity(chat_identifier)
            else:
                chat = await client.get_entity(chat_identifier)
        except Exception as e:
            click.echo(f"Error: Could not access chat: {e}", err=True)
            await client.disconnect()
            raise click.Abort()
        
        # Check for incremental export
        last_msg_id = get_last_message_id(output_file)
        
        if last_msg_id:
            click.echo(f"Resuming from message ID {last_msg_id}", err=True)
        
        # Export messages
        try:
            count = await dump_messages(client, chat, output_file, min_id=last_msg_id, since=since)
            
            # Report file size
            file_size = output_file.stat().st_size
            file_size_mb = file_size / 1024 / 1024
            
            click.echo(f"\nExported {count} messages")
            click.echo(f"File size: {file_size_mb:.2f} MB")
            
        except FloodWaitError as e:
            click.echo(f"Rate limited. Waiting {e.seconds} seconds...", err=True)
            await asyncio.sleep(e.seconds)
            # Retry
            count = await dump_messages(client, chat, output_file, min_id=last_msg_id, since=since)
        
        await client.disconnect()
    
    asyncio.run(export())


@cli.command()
@click.option('--chat-url', required=True, help='Telegram chat URL')
@click.option('--hours', type=int, default=1, help='Export last N hours (default: 1)')
@click.option('--clean/--raw', default=True, help='Output clean text format (default: True)')
def quick(chat_url: str, hours: int, clean: bool):
    """Quick export for last N hours - perfect for LLM analysis"""
    from .clean_export import convert_to_clean_format
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("exports/quick")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    temp_file = output_dir / f"quick_{hours}h_{timestamp}.jsonl"
    final_file = output_dir / f"quick_{hours}h_{timestamp}.txt"
    
    # Export with time limit
    since = datetime.now() - timedelta(hours=hours)
    
    # Run the export
    ctx = click.Context(dump)
    ctx.invoke(dump, chat_url=chat_url, out=str(temp_file), since=since, last=None)
    
    if clean and temp_file.exists():
        # Clean the export
        click.echo("\nCleaning export for LLM use...", err=True)
        stats = convert_to_clean_format(temp_file, final_file, filter_bots=True)
        
        click.echo(f"\n✅ Quick export complete!")
        click.echo(f"📊 Stats:")
        click.echo(f"   Kept: {stats['kept']} messages") 
        click.echo(f"   Filtered: {stats['filtered_bots']} bots, {stats['filtered_media_only']} media-only")
        click.echo(f"\n📁 Clean file: {final_file}")
        click.echo(f"\n💡 Copy to clipboard:")
        click.echo(f"   Mac: pbcopy < {final_file}")
        click.echo(f"   Linux: xclip -selection clipboard < {final_file}")
        
        # Remove temp file
        temp_file.unlink()
    else:
        click.echo(f"\n📁 Export saved to: {temp_file}")


@cli.command()
@click.option('--chat-url', required=True, help='Telegram chat URL')
@click.option('--out', required=True, type=click.Path(), help='Output JSONL file')
@click.option('--every', required=True, help='Sync interval (e.g., "5m", "1h") - minimum 5m recommended')
def sync(chat_url: str, out: str, every: str):
    """Continuously sync new messages"""
    # Parse interval
    if every.endswith('m'):
        interval = int(every[:-1]) * 60
    elif every.endswith('h'):
        interval = int(every[:-1]) * 3600
    else:
        interval = int(every)
    
    # Enforce minimum interval to avoid aggressive polling
    if interval < 300:  # 5 minutes
        click.echo("Warning: Using minimum interval of 5 minutes to avoid rate limits", err=True)
        interval = 300
    
    click.echo(f"Starting sync every {interval} seconds", err=True)
    
    while True:
        try:
            # Run dump command
            ctx = click.Context(dump)
            ctx.invoke(dump, chat_url=chat_url, out=out, since=None)
        except Exception as e:
            click.echo(f"Sync error: {e}", err=True)
        
        # Add some jitter to avoid predictable patterns
        jitter = random.uniform(0, 30)  # 0-30 seconds random delay
        time.sleep(interval + jitter)


if __name__ == '__main__':
    cli()
import json
import re
from pathlib import Path
import click
from datetime import datetime


def clean_text(text: str) -> str:
    """Clean text by removing URLs and cleaning up formatting"""
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r't\.me/\S+', '', text)
    
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Remove empty brackets
    text = re.sub(r'\[\s*\]', '', text)
    text = re.sub(r'\(\s*\)', '', text)
    
    return text.strip()


def is_bot_message(username: str, text: str) -> bool:
    """Detect common bot messages"""
    bot_indicators = ['Bot', 'bot', '_bot']
    spam_keywords = ['gained', 'UPDATE', 'FLEX', 'scanned it', '🚀', 'Market Cap']
    
    # Check if it's a bot username
    if username and any(indicator in username for indicator in bot_indicators):
        return True
    
    # Check for spam keywords
    if any(keyword in text for keyword in spam_keywords):
        return True
    
    return False


def convert_to_clean_format(input_file: Path, output_file: Path, filter_bots: bool = True):
    """Convert JSONL to a cleaner format for LLMs"""
    
    messages = []
    stats = {
        'total': 0,
        'kept': 0,
        'filtered_bots': 0,
        'filtered_media_only': 0
    }
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            stats['total'] += 1
            data = json.loads(line)
            
            # Skip bot messages if filter is on
            if filter_bots and is_bot_message(data.get('sender_username', ''), data.get('text', '')):
                stats['filtered_bots'] += 1
                continue
            
            # Skip media-only messages with no text
            if not data.get('text', '').strip() and data.get('media_type'):
                stats['filtered_media_only'] += 1
                continue
            
            # Clean the text
            clean_msg_text = clean_text(data.get('text', ''))
            
            # Skip empty messages after cleaning
            if not clean_msg_text:
                continue
            
            # Format timestamp
            date_str = data['date'].rstrip('Z')
            if date_str.endswith('+00:00+00:00'):
                date_str = date_str[:-6]  # Remove duplicate timezone
            timestamp = datetime.fromisoformat(date_str)
            readable_time = timestamp.strftime('%Y-%m-%d %H:%M')
            
            # Create simplified message
            clean_msg = {
                'time': readable_time,
                'user': data.get('sender_username', f"user_{data.get('sender_id', 'unknown')}"),
                'text': clean_msg_text
            }
            
            # Add reply context if exists
            if data.get('reply_to'):
                clean_msg['replying_to_msg_id'] = data['reply_to']
            
            messages.append(clean_msg)
            stats['kept'] += 1
    
    # Write clean format
    with open(output_file, 'w', encoding='utf-8') as f:
        # Option 1: Simple chat format (most LLM-friendly)
        if output_file.suffix == '.txt':
            for msg in messages:
                reply_indicator = f" (replying to #{msg.get('replying_to_msg_id', '')})" if 'replying_to_msg_id' in msg else ""
                f.write(f"[{msg['time']}] {msg['user']}{reply_indicator}: {msg['text']}\n")
        
        # Option 2: Clean JSON format
        else:
            for msg in messages:
                f.write(json.dumps(msg, ensure_ascii=False) + '\n')
    
    return stats


@click.command()
@click.option('--input', '-i', required=True, help='Input JSONL file')
@click.option('--output', '-o', help='Output file (defaults to input_clean.txt)')
@click.option('--format', type=click.Choice(['txt', 'jsonl']), default='txt', help='Output format')
@click.option('--keep-bots/--no-bots', default=False, help='Keep bot messages (default: filter out)')
def clean(input: str, output: str, format: str, keep_bots: bool):
    """Clean exported Telegram data for LLM processing"""
    
    input_file = Path(input)
    if not input_file.exists():
        click.echo(f"Error: Input file {input} not found", err=True)
        return
    
    if not output:
        output = input_file.stem + f"_clean.{format}"
    
    output_file = Path(output)
    
    click.echo(f"Cleaning {input_file.name}...")
    
    stats = convert_to_clean_format(input_file, output_file, filter_bots=not keep_bots)
    
    click.echo(f"\n✅ Cleaning complete!")
    click.echo(f"📊 Stats:")
    click.echo(f"   Total messages: {stats['total']}")
    click.echo(f"   Kept: {stats['kept']}")
    click.echo(f"   Filtered bots: {stats['filtered_bots']}")
    click.echo(f"   Filtered media-only: {stats['filtered_media_only']}")
    click.echo(f"\n📁 Clean file saved to: {output_file}")
    
    # Show sample
    click.echo(f"\n📝 Sample of cleaned output:")
    with open(output_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 5:
                break
            click.echo(f"   {line.strip()}")


if __name__ == '__main__':
    clean()
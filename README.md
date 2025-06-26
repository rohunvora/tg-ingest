# Telegram Personal Chat Analyzer

**⚠️ IMPORTANT: This tool is for PERSONAL USE ONLY to export YOUR OWN chat data from groups YOU ARE A MEMBER OF. This is NOT a scraping tool.**

A secure, privacy-focused tool for exporting your own Telegram group messages for personal analysis with AI assistants like Claude or ChatGPT.

## 🔒 Security & Ethics First

This tool:
- ✅ Only exports from groups YOU are already a member of
- ✅ Uses YOUR personal Telegram account (not a bot)
- ✅ Respects rate limits to avoid account issues
- ✅ Stores data locally on YOUR device only
- ❌ Cannot access groups you're not in
- ❌ Does NOT scrape or harvest data
- ❌ Does NOT share data with any third parties

**By using this tool, you acknowledge that you will only export data from groups where you have permission to do so.**

## Use Cases

- 📊 Analyze your team's Slack-to-Telegram migration
- 🧠 Get AI help understanding technical discussions
- 📝 Create summaries of important group decisions
- 🔍 Search through your own message history more effectively

## Prerequisites

- Python 3.10+
- Your own Telegram API credentials (free from Telegram)
- Membership in the groups you want to analyze

## Setup

1. **Get YOUR Telegram API credentials** (5 minutes, free):
   - Go to https://my.telegram.org/apps
   - Log in with YOUR phone number
   - Create an application (it's just for personal use)
   - Save your `api_id` and `api_hash`

2. **Install** (one-time setup):
```bash
git clone https://github.com/yourusername/tg-ingest.git
cd tg-ingest
./setup.sh  # or manually: python3 -m venv venv && source venv/bin/activate && pip install poetry && poetry install
```

3. **Configure** (create `.env` file):
```bash
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
```

## Usage

### 1. Authenticate (one-time)

```bash
./run.sh login
```

This logs into YOUR Telegram account. You'll receive a code in your Telegram app.

### 2. Quick Export (NEW! 🚀)

**Option A: Web UI** (Easiest)
```bash
./run.sh web
```
Opens a simple local web interface to:
- Export last 1h, 6h, 24h or custom time
- Auto-clean for AI analysis
- Download history

**Option B: Command Line** (Fastest)
```bash
# One-click export last hour
./quick1h.sh https://t.me/c/123456789/12345

# Or specify hours
./run.sh quick

# Filter by username
./run.sh quick --chat-url "https://t.me/c/123456789/12345" --hours 6 --username YOUR_USERNAME
```

**Option C: Direct to AI** (Copy to clipboard)
```bash
# Mac - exports and copies to clipboard
./quick1h.sh https://t.me/c/123456789/12345

# Now just paste into Claude/ChatGPT!
```

### 3. Full Export (for archival)

```bash
# Export all messages
poetry run tg_export dump --chat-url "https://t.me/c/123456789" --out my_archive.jsonl

# Export only your messages
poetry run tg_export dump --chat-url "https://t.me/c/123456789" --out my_messages.jsonl --username YOUR_USERNAME

# Export last 24 hours from specific user
poetry run tg_export dump --chat-url "https://t.me/c/123456789" --out filtered.jsonl --last 24h --username THEIR_USERNAME
```

## Output Format

Messages are saved in clean, AI-ready format:
```
[2025-06-26 14:32] username: message text
[2025-06-26 14:33] another_user (replying to #123): reply text
```

Bot messages and spam are automatically filtered out.

## 🛡️ Privacy & Security Features

1. **Local Processing Only**: All data stays on your machine
2. **No External APIs**: Direct connection to Telegram only
3. **Session Security**: Encrypted session stored locally
4. **Rate Limiting**: Automatic delays prevent account flags
5. **Minimal Permissions**: Only reads messages, cannot send

## ⚖️ Legal & Ethical Use

This tool is designed for:
- Personal productivity and analysis
- Backing up your own conversations
- Getting AI assistance with group discussions you're part of

**DO NOT use this tool to:**
- Export private conversations without consent
- Scrape public channels you're not a member of
- Violate Telegram's Terms of Service
- Share exported data without permission

## Troubleshooting

**"Not authenticated"**: Run `./run.sh login` first

**"Chat not found"**: Make sure you're a member and using the correct URL format

**"Rate limited"**: Wait a few minutes - the tool respects Telegram's limits

**Port already in use**: The web UI will try ports 8080, 5001, 5000, 8000

## Technical Details

- Built with Python and Telethon (official Telegram client library)
- Respects Telegram rate limits with smart delays
- Filters bot spam and media-only messages
- Incremental export support (resume from last message)

## Contributing

This is a personal tool shared for educational purposes. Feel free to fork and modify for your own use, but please:
- Respect Telegram's ToS
- Use ethically and responsibly
- Don't use for mass data collection

## License

MIT License - Use at your own risk and responsibility

## Disclaimer

This tool is provided as-is for personal use. The authors are not responsible for any misuse or violations of Telegram's Terms of Service. Always respect privacy and obtain consent before analyzing shared conversations.

---

**Remember**: With great power comes great responsibility. Use this tool ethically! 🙏
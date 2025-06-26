# Simple Guide for Non-Technical Users

## What This Does
This tool exports your Telegram group messages to a file that you can analyze with AI tools like ChatGPT or Claude.

## Step 1: Get Your Telegram API Credentials (5 minutes)

1. Go to https://my.telegram.org
2. Log in with your phone number (you'll get a code in Telegram)
3. Click "API development tools"
4. Fill in:
   - App title: "My Chat Exporter" (or anything)
   - Short name: "mychatexporter" (or anything)
   - Platform: "Other"
5. Click "Create application"
6. You'll see two important things - **SAVE THESE**:
   - `api_id`: (a number like 12345678)
   - `api_hash`: (a long code like a1b2c3d4e5f6...)

## Step 2: One-Time Setup (3 minutes)

1. Open Terminal (Mac) or Command Prompt (Windows)
2. Navigate to this folder and run:
   ```
   ./setup.sh
   ```
3. When asked, paste your api_id and api_hash

## Step 3: Login to Telegram (2 minutes)

Run:
```
./run.sh login
```

You'll get a code in your Telegram app - enter it when asked.

## Step 4: Export Your Chat (5-30 minutes depending on size)

Run:
```
./run.sh export
```

When asked for the chat URL:
- Open your private group in Telegram
- Click the group name at the top
- Find "Invite Link" or "Add Members"
- Copy the link (looks like `https://t.me/c/1234567890`)
- Paste it in the terminal

## What You Get

A file in the `exports` folder that contains all messages in JSON format. You can:
- Upload it to Claude or ChatGPT for analysis
- Ask questions like "What are the main topics discussed?"
- Get summaries, find patterns, extract insights

## Important Notes

- This only works for groups you're a member of
- It exports text only (no images/videos)
- Large groups (100k+ messages) may take 20-30 minutes
- Use responsibly - this is for personal analysis only

## Troubleshooting

**"Python not found"**: Install Python from https://python.org (get version 3.10 or newer)

**"Chat not found"**: Make sure you're using the correct URL format and you're a member of the group

**"Rate limited"**: Wait a few minutes and try again - Telegram has limits to prevent spam
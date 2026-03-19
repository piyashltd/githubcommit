import os
import telebot
from github import Github, Auth # 1. Auth ইম্পোর্ট করা হয়েছে
import json
import re
from datetime import datetime

# ---------------- CONFIGURATION (From Railway Environment) ----------------
# রেলওয়ে ভেরিয়েবল থেকে টোকেন নেওয়া হবে
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
REPO_NAME = os.environ.get('REPO_NAME')  # Example: 'username/repo-name'
FILE_PATH = 'src/data/dummyData.js'      # আপনার ফাইলের পাথ

# চেক করা হচ্ছে ভেরিয়েবল সেট করা আছে কিনা
if not BOT_TOKEN or not GITHUB_TOKEN or not REPO_NAME:
    print("❌ Error: Environment variables are missing!")
    exit(1)

# ---------------- INITIALIZATION ----------------
bot = telebot.TeleBot(BOT_TOKEN)

# 2. এখানে Deprecation Warning ফিক্স করা হয়েছে
auth = Auth.Token(GITHUB_TOKEN)
g = Github(auth=auth)

# ---------------- DATE FORMATTER HELPER ----------------
def standardize_date(date_str):
    """বিভিন্ন ফরম্যাটের ডেটকে '13 Jan 2025' ফরম্যাটে সাজানোর ফাংশন"""
    if not date_str:
        return date_str
        
    # সম্ভাব্য সব ডেট ফরম্যাটের লিস্ট
    formats = [
        "%b %d, %Y",   # Jan 13, 2025
        "%B %d, %Y",   # January 13, 2025
        "%Y-%m-%d",    # 2025-01-13
        "%d %b %Y",    # 13 Jan 2025 (Already correct format)
        "%d %B %Y",    # 13 January 2025
        "%m/%d/%Y",    # 01/13/2025
        "%d/%m/%Y",    # 13/01/2025
        "%b %d %Y"     # Jan 13 2025
    ]
    
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str.strip(), fmt)
            return parsed_date.strftime("%d %b %Y")
        except ValueError:
            continue
            
    return date_str

# ---------------- GITHUB PUSH FUNCTION ----------------
def push_to_github(new_episodes_list):
    try:
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        
        # বর্তমান কন্টেন্ট পড়া
        original_content = contents.decoded_content.decode("utf-8")
        
        # --- আগে থেকে থাকা সব ডেট আপডেট করার লজিক (Regex) ---
        def date_replacer(match):
            prefix = match.group(1) # 'date: ' বা '"date": ' অংশটুকু
            old_date = match.group(2) # ভেতরের ডেট (যেমন: Jan 13, 2025)
            new_date = standardize_date(old_date) # ডেট ফরম্যাট ঠিক করা
            return f'{prefix}"{new_date}"'
            
        # Regex প্যাটার্ন যা date: "..." অথবা "date": "..." ফরম্যাট খুঁজবে
        date_pattern = re.compile(r'((?:"date"|date)\s*:\s*)["\'](.*?)["\']')
        
        # পুরো ফাইলের আগের সব ডেট আপডেট করা হলো
        fixed_original_content = date_pattern.sub(date_replacer, original_content)
        # --------------------------------------------------------

        # 'episodes' অ্যারে খুঁজে বের করা (fixed_original_content থেকে)
        start_marker = "export const episodes = ["
        start_index = fixed_original_content.find(start_marker)
        
        if start_index == -1:
            return "❌ Error: 'episodes' array not found in dummyData.js!"

        # ক্লোজিং ব্র্যাকেট খুঁজে বের করা
        end_index = fixed_original_content.find("];", start_index)
        
        if end_index == -1:
            return "❌ Error: Closing bracket for episodes array not found!"

        # নতুন ডাটা ফরম্যাট করা (JSON String)
        formatted_json_str = json.dumps(new_episodes_list, indent=2)
        
        # বাইরের [ ] ব্র্যাকেট রিমুভ করা
        inner_content = formatted_json_str.strip()[1:-1] 
        
        # ডাটা ইনজেক্ট করা (আগের ঠিক করা ডাটার পরে কমা দিয়ে নতুন ডাটা বসানো)
        updated_content = (
            fixed_original_content[:end_index].rstrip() + 
            ",\n" + 
            inner_content + 
            "\n" + 
            fixed_original_content[end_index:]
        )
        
        # গিটহাবে পুশ করা
        repo.update_file(
            contents.path, 
            f"Added {len(new_episodes_list)} episodes & fixed old dates via Bot", 
            updated_content, 
            contents.sha
        )
        
        return f"✅ Success! Added {len(new_episodes_list)} new episodes AND updated all previous dates to '13 Jan 2025' format."

    except Exception as e:
        return f"❌ GitHub Error: {str(e)}"

# ---------------- BOT COMMANDS ----------------

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hi! Send me a **JSON List** [...] of episodes to upload.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()
    
    # JSON ভ্যালিডেশন
    if not text.startswith('['):
        bot.reply_to(message, "⚠️ Please send a JSON list starting with `[`")
        return

    try:
        data = json.loads(text)
        
        # নতুন পাঠানো ড্যাটার ডেটগুলোও গিটহাবে পুশ করার আগে ঠিক করে নেওয়া হচ্ছে
        for episode in data:
            if 'date' in episode:
                episode['date'] = standardize_date(episode['date'])
        
        bot.reply_to(message, "⏳ Uploading to GitHub... Fixing old dates and adding new ones. Please wait.")
        result = push_to_github(data)
        
        bot.reply_to(message, result)

    except json.JSONDecodeError:
        bot.reply_to(message, "❌ Invalid JSON Format!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ---------------- RUN BOT ----------------
print("🤖 Bot is running on Railway...")
bot.infinity_polling()

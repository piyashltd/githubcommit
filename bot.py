import os
import telebot
from github import Github
import json

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
g = Github(GITHUB_TOKEN)

def push_to_github(new_episodes_list):
    try:
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        
        # বর্তমান কন্টেন্ট পড়া
        original_content = contents.decoded_content.decode("utf-8")
        
        # 'episodes' অ্যারে খুঁজে বের করা
        start_marker = "export const episodes = ["
        start_index = original_content.find(start_marker)
        
        if start_index == -1:
            return "❌ Error: 'episodes' array not found in dummyData.js!"

        # ক্লোজিং ব্র্যাকেট খুঁজে বের করা
        end_index = original_content.find("];", start_index)
        
        if end_index == -1:
            return "❌ Error: Closing bracket for episodes array not found!"

        # নতুন ডাটা ফরম্যাট করা (JSON String)
        formatted_json_str = json.dumps(new_episodes_list, indent=2)
        
        # বাইরের [ ] ব্র্যাকেট রিমুভ করা
        inner_content = formatted_json_str.strip()[1:-1] 
        
        # ডাটা ইনজেক্ট করা (আগের ডাটার পরে কমা দিয়ে)
        # লজিক: ...আগের ডাটা, \n নতুন ডাটা \n ];
        
        # আমরা end_index এর ঠিক আগে বসাচ্ছি
        # আগের লাইনে কমা আছে কিনা সেটা সেফটির জন্য আমরা নতুন ডাটার শুরুতেই একটা কমা দিচ্ছি
        updated_content = (
            original_content[:end_index].rstrip() + 
            ",\n" + 
            inner_content + 
            "\n" + 
            original_content[end_index:]
        )
        
        # গিটহাবে পুশ করা
        repo.update_file(
            contents.path, 
            f"Added {len(new_episodes_list)} new episodes via Bot", 
            updated_content, 
            contents.sha
        )
        
        return f"✅ Success! {len(new_episodes_list)} episodes pushed to GitHub."

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
        
        bot.reply_to(message, "⏳ Uploading to GitHub... Please wait.")
        result = push_to_github(data)
        
        bot.reply_to(message, result)

    except json.JSONDecodeError:
        bot.reply_to(message, "❌ Invalid JSON Format!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ---------------- RUN BOT ----------------
print("🤖 Bot is running on Railway...")
bot.infinity_polling()

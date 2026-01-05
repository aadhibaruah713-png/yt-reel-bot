import os, subprocess, math, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

TOKEN = '8257953823:AAHj1hkdHv9zY7eUwCrj6fvymSq2-vzIcic'

# ভিডিওর মোট দৈর্ঘ্য বের করার ফাংশন
def get_duration(file):
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file}'
    duration = subprocess.check_output(cmd, shell=True)
    return float(duration)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ বট এখন একদম ফ্রেশ! নতুন লিঙ্ক দিন, আমি সেটিই প্রসেস করবো।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    chat_id = update.message.chat_id
    
    if "youtube.com" in url or "youtu.be" in url:
        # আগের কোনো ফাইল থাকলে তা ডিলিট করা (যাতে নতুন ভিডিও কাজ করে)
        input_file = f"raw_{chat_id}.mp4"
        if os.path.exists(input_file):
            os.remove(input_file)
            
        await update.message.reply_text("⏳ নতুন ভিডিওটি চেক করছি... দয়া করে অপেক্ষা করুন।")
        
        try:
            # নতুন ভিডিও ডাউনলোড
            subprocess.run(['yt-dlp', '-f', 'bestvideo[height<=720]+bestaudio/best', '--merge-output-format', 'mp4', '-o', input_file, url], check=True)
            
            duration = get_duration(input_file)
            total_parts = math.floor(duration / 58)
            
            # ডাটা সেভ করা
            context.user_data['url'] = url
            context.user_data['file'] = input_file
            context.user_data['total_parts'] = total_parts

            # বাটন তৈরি (প্রতি ৪টি বাটন এক লাইনে)
            keyboard = []
            row = []
            for i in range(1, min(total_parts + 1, 21)):
                row.append(InlineKeyboardButton(f"Part {i}", callback_data=f"p_{i}"))
                if len(row) == 4:
                    keyboard.append(row)
                    row = []
            if row: keyboard.append(row)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(f"🎬 ভিডিওটি সফলভাবে পাওয়া গেছে!\nমোট রিলে ভাগ করা যাবে: {total_parts} টি।\nকোন পার্টটি রিল বানাতে চান?", reply_markup=reply_markup)
            
        except Exception as e:
            await update.message.reply_text("❌ ভিডিওটি ডাউনলোড করা যাচ্ছে না। অন্য লিঙ্ক ট্রাই করুন।")
    else:
        await update.message.reply_text("❌ এটি সঠিক ইউটিউব লিঙ্ক নয়।")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.message.chat_id
    input_file = f"raw_{chat_id}.mp4" # সব সময় কারেন্ট ফাইলের নাম
    
    # নিশ্চিত করা যে ফাইলটি আছে কি না
    if not os.path.exists(input_file):
        await query.message.reply_text("❌ ভিডিও ফাইলটি খুঁজে পাওয়া যাচ্ছে না। আবার লিঙ্ক দিন।")
        return

    if data.startswith('p_'):
        part_num = int(data.split('_')[1])
        start_time = (part_num - 1) * 58
        output_file = f"reel_{chat_id}_{part_num}.mp4"

        await query.edit_message_text(f"⚙️ পার্ট {part_num} এডিটিং শুরু হয়েছে...\n(Center Crop + Audio Sync Applied)")

        # পারফেক্ট ফিল্টার (Crop + Audio Fix + Anti-Copyright)
        cmd = (
            f'ffmpeg -ss {start_time} -t 58 -i {input_file} '
            f'-vf "crop=ih*9/16:ih,scale=720:1280,hflip,eq=brightness=0.07:contrast=1.2" '
            f'-af "aresample=44100,asetrate=44100*1.04,atempo=1.0/1.04" '
            f'-c:v libx264 -preset superfast -aspect 9:16 -y {output_file}'
        )
        
        try:
            subprocess.run(cmd, shell=True, check=True)
            # ভিডিও সেন্ড করা
            await query.message.reply_video(
                video=open(output_file, 'rb'), 
                caption=f"✅ Reel Part {part_num} Ready!\n\n#copyright_free #shorts",
                width=720, height=1280
            )
            # রেন্ডার করা ফাইল ডিলিট (স্টোরেজ বাঁচানোর জন্য)
            os.remove(output_file)
        except Exception as e:
            await query.message.reply_text(f"❌ এরর: {str(e)}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button))
    print("Bot is running perfectly...")
    app.run_polling()

if __name__ == '__main__':
    main()

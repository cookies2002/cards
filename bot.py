# Magical Card Game Bot - Updated with Admin Check, /profile, /hp, Clean UI
# Features: MongoDB storage, cooldowns, spam prevention, battle system, inline buttons

import os
import random
from datetime import datetime, timedelta
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# === CONFIG ===
API_ID = 24977986
API_HASH = "abc6095228862c7502397c928bd7999e"
BOT_TOKEN = "8382535043:AAFRZsmxNqzk0I6QXYF6Qb2SQPjUUbBO9Lo"
MONGO_URI = "mongodb+srv://xarwin2:xarwin2002@cluster0.qmetx2m.mongodb.net/?retryWrites=true&w=majority"

# === INIT ===
client = Client("card_game_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = MongoClient(MONGO_URI).card_game
users = db.users

# === CONSTANTS ===
DAILY_REWARD = 5
WIN_REWARD = 10
MAX_HP = 100
CARD_POOL = [
    "🔥 Fire Blast", "❄️ Ice Shield", "⚡ Thunder Blade", "🌪 Wind Fury", "💀 Death Ray",
    "🧊 Freeze", "🌈 Rainbow Slash", "🌋 Lava Burst", "💨 Speed Strike", "🌕 Moonlight Wave",
    "🌑 Shadow Slash", "🌟 Starfire Beam", "🎯 Precision Hit", "🧠 Mind Control", "👁 Psychic Gaze",
    "🐉 Dragon Flame", "🐍 Venom Fang", "🦂 Scorpion Sting", "🦄 Mystic Horn", "🔮 Arcane Shock",
    "🌊 Tsunami Wave", "🍃 Nature’s Grasp", "🎆 Fireworks Barrage", "🌀 Spiral Whirl",
    "⚔ Blade Barrage"
]

# === HELPERS ===
def get_user(user_id):
    user = users.find_one({"_id": user_id})
    if not user:
        user = {
            "_id": user_id,
            "coins": 0,
            "cards": [],
            "last_draw": None,
            "last_daily": None,
            "hp": MAX_HP,
            "profile": {"battles_won": 0, "battles_played": 0}
        }
        users.insert_one(user)
    return user

def update_user(user_id, data):
    users.update_one({"_id": user_id}, {"$set": data})

def add_card(user_id, card):
    users.update_one({"_id": user_id}, {"$push": {"cards": card}})

def reward_coins(user_id, amount):
    users.update_one({"_id": user_id}, {"$inc": {"coins": amount}})

def update_battle_stats(user_id, win=False):
    field = {"profile.battles_played": 1}
    if win:
        field["profile.battles_won"] = 1
    users.update_one({"_id": user_id}, {"$inc": field})

# === COMMANDS ===

@client.on_message(filters.command("start"))
async def start(_, message: Message):
    get_user(message.from_user.id)
    await message.reply("\ud83d\udc4b Welcome to the Magical Card Game Bot! Use /join to enter the battle arena.")

@client.on_message(filters.command("join"))
async def join(_, message: Message):
    get_user(message.from_user.id)
    await message.reply("\u2705 You have joined the magical arena! Use /draw to get your first card.")

@client.on_message(filters.command("draw"))
async def draw(_, message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    now = datetime.utcnow()
    if user.get("last_draw") and now - user["last_draw"] < timedelta(days=1):
        return await message.reply("\u23f3 You can only draw one card per day. Come back tomorrow!")

    card = random.choice(CARD_POOL)
    add_card(user_id, card)
    update_user(user_id, {"last_draw": now})
    await message.reply(f"\ud83c\udfb4 You drew: {card}! Use /inventory to view your cards.")

@client.on_message(filters.command("daily"))
async def daily(_, message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    now = datetime.utcnow()
    if user.get("last_daily") and now - user["last_daily"] < timedelta(days=1):
        return await message.reply("\u23f3 You already claimed your daily reward today.")

    reward_coins(user_id, DAILY_REWARD)
    update_user(user_id, {"last_daily": now})
    await message.reply(f"\ud83d\udcb0 Daily reward claimed! +{DAILY_REWARD} coins. Use /coins to check balance.")

@client.on_message(filters.command("coins"))
async def coins(_, message: Message):
    user = get_user(message.from_user.id)
    await message.reply(f"\ud83e\ude99 Your current balance: {user['coins']} coins.\n\ud83c\udfc6 Win battles to earn +{WIN_REWARD} coins!")

@client.on_message(filters.command("hp"))
async def hp(_, message: Message):
    user = get_user(message.from_user.id)
    await message.reply(f"\u2764\ufe0f Your current HP: {user['hp']} / {MAX_HP}")

@client.on_message(filters.command("profile"))
async def profile(_, message: Message):
    user = get_user(message.from_user.id)
    profile = user["profile"]
    await message.reply(
        f"\ud83d\udcc8 Profile:\n\n\ud83e\ude99 Coins: {user['coins']}\n\u2764\ufe0f HP: {user['hp']} / {MAX_HP}\n\ud83c\udf1f Battles Won: {profile['battles_won']}\n\u2694 Battles Played: {profile['battles_played']}\n\ud83c\udfaf Cards Owned: {len(user['cards'])}"
    )

@client.on_message(filters.command("use"))
async def use(_, message: Message):
    user_id = message.from_user.id
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return await message.reply("\u26a0\ufe0f Reply to a user's message to attack them.")

    target_id = message.reply_to_message.from_user.id
    if user_id == target_id:
        return await message.reply("\ud83d\ude45 You can't attack yourself!")

    user = get_user(user_id)
    target = get_user(target_id)
    if not user["cards"]:
        return await message.reply("\ud83d\udeab You have no cards to use. Draw one with /draw.")

    card = random.choice(user["cards"])
    users.update_one({"_id": user_id}, {"$pull": {"cards": card}})
    reward_coins(user_id, WIN_REWARD)
    update_battle_stats(user_id, win=True)
    update_battle_stats(target_id)
    await message.reply(
        f"\u2694\ufe0f {message.from_user.first_name} used {card} on {message.reply_to_message.from_user.first_name} and won the duel!\n\ud83c\udfc5 +{WIN_REWARD} coins! \ud83c\udf89")

@client.on_message(filters.command("startgame"))
async def startgame(_, message: Message):
    chat = await client.get_chat_member(message.chat.id, message.from_user.id)
    if not chat.status in ("administrator", "creator"):
        return await message.reply("\u274c Only group admins can start the game.")
    await message.reply("\u2728 Game started! Players can /join and begin dueling!")

@client.on_message(filters.command("end"))
async def end(_, message: Message):
    await message.reply("\ud83d\uded1 Game ended. Use /join to play again.")

@client.on_message(filters.command("skip"))
async def skip(_, message: Message):
    await message.reply("\u23e9 Turn skipped. Next player!")

@client.on_message(filters.command("shop"))
async def shop(_, message: Message):
    buttons = [
        [InlineKeyboardButton("\ud83d\udee1 Buy Shield (HP+20) - 3 Coins", callback_data="buy_shield")],
        [InlineKeyboardButton("\ud83d\udcdc Buy Scroll (Power Card) - 5 Coins", callback_data="buy_scroll")],
        [InlineKeyboardButton("\ud83d\udc09 Buy Dragon Fury - 7 Coins", callback_data="buy_dragon")],
        [InlineKeyboardButton("\ud83d\udd2e Buy Arcane Boost (HP+50) - 10 Coins", callback_data="buy_hp50")]
    ]
    await message.reply("\ud83c\udfcd Shop: Use your coins to buy powerful cards or boost your HP:", reply_markup=InlineKeyboardMarkup(buttons))

@client.on_callback_query()
async def handle_shop(client, callback):
    user_id = callback.from_user.id
    user = get_user(user_id)
    data = callback.data
    if data == "buy_shield" and user["coins"] >= 3:
        reward_coins(user_id, -3)
        update_user(user_id, {"hp": min(user["hp"] + 20, MAX_HP)})
        await callback.message.delete()
        await callback.answer("+20 HP gained!")
    elif data == "buy_scroll" and user["coins"] >= 5:
        reward_coins(user_id, -5)
        add_card(user_id, "\ud83d\udcdc Mystic Scroll")
        await callback.message.delete()
        await callback.answer("Scroll added to inventory!")
    elif data == "buy_dragon" and user["coins"] >= 7:
        reward_coins(user_id, -7)
        add_card(user_id, "\ud83d\udc09 Dragon Fury")
        await callback.message.delete()
        await callback.answer("Dragon Fury acquired!")
    elif data == "buy_hp50" and user["coins"] >= 10:
        reward_coins(user_id, -10)
        update_user(user_id, {"hp": min(user["hp"] + 50, MAX_HP)})
        await callback.message.delete()
        await callback.answer("+50 HP boost applied!")
    else:
        await callback.answer("Not enough coins!", show_alert=True)

@client.on_message(filters.command("leaderboard"))
async def leaderboard(_, message: Message):
    top = users.find().sort("profile.battles_won", -1).limit(10)
    text = "\ud83c\udfc6 Top Duelists:\n"
    for i, user in enumerate(top, 1):
        text += f"{i}. {user['_id']} - {user['profile']['battles_won']} Wins\n"
    await message.reply(text)

@client.on_inline_query()
async def inline_query_handler(_, inline_query):
    user = get_user(inline_query.from_user.id)
    cards = user.get("cards", [])
    results = []
    for i, card in enumerate(cards):
        results.append({
            "type": "article",
            "id": str(i),
            "title": card,
            "input_message_content": {"message_text": f"\ud83c\udfb4 I have: {card}"}
        })
    await inline_query.answer(results[:10], cache_time=1)

@client.on_message(filters.text & ~filters.command(["start", "join", "draw", "use", "inventory", "coins", "daily", "shop", "skip", "end", "leaderboard", "profile", "hp", "startgame"]))
async def unknown(_, message: Message):
    pass

client.run()

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageOps
import aiohttp
import io
import os
from collections import defaultdict
import time

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== SETTINGS =====
AUTO_ROLE_NAME = "HCD Member"
SPAM_LIMIT = 5
SPAM_TIME = 5
# ====================

spam_tracker = defaultdict(list)

# ===== WELCOME + AUTO ROLE =====
@bot.event
async def on_ready():
    print(f"Bot {bot.user} siap!")

@bot.event
async def on_member_join(member):
    # Auto Role
    role = discord.utils.get(member.guild.roles, name=AUTO_ROLE_NAME)
    if role:
        await member.add_roles(role)
        print(f"Role {AUTO_ROLE_NAME} diberikan ke {member.name}")

    # Cari channel welcome otomatis
    channel = None
    for ch in member.guild.text_channels:
        if "welcome" in ch.name.lower():
            channel = ch
            break
    if not channel:
        return

    # Download avatar
    async with aiohttp.ClientSession() as session:
        async with session.get(str(member.display_avatar.url)) as resp:
            avatar_data = await resp.read()

    # Buat welcome card
    card = Image.new("RGB", (800, 300), color=(20, 20, 30))
    draw = ImageDraw.Draw(card)

    avatar = Image.open(io.BytesIO(avatar_data)).resize((200, 200)).convert("RGBA")
    mask = Image.new("L", (200, 200), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 200, 200), fill=255)
    avatar.putalpha(mask)
    card.paste(avatar, (50, 50), avatar)

    draw.text((280, 80), "WELCOME", fill=(0, 200, 255))
    draw.text((280, 130), f"{member.name}", fill="white")
    draw.text((280, 180), f"Member ke-{member.guild.member_count}", fill=(150, 150, 150))

    output = io.BytesIO()
    card.save(output, format="PNG")
    output.seek(0)

    await channel.send(
        f"Welcome {member.mention} ke **{member.guild.name}**! 🎉",
        file=discord.File(output, "welcome.png")
    )

# ===== ANTI SPAM =====
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    now = time.time()

    spam_tracker[user_id] = [t for t in spam_tracker[user_id] if now - t < SPAM_TIME]
    spam_tracker[user_id].append(now)

    if len(spam_tracker[user_id]) >= SPAM_LIMIT:
        await message.delete()
        await message.channel.send(
            f"{message.author.mention} ⚠️ Jangan spam! Pesan kamu dihapus.",
            delete_after=5
        )
        spam_tracker[user_id] = []

    await bot.process_commands(message)

# ===== MODERASI COMMANDS =====
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Tidak ada alasan"):
    await member.kick(reason=reason)
    await ctx.send(f"✅ {member.name} telah di-kick. Alasan: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Tidak ada alasan"):
    await member.ban(reason=reason)
    await ctx.send(f"✅ {member.name} telah di-ban. Alasan: {reason}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ {amount} pesan dihapus!", delete_after=3)

bot.run(os.environ["TOKEN"])

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageOps, ImageFilter
import aiohttp
import io
import os
import asyncio
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

def make_welcome_card(avatar_data, username, member_count, server_name):
    W, H = 900, 320

    # Background gradient gelap
    card = Image.new("RGB", (W, H), color=(10, 10, 10))
    draw = ImageDraw.Draw(card)

    # Gradient overlay
    for i in range(H):
        ratio = i / H
        r = int(10 + 20 * ratio)
        g = int(10 + 10 * ratio)
        b = int(10 + 5 * ratio)
        draw.line([(0, i), (W, i)], fill=(r, g, b))

    # Gold accent bar kiri
    for x in range(8):
        alpha = 255 - x * 20
        draw.rectangle([(x, 0), (x, H)], fill=(184, 134, 11))

    # Gold accent bar kanan
    for x in range(8):
        alpha = 255 - x * 20
        draw.rectangle([(W - x - 1, 0), (W - x - 1, H)], fill=(184, 134, 11))

    # Gold line atas dan bawah
    draw.rectangle([(0, 0), (W, 4)], fill=(212, 175, 55))
    draw.rectangle([(0, H - 4), (W, H)], fill=(212, 175, 55))

    # Glow lingkaran di belakang avatar
    glow_x, glow_y = 160, 160
    for r in range(120, 90, -3):
        alpha = int(60 * (1 - (r - 90) / 30))
        glow_color = (212, 175, 55)
        draw.ellipse(
            [(glow_x - r, glow_y - r), (glow_x + r, glow_y + r)],
            outline=glow_color
        )

    # Avatar bulat
    avatar_img = Image.open(io.BytesIO(avatar_data)).resize((180, 180)).convert("RGBA")
    mask = Image.new("L", (180, 180), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 180, 180), fill=255)
    avatar_img.putalpha(mask)

    # Border gold avatar
    border_size = 194
    border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
    ImageDraw.Draw(border).ellipse((0, 0, border_size, border_size), fill=(212, 175, 55))
    card.paste(border, (glow_x - border_size // 2, glow_y - border_size // 2), border)

    avatar_pos = (glow_x - 90, glow_y - 90)
    card.paste(avatar_img, avatar_pos, avatar_img)

    # Teks WELCOME kecil di atas
    draw.text((340, 55), "WELCOME TO", fill=(212, 175, 55))

    # Nama server
    draw.text((340, 80), server_name.upper(), fill=(255, 255, 255))

    # Garis gold pemisah
    draw.rectangle([(340, 135), (840, 138)], fill=(212, 175, 55))

    # Nama member besar
    draw.text((340, 150), username, fill=(255, 255, 255))

    # Nomor member
    draw.text((340, 230), f"Member #{member_count}", fill=(180, 150, 50))

    # Teks bawah
    draw.text((340, 265), "Selamat bergabung!", fill=(120, 120, 120))

    return card

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

    # Cari channel welcome
    channel = None
    for ch in member.guild.text_channels:
        if "welcome" in ch.name.lower():
            channel = ch
            break
    if not channel:
        return

    # Download avatar
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(str(member.display_avatar.url)) as resp:
                avatar_data = await resp.read()
    except Exception as e:
        print(f"Gagal download avatar: {e}")
        await channel.send(f"Welcome {member.mention} ke **{member.guild.name}**!")
        return

    # Buat welcome card premium
    card = make_welcome_card(
        avatar_data,
        member.name,
        member.guild.member_count,
        member.guild.name
    )

    output = io.BytesIO()
    card.save(output, format="PNG")
    output.seek(0)

    await channel.send(
        f"Welcome {member.mention}!",
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
            f"{message.author.mention} Jangan spam! Pesan kamu dihapus.",
            delete_after=5
        )
        spam_tracker[user_id] = []

    await bot.process_commands(message)

# ===== MODERASI COMMANDS =====
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Tidak ada alasan"):
    await member.kick(reason=reason)
    await ctx.send(f"{member.name} telah di-kick. Alasan: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Tidak ada alasan"):
    await member.ban(reason=reason)
    await ctx.send(f"{member.name} telah di-ban. Alasan: {reason}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"{amount} pesan dihapus!", delete_after=3)

# ===== AUTO RECONNECT =====
async def main():
    while True:
        try:
            await bot.start(os.environ["TOKEN"])
        except Exception as e:
            print(f"Error: {e}, reconnecting in 5 seconds...")
            await asyncio.sleep(5)

asyncio.run(main())

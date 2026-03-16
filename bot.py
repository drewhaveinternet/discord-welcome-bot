import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageOps, ImageFilter, ImageFont
import aiohttp
import io
import os
import asyncio
import math
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

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def draw_hexagon(draw, cx, cy, size, fill=None, outline=None, width=2):
    points = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        x = cx + size * math.cos(angle)
        y = cy + size * math.sin(angle)
        points.append((x, y))
    if fill:
        draw.polygon(points, fill=fill)
    if outline:
        draw.polygon(points, outline=outline)

def make_welcome_card(avatar_data, username, member_count, server_name):
    W, H = 960, 340

    # ── BASE BACKGROUND ──
    card = Image.new("RGB", (W, H), (8, 8, 12))
    draw = ImageDraw.Draw(card)

    # ── BACKGROUND GRADIENT ──
    for y in range(H):
        ratio = y / H
        r = int(8 + 15 * (1 - ratio))
        g = int(8 + 8 * (1 - ratio))
        b = int(12 + 25 * (1 - ratio))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # ── GRID PATTERN (FPS HUD style) ──
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill=(255, 100, 0, 10))
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill=(255, 100, 0, 10))

    # ── DIAGONAL SLASH DECORATIONS ──
    for i in range(-5, 20):
        offset = i * 60
        draw.line([(offset, 0), (offset + H, H)], fill=(255, 100, 0), width=1)

    # ── CORNER BRACKETS (FPS HUD) ──
    bracket_color = (255, 140, 0)
    bracket_len = 30
    thick = 3
    # Top-left
    draw.rectangle([(15, 15), (15 + bracket_len, 15 + thick)], fill=bracket_color)
    draw.rectangle([(15, 15), (15 + thick, 15 + bracket_len)], fill=bracket_color)
    # Top-right
    draw.rectangle([(W - 15 - bracket_len, 15), (W - 15, 15 + thick)], fill=bracket_color)
    draw.rectangle([(W - 15 - thick, 15), (W - 15, 15 + bracket_len)], fill=bracket_color)
    # Bottom-left
    draw.rectangle([(15, H - 15 - thick), (15 + bracket_len, H - 15)], fill=bracket_color)
    draw.rectangle([(15, H - 15 - bracket_len), (15 + thick, H - 15)], fill=bracket_color)
    # Bottom-right
    draw.rectangle([(W - 15 - bracket_len, H - 15 - thick), (W - 15, H - 15)], fill=bracket_color)
    draw.rectangle([(W - 15 - thick, H - 15 - bracket_len), (W - 15, H - 15)], fill=bracket_color)

    # ── LEFT SIDE GLOW PANEL ──
    for i in range(280, 0, -1):
        alpha = int(80 * (1 - i / 280))
        draw.rectangle([(0, 0), (i, H)], fill=(255, 80, 0))

    # ── HEXAGON PATTERN (RPG style) ──
    for hx, hy, size, alpha in [
        (80, 170, 140, 30),
        (80, 170, 120, 20),
        (80, 170, 100, 15),
    ]:
        draw_hexagon(draw, hx, hy, size, outline=(255, 140, 0))

    # ── AVATAR GLOW ──
    for r in range(100, 75, -3):
        glow_alpha = int(120 * (1 - (r - 75) / 25))
        draw.ellipse(
            [(80 - r, 170 - r), (80 + r, 170 + r)],
            outline=(255, 120, 0)
        )

    # ── AVATAR ──
    try:
        avatar_img = Image.open(io.BytesIO(avatar_data)).resize((140, 140)).convert("RGBA")
        mask = Image.new("L", (140, 140), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 140, 140), fill=255)
        avatar_img.putalpha(mask)

        # Orange border
        border_size = 154
        border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
        ImageDraw.Draw(border).ellipse((0, 0, border_size - 1, border_size - 1), fill=(255, 140, 0))
        card.paste(border, (80 - border_size // 2, 170 - border_size // 2), border)

        # Inner dark border
        inner_size = 148
        inner = Image.new("RGBA", (inner_size, inner_size), (0, 0, 0, 0))
        ImageDraw.Draw(inner).ellipse((0, 0, inner_size - 1, inner_size - 1), fill=(20, 15, 10))
        card.paste(inner, (80 - inner_size // 2, 170 - inner_size // 2), inner)

        card.paste(avatar_img, (80 - 70, 170 - 70), avatar_img)
    except Exception as e:
        print(f"Avatar error: {e}")

    # ── VERTICAL SEPARATOR LINE ──
    for y in range(30, H - 30):
        ratio = abs(y - H // 2) / (H // 2)
        brightness = int(255 * (1 - ratio * 0.5))
        draw.point((195, y), fill=(brightness, int(brightness * 0.55), 0))

    # ── RIGHT PANEL CONTENT ──
    text_x = 220

    # SERVER NAME tag
    draw.rectangle([(text_x, 38), (text_x + 180, 62)], fill=(255, 100, 0))
    draw.rectangle([(text_x + 178, 38), (text_x + 188, 62)], fill=(200, 70, 0))
    draw.text((text_x + 8, 43), server_name.upper()[:20], fill=(255, 255, 255))

    # PLAYER JOINED text
    draw.text((text_x, 78), "PLAYER  JOINED  THE  SERVER", fill=(255, 140, 0))

    # Divider line with glow
    for thickness in range(3, 0, -1):
        alpha = 255 - (3 - thickness) * 80
        draw.rectangle(
            [(text_x, 108 - thickness), (W - 40, 108 + thickness)],
            fill=(255, 100, 0)
        )

    # USERNAME large
    draw.text((text_x, 120), username, fill=(255, 255, 255))

    # Stats bar (RPG style)
    draw.text((text_x, 185), "MEMBER ID", fill=(255, 100, 0))
    draw.text((text_x + 130, 185), f"#{member_count:04d}", fill=(255, 200, 100))

    draw.text((text_x + 320, 185), "STATUS", fill=(255, 100, 0))
    draw.text((text_x + 420, 185), "ACTIVE", fill=(100, 255, 100))

    # XP Bar (RPG element)
    bar_x, bar_y = text_x, 215
    bar_w, bar_h = 480, 12
    draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], fill=(30, 20, 10))
    draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], outline=(255, 100, 0))
    fill_w = min(bar_w, max(20, (member_count % 100) * bar_w // 100))
    for bx in range(fill_w):
        ratio = bx / bar_w
        r = int(255 * (1 - ratio * 0.3))
        g = int(100 + 50 * ratio)
        b = 0
        draw.line([(bar_x + bx, bar_y + 1), (bar_x + bx, bar_y + bar_h - 1)], fill=(r, g, b))
    draw.text((bar_x, bar_y + 16), "REPUTATION XP", fill=(150, 100, 50))
    draw.text((bar_x + 390, bar_y + 16), f"{member_count % 100}/100", fill=(255, 140, 0))

    # Bottom tagline
    draw.rectangle([(text_x, 285), (W - 40, 287)], fill=(80, 50, 0))
    draw.text((text_x, 293), "WELCOME  TO  THE  BATTLEFIELD  -  PROVE  YOUR  WORTH", fill=(100, 70, 30))

    # ── SCAN LINE EFFECT ──
    for y in range(0, H, 4):
        draw.line([(0, y), (W, y)], fill=(0, 0, 0))

    # ── TOP RIGHT HUD ──
    draw.text((W - 120, 20), "HCD // v1.0", fill=(255, 100, 0))
    draw.text((W - 100, 35), "SECURE LINK", fill=(100, 255, 100))

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

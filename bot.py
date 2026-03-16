import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageOps, ImageFilter
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
TICKET_CATEGORY = "Tickets"
SUPPORT_ROLE = "Admin"
# ====================

spam_tracker = defaultdict(list)

# ===== WELCOME CARD =====
def draw_hexagon(draw, cx, cy, size, fill=None, outline=None):
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
    card = Image.new("RGB", (W, H), (8, 8, 12))
    draw = ImageDraw.Draw(card)

    for y in range(H):
        ratio = y / H
        r = int(8 + 15 * (1 - ratio))
        g = int(8 + 8 * (1 - ratio))
        b = int(12 + 25 * (1 - ratio))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    for i in range(-5, 20):
        offset = i * 60
        draw.line([(offset, 0), (offset + H, H)], fill=(255, 100, 0))

    bracket_color = (255, 140, 0)
    bracket_len = 30
    thick = 3
    draw.rectangle([(15, 15), (15+bracket_len, 15+thick)], fill=bracket_color)
    draw.rectangle([(15, 15), (15+thick, 15+bracket_len)], fill=bracket_color)
    draw.rectangle([(W-15-bracket_len, 15), (W-15, 15+thick)], fill=bracket_color)
    draw.rectangle([(W-15-thick, 15), (W-15, 15+bracket_len)], fill=bracket_color)
    draw.rectangle([(15, H-15-thick), (15+bracket_len, H-15)], fill=bracket_color)
    draw.rectangle([(15, H-15-bracket_len), (15+thick, H-15)], fill=bracket_color)
    draw.rectangle([(W-15-bracket_len, H-15-thick), (W-15, H-15)], fill=bracket_color)
    draw.rectangle([(W-15-thick, H-15-bracket_len), (W-15, H-15)], fill=bracket_color)

    for i in range(280, 0, -1):
        draw.rectangle([(0, 0), (i, H)], fill=(255, 80, 0))

    for hx, hy, size in [(80, 170, 140), (80, 170, 120), (80, 170, 100)]:
        draw_hexagon(draw, hx, hy, size, outline=(255, 140, 0))

    for r in range(100, 75, -3):
        draw.ellipse([(80-r, 170-r), (80+r, 170+r)], outline=(255, 120, 0))

    try:
        avatar_img = Image.open(io.BytesIO(avatar_data)).resize((140, 140)).convert("RGBA")
        mask = Image.new("L", (140, 140), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 140, 140), fill=255)
        avatar_img.putalpha(mask)
        border_size = 154
        border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
        ImageDraw.Draw(border).ellipse((0, 0, border_size-1, border_size-1), fill=(255, 140, 0))
        card.paste(border, (80-border_size//2, 170-border_size//2), border)
        inner_size = 148
        inner = Image.new("RGBA", (inner_size, inner_size), (0, 0, 0, 0))
        ImageDraw.Draw(inner).ellipse((0, 0, inner_size-1, inner_size-1), fill=(20, 15, 10))
        card.paste(inner, (80-inner_size//2, 170-inner_size//2), inner)
        card.paste(avatar_img, (80-70, 170-70), avatar_img)
    except Exception as e:
        print(f"Avatar error: {e}")

    for y in range(30, H-30):
        ratio = abs(y - H//2) / (H//2)
        brightness = int(255 * (1 - ratio * 0.5))
        draw.point((195, y), fill=(brightness, int(brightness*0.55), 0))

    text_x = 220
    draw.rectangle([(text_x, 38), (text_x+180, 62)], fill=(255, 100, 0))
    draw.text((text_x+8, 43), server_name.upper()[:20], fill=(255, 255, 255))
    draw.text((text_x, 78), "PLAYER  JOINED  THE  SERVER", fill=(255, 140, 0))
    draw.rectangle([(text_x, 108), (W-40, 110)], fill=(255, 100, 0))
    draw.text((text_x, 120), username, fill=(255, 255, 255))
    draw.text((text_x, 185), "MEMBER ID", fill=(255, 100, 0))
    draw.text((text_x+130, 185), f"#{member_count:04d}", fill=(255, 200, 100))
    draw.text((text_x+320, 185), "STATUS", fill=(255, 100, 0))
    draw.text((text_x+420, 185), "ACTIVE", fill=(100, 255, 100))

    bar_x, bar_y = text_x, 215
    bar_w, bar_h = 480, 12
    draw.rectangle([(bar_x, bar_y), (bar_x+bar_w, bar_y+bar_h)], fill=(30, 20, 10))
    draw.rectangle([(bar_x, bar_y), (bar_x+bar_w, bar_y+bar_h)], outline=(255, 100, 0))
    fill_w = min(bar_w, max(20, (member_count % 100) * bar_w // 100))
    for bx in range(fill_w):
        ratio = bx / bar_w
        r = int(255 * (1 - ratio * 0.3))
        g = int(100 + 50 * ratio)
        draw.line([(bar_x+bx, bar_y+1), (bar_x+bx, bar_y+bar_h-1)], fill=(r, g, 0))
    draw.text((bar_x, bar_y+16), "REPUTATION XP", fill=(150, 100, 50))
    draw.text((bar_x+390, bar_y+16), f"{member_count % 100}/100", fill=(255, 140, 0))
    draw.rectangle([(text_x, 285), (W-40, 287)], fill=(80, 50, 0))
    draw.text((text_x, 293), "WELCOME  TO  THE  BATTLEFIELD  -  PROVE  YOUR  WORTH", fill=(100, 70, 30))

    for y in range(0, H, 4):
        draw.line([(0, y), (W, y)], fill=(0, 0, 0))

    draw.text((W-120, 20), "HCD // v1.0", fill=(255, 100, 0))
    draw.text((W-100, 35), "SECURE LINK", fill=(100, 255, 100))

    return card

# ===== WELCOME + AUTO ROLE =====
@bot.event
async def on_ready():
    print(f"Bot {bot.user} siap!")
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())

@bot.event
async def on_member_join(member):
    role = discord.utils.get(member.guild.roles, name=AUTO_ROLE_NAME)
    if role:
        await member.add_roles(role)

    channel = None
    for ch in member.guild.text_channels:
        if "welcome" in ch.name.lower():
            channel = ch
            break
    if not channel:
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(str(member.display_avatar.url)) as resp:
                avatar_data = await resp.read()
    except Exception as e:
        await channel.send(f"Welcome {member.mention} ke **{member.guild.name}**!")
        return

    card = make_welcome_card(avatar_data, member.name, member.guild.member_count, member.guild.name)
    output = io.BytesIO()
    card.save(output, format="PNG")
    output.seek(0)
    await channel.send(f"Welcome {member.mention}!", file=discord.File(output, "welcome.png"))

# ===== TICKET SYSTEM =====
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Buat Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.name.lower()}")
        if existing:
            await interaction.response.send_message(f"Kamu sudah punya ticket aktif: {existing.mention}", ephemeral=True)
            return

        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY)

        support_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            f"ticket-{user.name.lower()}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎫 Ticket Support HCD",
            description=(
                f"Halo {user.mention}! Selamat datang di support HCD.\n\n"
                f"**Jelaskan masalah kamu** dan tim support akan segera membantu!\n\n"
                f"```\n"
                f"User    : {user.name}\n"
                f"ID      : {user.id}\n"
                f"Server  : {guild.name}\n"
                f"```"
            ),
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="HCD Support System • Klik tutup jika sudah selesai")

        await channel.send(
            content=f"{user.mention} {support_role.mention if support_role else ''}",
            embed=embed,
            view=CloseTicketView()
        )
        await interaction.response.send_message(
            f"Ticket berhasil dibuat! {channel.mention}",
            ephemeral=True
        )


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Tutup Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Ticket Ditutup",
            description=f"Ticket ditutup oleh {interaction.user.mention}\nChannel akan dihapus dalam 5 detik...",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        await interaction.channel.delete()


@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    # Hapus pesan command
    await ctx.message.delete()

    # Cari atau buat channel ticket
    ticket_channel = discord.utils.get(ctx.guild.text_channels, name="ticket")
    if not ticket_channel:
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=False
            )
        }
        ticket_channel = await ctx.guild.create_text_channel(
            "ticket",
            overwrites=overwrites,
            topic="Klik tombol di bawah untuk membuat ticket support"
        )

    embed = discord.Embed(
        title="🎫 HCD SUPPORT TICKET",
        description=(
            "**Butuh bantuan? Kami siap membantu kamu!**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📌 **Cara Membuat Ticket:**\n"
            "> Klik tombol **Buat Ticket** di bawah\n"
            "> Channel private akan otomatis dibuat\n"
            "> Jelaskan masalah kamu\n"
            "> Tim support akan segera membalas\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ **Peraturan Ticket:**\n"
            "> Gunakan ticket dengan bijak\n"
            "> Jangan spam atau abuse sistem ticket\n"
            "> Satu user hanya boleh punya 1 ticket aktif\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.orange()
    )
    embed.set_footer(text="HCD Support System • Tersedia 24/7")

    await ticket_channel.send(embed=embed, view=TicketView())
    await ctx.send(f"Panel ticket berhasil dibuat di {ticket_channel.mention}!", delete_after=5)

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

# ===== MODERASI =====
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

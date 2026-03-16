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
TICKET_CATEGORY = "Tickets"
SUPPORT_ROLE = "Admin"
# ====================

spam_tracker = defaultdict(list)

# =====================
# WELCOME CARD PREMIUM
# =====================
def make_welcome_card(avatar_data, username, member_count, server_name):
    W, H = 1000, 360

    # === BASE ===
    card = Image.new("RGB", (W, H), (5, 5, 8))
    draw = ImageDraw.Draw(card)

    # === BACKGROUND GRADIENT ===
    for y in range(H):
        t = y / H
        r = int(5 + 10 * t)
        g = int(5 + 5 * t)
        b = int(8 + 20 * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # === SCANLINE SUBTLE ===
    for y in range(0, H, 3):
        draw.line([(0, y), (W, y)], fill=(0, 0, 0))

    # === LEFT GLOW PANEL ===
    for i in range(320, 0, -1):
        alpha = int(60 * (i / 320) ** 2)
        draw.rectangle([(0, 0), (i, H)], fill=(200, 70, 0))

    # === DIAGONAL LINES (subtle) ===
    for i in range(-10, 25):
        x = i * 55
        draw.line([(x, 0), (x + H, H)], fill=(255, 80, 0))

    # === LEFT PANEL BORDER ===
    for i in range(4):
        draw.rectangle([(310 - i, 0), (312 - i, H)], fill=(255, 120 - i*20, 0))

    # === HEXAGON RINGS ===
    cx, cy = 155, 180
    for size, color in [
        (148, (255, 140, 0)),
        (136, (200, 100, 0)),
        (124, (150, 70, 0)),
    ]:
        pts = []
        for j in range(6):
            angle = math.radians(60 * j)
            pts.append((cx + size * math.cos(angle), cy + size * math.sin(angle)))
        draw.polygon(pts, outline=color)

    # === GLOW RINGS ===
    for r in range(108, 80, -4):
        draw.ellipse([(cx-r, cy-r), (cx+r, cy+r)], outline=(255, 120, 0))

    # === AVATAR ===
    try:
        av = Image.open(io.BytesIO(avatar_data)).resize((148, 148)).convert("RGBA")
        mask = Image.new("L", (148, 148), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 148, 148), fill=255)
        av.putalpha(mask)

        # Gold border
        b1 = Image.new("RGBA", (160, 160), (0,0,0,0))
        ImageDraw.Draw(b1).ellipse((0,0,159,159), fill=(255, 160, 0))
        card.paste(b1, (cx-80, cy-80), b1)

        # Dark inner ring
        b2 = Image.new("RGBA", (152, 152), (0,0,0,0))
        ImageDraw.Draw(b2).ellipse((0,0,151,151), fill=(15, 10, 5))
        card.paste(b2, (cx-76, cy-76), b2)

        card.paste(av, (cx-74, cy-74), av)
    except Exception as e:
        print(f"Avatar error: {e}")

    # === CORNER BRACKETS ===
    bc = (255, 160, 0)
    bl = 35
    bw = 4
    # top-left
    draw.rectangle([(8, 8), (8+bl, 8+bw)], fill=bc)
    draw.rectangle([(8, 8), (8+bw, 8+bl)], fill=bc)
    # top-right
    draw.rectangle([(W-8-bl, 8), (W-8, 8+bw)], fill=bc)
    draw.rectangle([(W-8-bw, 8), (W-8, 8+bl)], fill=bc)
    # bottom-left
    draw.rectangle([(8, H-8-bw), (8+bl, H-8)], fill=bc)
    draw.rectangle([(8, H-8-bl), (8+bw, H-8)], fill=bc)
    # bottom-right
    draw.rectangle([(W-8-bl, H-8-bw), (W-8, H-8)], fill=bc)
    draw.rectangle([(W-8-bw, H-8-bl), (W-8, H-8)], fill=bc)

    # === TOP & BOTTOM BORDER ===
    draw.rectangle([(0, 0), (W, 4)], fill=(255, 140, 0))
    draw.rectangle([(0, H-4), (W, H)], fill=(255, 140, 0))

    # === RIGHT CONTENT PANEL ===
    tx = 335

    # --- SERVER TAG ---
    tag_w = 220
    draw.rectangle([(tx, 28), (tx+tag_w, 56)], fill=(180, 70, 0))
    draw.rectangle([(tx+tag_w, 28), (tx+tag_w+14, 56)], fill=(120, 45, 0))
    draw.rectangle([(tx, 28), (tx+4, 56)], fill=(255, 180, 0))
    draw.text((tx+12, 34), f"// {server_name.upper()[:18]}", fill=(255, 230, 180))

    # --- HUD TOP RIGHT ---
    draw.text((W-175, 16), "[ SECURE CONNECTION ]", fill=(80, 200, 80))
    draw.text((W-130, 32), "HCD  v2.0", fill=(255, 120, 0))

    # --- PLAYER JOINED ---
    draw.text((tx, 70), "NEW  PLAYER  DETECTED", fill=(255, 100, 0))

    # --- DIVIDER ---
    for i in range(3):
        alpha = 255 - i * 80
        draw.rectangle([(tx, 100+i), (W-30, 101+i)], fill=(255, 100+i*20, 0))

    # --- USERNAME LARGE ---
    # Shadow
    draw.text((tx+3, 118), username[:22], fill=(80, 40, 0))
    draw.text((tx+2, 117), username[:22], fill=(120, 60, 0))
    # Main
    draw.text((tx, 115), username[:22], fill=(255, 255, 255))

    # --- DIVIDER 2 ---
    draw.rectangle([(tx, 170), (W-30, 171)], fill=(60, 35, 0))

    # --- STATS ROW ---
    # Member ID box
    draw.rectangle([(tx, 182), (tx+190, 210)], fill=(20, 12, 5))
    draw.rectangle([(tx, 182), (tx+190, 210)], outline=(255, 100, 0))
    draw.text((tx+8, 186), "MEMBER ID", fill=(255, 100, 0))
    draw.text((tx+8, 198), f"# {member_count:05d}", fill=(255, 210, 100))

    # Status box
    draw.rectangle([(tx+205, 182), (tx+370, 210)], fill=(5, 20, 5))
    draw.rectangle([(tx+205, 182), (tx+370, 210)], outline=(0, 200, 80))
    draw.text((tx+213, 186), "STATUS", fill=(0, 200, 80))
    draw.text((tx+213, 198), "ONLINE", fill=(100, 255, 100))

    # Rank box
    draw.rectangle([(tx+385, 182), (tx+550, 210)], fill=(15, 10, 20))
    draw.rectangle([(tx+385, 182), (tx+550, 210)], outline=(150, 80, 255))
    draw.text((tx+393, 186), "RANK", fill=(150, 80, 255))
    draw.text((tx+393, 198), "RECRUIT", fill=(200, 150, 255))

    # --- XP BAR ---
    draw.text((tx, 224), "[ EXPERIENCE POINTS ]", fill=(255, 100, 0))
    bx, by = tx, 242
    bw2, bh = 610, 18
    # Bar background
    draw.rectangle([(bx, by), (bx+bw2, by+bh)], fill=(20, 12, 5))
    draw.rectangle([(bx, by), (bx+bw2, by+bh)], outline=(100, 50, 0))
    # Bar fill gradient
    fill_w = min(bw2-4, max(30, (member_count % 100) * (bw2-4) // 100))
    for px in range(fill_w):
        ratio = px / bw2
        r = int(255 * (1 - ratio * 0.2))
        g = int(80 + 120 * ratio)
        b2 = int(0 + 30 * ratio)
        draw.line([(bx+2+px, by+2), (bx+2+px, by+bh-2)], fill=(r, g, b2))
    # XP text overlay
    xp_val = member_count % 100
    draw.text((bx+5, by+2), f"XP  {xp_val}/100", fill=(255, 220, 150))
    draw.text((bx+bw2-65, by+2), f"LVL {member_count//100 + 1}", fill=(255, 200, 100))

    # --- BOTTOM TAGLINE ---
    draw.rectangle([(tx, 278), (W-30, 280)], fill=(60, 35, 0))
    draw.text((tx, 288), "WELCOME  TO  THE  BATTLEFIELD  //  PROVE  YOUR  WORTH", fill=(120, 70, 20))
    draw.text((tx, 308), f"You are our {member_count}th warrior. Stand strong.", fill=(80, 50, 15))

    return card


# ===== EVENTS =====
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
    except:
        await channel.send(f"Welcome {member.mention} ke **{member.guild.name}**!")
        return

    card = make_welcome_card(avatar_data, member.name, member.guild.member_count, member.guild.name)
    output = io.BytesIO()
    card.save(output, format="PNG")
    output.seek(0)
    await channel.send(f"Welcome {member.mention}!", file=discord.File(output, "welcome.png"))

@bot.event
async def on_member_remove(member):
    # Kirim DM notif ke user yang di-kick/leave
    try:
        embed = discord.Embed(
            title="Kamu telah meninggalkan server",
            description=(
                f"Kamu telah keluar dari **{member.guild.name}**.\n\n"
                f"Jika kamu di-kick atau ban tanpa alasan yang jelas,\n"
                f"silakan hubungi admin melalui server lain.\n\n"
                f"Terima kasih telah bergabung bersama kami!"
            ),
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)
        embed.set_footer(text=f"HCD System • {member.guild.name}")
        await member.send(embed=embed)
    except:
        pass

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
            await interaction.response.send_message(
                f"Kamu sudah punya ticket aktif: {existing.mention}",
                ephemeral=True
            )
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
            title="TICKET SUPPORT AKTIF",
            description=(
                f"Halo {user.mention}!\n\n"
                f"Ticket support kamu telah dibuat.\n"
                f"Jelaskan masalah kamu secara detail dan\n"
                f"tim support akan segera membantu!\n\n"
                f"```\n"
                f"User   : {user.name}\n"
                f"ID     : {user.id}\n"
                f"Server : {guild.name}\n"
                f"```"
            ),
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="HCD Support System • Klik Tutup jika sudah selesai")

        mention_text = f"{user.mention}"
        if support_role:
            mention_text += f" {support_role.mention}"

        await channel.send(content=mention_text, embed=embed, view=CloseTicketView())

        # Kirim DM ke user bahwa ticket dibuat
        try:
            dm_embed = discord.Embed(
                title="Ticket Kamu Telah Dibuat",
                description=(
                    f"Ticket support kamu di **{guild.name}** telah berhasil dibuat!\n\n"
                    f"Tim support akan segera membalas pesanmu.\n"
                    f"Sabar ya, kami akan segera membantu!"
                ),
                color=discord.Color.orange()
            )
            dm_embed.set_footer(text="HCD Support System")
            await user.send(embed=dm_embed)
        except:
            pass

        await interaction.response.send_message(
            f"Ticket berhasil dibuat! {channel.mention}",
            ephemeral=True
        )


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Tutup Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild

        # Cari siapa pemilik ticket
        ticket_owner_name = channel.name.replace("ticket-", "")
        ticket_owner = discord.utils.find(
            lambda m: m.name.lower() == ticket_owner_name,
            guild.members
        )

        embed = discord.Embed(
            title="Ticket Ditutup",
            description=(
                f"Ticket ditutup oleh {interaction.user.mention}\n"
                f"Channel akan dihapus dalam 5 detik..."
            ),
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

        # Kirim DM notif ke pemilik ticket
        if ticket_owner:
            try:
                dm_embed = discord.Embed(
                    title="Ticket Kamu Telah Ditutup",
                    description=(
                        f"Ticket support kamu di **{guild.name}** telah ditutup oleh **{interaction.user.name}**.\n\n"
                        f"Jika masalah kamu belum terselesaikan,\n"
                        f"silakan buat ticket baru di server.\n\n"
                        f"Terima kasih telah menghubungi support HCD!"
                    ),
                    color=discord.Color.red()
                )
                dm_embed.set_footer(text="HCD Support System")
                await ticket_owner.send(embed=dm_embed)
            except:
                pass

        await asyncio.sleep(5)
        await channel.delete()


@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    await ctx.message.delete()

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
        title="HCD SUPPORT SYSTEM",
        description=(
            "**Butuh bantuan? Tim HCD siap membantu kamu!**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**CARA MEMBUAT TICKET:**\n"
            "```\n"
            "1. Klik tombol BUAT TICKET di bawah\n"
            "2. Channel private otomatis dibuat\n"
            "3. Jelaskan masalah kamu\n"
            "4. Tunggu balasan dari tim support\n"
            "5. Klik TUTUP TICKET jika selesai\n"
            "```\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**PERATURAN TICKET:**\n"
            "```\n"
            "- Gunakan ticket dengan bijak\n"
            "- Jangan spam atau abuse sistem\n"
            "- 1 user hanya boleh 1 ticket aktif\n"
            "- Kamu akan dapat notif DM otomatis\n"
            "```\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.orange()
    )
    embed.set_footer(text="HCD Support System • Tersedia 24/7 • Bot akan DM kamu otomatis")

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
    # Kirim DM ke member sebelum di-kick
    try:
        embed = discord.Embed(
            title="Kamu Telah Di-Kick",
            description=(
                f"Kamu telah di-kick dari **{ctx.guild.name}**\n\n"
                f"**Alasan:** {reason}\n\n"
                f"Kamu bisa join kembali jika sudah memahami peraturan server."
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text=f"HCD Moderation System")
        await member.send(embed=embed)
    except:
        pass

    await member.kick(reason=reason)
    await ctx.send(f"{member.name} telah di-kick. Alasan: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Tidak ada alasan"):
    # Kirim DM ke member sebelum di-ban
    try:
        embed = discord.Embed(
            title="Kamu Telah Di-Ban",
            description=(
                f"Kamu telah di-ban dari **{ctx.guild.name}**\n\n"
                f"**Alasan:** {reason}\n\n"
                f"Jika kamu merasa ini tidak adil, hubungi admin."
            ),
            color=discord.Color.dark_red()
        )
        embed.set_footer(text=f"HCD Moderation System")
        await member.send(embed=embed)
    except:
        pass

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

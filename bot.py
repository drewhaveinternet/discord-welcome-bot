import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageOps
import aiohttp
import io
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot {bot.user} siap!")

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="welcome")
    if not channel:
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(str(member.display_avatar.url)) as resp:
            avatar_data = await resp.read()

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
        f"Welcome {member.mention} ke **{member.guild.name}**!",
        file=discord.File(output, "welcome.png")
    )

bot.run(os.environ["TOKEN"])

import discord
import random
import asyncio
import youtube_dl
from discord.ext import commands
from config import settings
from config import ytdl_format_options
from config import ffmpeg_options
from discord_components import DiscordComponents, Button, ButtonStyle

intents = discord.Intents.default()
intents.members = True

youtube_dl.utils.bug_reports_message = lambda: ''
bot = commands.Bot(command_prefix=settings['prefix'], intents=intents)

greetings = ['Здарова, ', 'Привет, ', 'Приветос, ']

syncTube_url = 'https://synchtube.ru/r/Steel20'
notAlone_url = 'https://notalone.tv/room/mX4UNcGZFp'
jackbox_url = 'https://jackbox.fun/'


@bot.command(aliases=['ghbdtn', 'привет', 'Здарова', 'Привет'])
async def hello(ctx):
    """Greetings"""
    author = ctx.message.author
    await ctx.send(f'{random.choice(greetings)}  {author.mention}!')


@bot.command()
async def roll(ctx, dice: str):
    """Rolls dice in format nDm """

    try:
        rolls, limit = map(int, dice.split('d'))
    except Exception:
        await ctx.send('Формат аргумента <количество>d<кубик>!')
        return
    result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
    await ctx.send(result)


@bot.command()
async def VCID(ctx):
    """Get channel ID"""
    await ctx.send(ctx.message.author.voice.channel.id)


@bot.command(aliases=['l', 'L'])
async def links_send(ctx):
    """Ссылки на всякий контент"""
    await ctx.send(
        embed=discord.Embed(title="Ссылки"),
        components=[
            Button(style=ButtonStyle.URL, label="SyncTube", url=syncTube_url),
            Button(style=ButtonStyle.URL, label="NotAlone", url=notAlone_url),
            Button(style=ButtonStyle.URL, label="JackBox", url=jackbox_url)
        ]
    )


ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot_):
        self.bot = bot_

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command(aliases=['Play', 'p', 'P'])
    async def play(self, ctx, *, url):
        """Plays a music from YouTube link"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command()
    async def stop(self, ctx):
        """Stop and leave"""

        await ctx.voice_client.disconnect()

    @commands.command(aliases=['r'])
    async def radio(self, ctx):
        """LoFi radio"""

        player = await YTDLSource.from_url('https://www.youtube.com/watch?v=5qap5aO4i9A&ab_channel=LofiGirl',
                                           loop=self.bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
        await ctx.send('Now playing: {}'.format(player.title))

    @play.before_invoke
    @radio.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


@bot.event
async def on_voice_state_update(member, before, after):
    if not member.id == bot.user.id:
        return

    elif before.channel is None:
        voice = after.channel.guild.voice_client
        time = 0
        while True:
            await asyncio.sleep(1)
            time = time + 1
            if voice.is_playing() and not voice.is_paused():
                time = 0
            if time == 60:
                await voice.disconnect()
            if not voice.is_connected():
                break


@bot.event
async def on_ready():
    DiscordComponents(bot)
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('------')


bot.add_cog(Music(bot))
bot.run(settings['token'])

#####前提条件のため操作禁止#####
import asyncio
import os
from dotenv import load_dotenv

import discord
from discord.ext import commands

load_dotenv()

TOKEN = os.getenv("TOKEN")
PREFIX = os.getenv("PREFIX", "pmt!")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

current_tasks = {}
#####ここまで#####

#####ポモドーロタイマー処理#####
async def play_sound(ctx, filename):
    if not ctx.author.voice:
        await ctx.send("VCに入室してください")
        return

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        vc = await voice_channel.connect()
    else:
        vc = ctx.voice_client

    path = f"sounds/{filename}"

    if not os.path.exists(path):
        await ctx.send(f"音声ファイルが見つかりません: {path}")
        return

    while vc.is_playing():
        await asyncio.sleep(0.2)

    vc.play(discord.FFmpegPCMAudio(path))

    while vc.is_playing():
        await asyncio.sleep(0.2)


async def update_timer_message(message, status, current_round, total_rounds, seconds):
    minutes = seconds // 60
    remain_seconds = seconds % 60

    await message.edit(
        content=(
            "🍅 ポモドーロタイマー\n\n"
            f"状態: {status}\n"
            f"セット: {current_round} / {total_rounds}\n"
            f"残り: {minutes:02}:{remain_seconds:02}"
        )
    )


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


#####動作中処理#####
@bot.command()
async def start(ctx, work_min: int, break_min: int, rounds: int):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("VCに入室後、開始してください")
        return

    channel_id = ctx.author.voice.channel.id

    task = current_tasks.get(channel_id)
    if task and not task.done():
        await ctx.send("タイマー起動中。停止： `pmt!stop`")
        return

    async def timer():
        await play_sound(ctx, "start.mp3")

        timer_message = await ctx.send(
            "🍅 ポモドーロタイマー\n\n準備中..."
        )

        for i in range(1, rounds + 1):
            for remain in range(work_min * 60, -1, -30):
                await update_timer_message(
                    timer_message,
                    "作業中",
                    i,
                    rounds,
                    remain
                )
                await asyncio.sleep(30)

            if i == rounds:
                await update_timer_message(
                    timer_message,
                    "終了",
                    rounds,
                    rounds,
                    0
                )
                await play_sound(ctx, "finish.mp3")
                await asyncio.sleep(1)

                if ctx.voice_client:
                    await ctx.voice_client.disconnect()
                    await ctx.send("全セット終了 VC退出")
 
                current_tasks.pop(channel_id, None)
                break


            await play_sound(ctx, "break.mp3")

            for remain in range(break_min * 60, -1, -30):
                await update_timer_message(
                    timer_message,
                    "休憩中",
                    i,
                    rounds,
                    remain
                )
                await asyncio.sleep(30)

            await play_sound(ctx, "start.mp3")

    current_tasks[channel_id] = asyncio.create_task(timer())


#####ストップ処理#####
@bot.command()
async def stop(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("停止するVCに入室してください")
        return

    channel_id = ctx.author.voice.channel.id
    task = current_tasks.get(channel_id)

    if task and not task.done():
        task.cancel()
        current_tasks.pop(channel_id, None)

        await ctx.send("タイマー停止")

        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("VC退出")
        
    else:
        await ctx.send("VCで起動中タイマーはありません")


#####VC入室
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("VC退出。")
    else:
        await ctx.send("VCに入室していません")


#####エラー処理#####
@start.error
async def start_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("使い方：`pmt!start <作業分> <休憩分> <回数>` 例：`pmt!start 25 5 4`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("条件を指定してください 例：`pmt!start 25 5 4`")
    else:
        await ctx.send(f"エラー発生: {type(error).__name__}")


bot.run(TOKEN)
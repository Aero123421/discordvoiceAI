import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands
import json


class SetupCog(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    setup = SlashCommandGroup("setup", "Botの初期設定を行います。")

    @setup.command(name="channels", description="録音対象カテゴリと送信先を設定")
    async def setup_channels(self, ctx: discord.ApplicationContext):
        categories = [
            c for c in ctx.guild.channels
            if isinstance(c, discord.CategoryChannel)
        ]
        text_channels = [c for c in ctx.guild.text_channels]
        if not categories or not text_channels:
            await ctx.respond(
                "設定に必要なチャンネルが見つかりません。",
                ephemeral=True,
            )
            return

        options_cat = [
            discord.SelectOption(label=c.name, value=str(c.id))
            for c in categories
        ]
        options_text = [
            discord.SelectOption(label=c.name, value=str(c.id))
            for c in text_channels
        ]
        category_select = discord.ui.Select(
            placeholder="録音カテゴリ",
            options=options_cat,
        )
        text_select = discord.ui.Select(
            placeholder="送信先チャンネル",
            options=options_text,
        )

        async def callback(interaction: discord.Interaction):
            config = {
                "target_category_id": int(category_select.values[0]),
                "output_channel_id": int(text_select.values[0])
            }
            with open(f"config_{ctx.guild.id}.json", "w") as f:
                json.dump(config, f)
            await interaction.response.send_message("設定完了", ephemeral=True)

        category_select.callback = callback
        text_select.callback = callback

        view = discord.ui.View()
        view.add_item(category_select)
        view.add_item(text_select)
        await ctx.respond("設定を選択してください", view=view, ephemeral=True)


def setup(bot):
    bot.add_cog(SetupCog(bot))

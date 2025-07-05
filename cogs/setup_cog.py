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
        class SetupView(discord.ui.View):
            def __init__(self, ctx):
                super().__init__(timeout=180)
                self.ctx = ctx
                self.category_id: int | None = None
                self.output_channel_id: int | None = None

                self.category_select = discord.ui.Select(
                    placeholder="録音カテゴリ",
                    options=options_cat,
                )
                self.text_select = discord.ui.Select(
                    placeholder="送信先チャンネル",
                    options=options_text,
                )

                self.category_select.callback = self.category_callback
                self.text_select.callback = self.text_callback

                self.add_item(self.category_select)
                self.add_item(self.text_select)

            async def category_callback(self, interaction: discord.Interaction):
                self.category_id = int(self.category_select.values[0])
                await interaction.response.defer()

            async def text_callback(self, interaction: discord.Interaction):
                self.output_channel_id = int(self.text_select.values[0])
                await interaction.response.defer()

            @discord.ui.button(label="保存", style=discord.ButtonStyle.green)
            async def save(self, button: discord.ui.Button, interaction: discord.Interaction):
                if self.category_id is None or self.output_channel_id is None:
                    await interaction.response.send_message(
                        "カテゴリと送信先を選択してください。",
                        ephemeral=True,
                    )
                    return
                config = {
                    "target_category_id": self.category_id,
                    "output_channel_id": self.output_channel_id,
                }
                with open(f"config_{self.ctx.guild.id}.json", "w") as f:
                    json.dump(config, f)
                await interaction.response.send_message("設定完了", ephemeral=True)
                self.stop()

        view = SetupView(ctx)
        await ctx.respond("設定を選択してください", view=view, ephemeral=True)

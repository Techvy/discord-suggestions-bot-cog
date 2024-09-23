import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput

class Suggestionbuttons(View):
    def __init__(self, embed, message):
        super().__init__()
        self.upvotes = 0
        self.downvotes = 0
        self.voters = {} 
        self.embed = embed  
        self.message = message
        self.upvote_button = Button(label=self.get_upvote_label(), style=discord.ButtonStyle.green)
        self.downvote_button = Button(label=self.get_downvote_label(), style=discord.ButtonStyle.red)
        self.add_item(self.upvote_button)
        self.add_item(self.downvote_button)
        self.upvote_button.callback = self.upvote_callback
        self.downvote_button.callback = self.downvote_callback

#------Simple function to get upvote and downvotes percentage--------#
    def get_vote_percentage(self):
        total_votes = self.upvotes + self.downvotes
        if total_votes == 0:
            return 0, 0
        upvote_percentage = (self.upvotes / total_votes) * 100
        downvote_percentage = (self.downvotes / total_votes) * 100
        return upvote_percentage, downvote_percentage
    
#------Return upvotes--------#
    def get_upvote_label(self):
        upvote_percentage, _ = self.get_vote_percentage()
        return f"👍 {self.upvotes} ({upvote_percentage:.0f}%)"
    
#------Return downvotes--------#
    def get_downvote_label(self):
        _, downvote_percentage = self.get_vote_percentage()
        return f"👎 {self.downvotes} ({downvote_percentage:.0f}%)"
    
#------Update views of embed--------#
    async def update_view_and_embed(self):
        # Update button labels with percentages
        self.upvote_button.label = self.get_upvote_label()
        self.downvote_button.label = self.get_downvote_label()

#------Update embed fields--------#
        upvote_percentage, downvote_percentage = self.get_vote_percentage()
        self.embed.set_field_at(0, name=f"Upvotes ({upvote_percentage:.0f}%)", value=str(self.upvotes), inline=True)
        self.embed.set_field_at(1, name=f"Downvotes ({downvote_percentage:.0f}%)", value=str(self.downvotes), inline=True)

#------Edit the message to reflect the updated embed and view--------#
        await self.message.edit(embed=self.embed, view=self)

    async def upvote_callback(self, interaction: discord.Interaction):
        """Handle the upvote button press and update the count."""
        user_id = interaction.user.id

        if user_id in self.voters:
            if self.voters[user_id] == "upvote":
                await interaction.response.send_message("You've already upvoted!", ephemeral=True)
            else:
                await interaction.response.send_message("You've already downvoted and cannot upvote.", ephemeral=True)
            return

#------Register users upvotes--------#
        self.voters[user_id] = "upvote"
        self.upvotes += 1

        await self.update_view_and_embed()
        await interaction.response.send_message("Upvoted!", ephemeral=True)

    async def downvote_callback(self, interaction: discord.Interaction):
        """Handle the downvote button press and update the count."""
        user_id = interaction.user.id

        if user_id in self.voters:
            if self.voters[user_id] == "downvote":
                await interaction.response.send_message("You've already downvoted!", ephemeral=True)
            else:
                await interaction.response.send_message("You've already upvoted and cannot downvote.", ephemeral=True)
            return

#------Register users downvotes--------#
        self.voters[user_id] = "downvote"
        self.downvotes += 1
        await self.update_view_and_embed()

        await interaction.response.send_message("Downvoted!", ephemeral=True)

#-------Modal for suggestion input-------#
class SuggestionModal(Modal):
    def __init__(self, bot, channel_id):
        super().__init__(title="Submit a Suggestion")
        self.suggestion_input = TextInput(label="Your Suggestion", style=discord.TextStyle.paragraph)
        self.add_item(self.suggestion_input)
        self.bot = bot
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        suggestion_channel = self.bot.get_channel(self.channel_id)

        if suggestion_channel is None:
            await interaction.response.send_message("Suggestion channel not found. Please check the channel ID.", ephemeral=True)
            return
        
#-------Create an embed with initial 0 upvotes and downovtes respectively.-------#
        embed = discord.Embed(title="New Suggestion", description=f"> {self.suggestion_input.value}", color=discord.Color.blue())
        embed.add_field(name="Upvotes (0%)", value="0", inline=True)
        embed.add_field(name="Downvotes (0%)", value="0", inline=True)
        embed.set_footer(text=f"Suggested by {interaction.user.display_name}", icon_url=interaction.user.avatar.url)
        message = await suggestion_channel.send(embed=embed)
        view = Suggestionbuttons(embed=embed, message=message)
        await message.edit(view=view)
        await interaction.response.send_message(f"Your suggestion has been submitted to {suggestion_channel.mention}!", ephemeral=True)

class DecisionModal(Modal):
    def __init__(self, bot, suggestion_message, action, response_channel):
        super().__init__(title=f"{action.capitalize()} Suggestion")
        self.reason_input = TextInput(label="Reason for decision", style=discord.TextStyle.paragraph)
        self.add_item(self.reason_input)
        self.bot = bot
        self.suggestion_message = suggestion_message
        self.action = action
        self.response_channel = response_channel

    async def on_submit(self, interaction: discord.Interaction):
        response_channel = self.bot.get_channel(self.response_channel)
        if response_channel is None:
            await interaction.response.send_message("Response channel not found.", ephemeral=True)
            return
        embed_color = discord.Color.green() if self.action == "approve" else discord.Color.red()
        embed_title = f"Suggestion {'Approved' if self.action == 'approve' else 'Denied'}"
        response_embed = discord.Embed(
            title=embed_title,
            description=self.suggestion_message.embeds[0].description,  # Ensure only the description is included
            color=embed_color
        )
        response_embed.add_field(name="Reason", value=self.reason_input.value, inline=False)
        response_embed.set_footer(text=f"Processed by {interaction.user.display_name}", icon_url=interaction.user.avatar.url)
        await response_channel.send(embed=response_embed)
        await interaction.response.send_message(f"Suggestion has been {self.action}d and posted in {response_channel.mention}.", ephemeral=True)
        updated_embed = self.suggestion_message.embeds[0]
        updated_embed.color = embed_color
        updated_embed.title = f"Suggestion {self.action.capitalize()}"

        await self.suggestion_message.edit(embed=updated_embed)

class SuggestionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.suggestion_channel_id = 1287630035259232320  # Replace with your suggestion channel ID
        self.approved_channel_id = 1287638951657472052  # Replace with your approved suggestions channel ID
        self.denied_channel_id = 1287638937774325772  # Replace with your denied suggestions channel ID


#------- COMMANDS -------#
    @commands.hybrid_command(name="suggest", description="Make a suggestion!")
    async def suggest(self, ctx: commands.Context):
        """Opens a modal to submit a suggestion."""
        if ctx.interaction:
            modal = SuggestionModal(self.bot, self.suggestion_channel_id)
            await ctx.interaction.response.send_modal(modal)
        else:
            await ctx.send("This command can only be used as a slash command.")
 
    @commands.hybrid_command(name="approve", description="Approve a suggestion by its message ID.")
    async def approve(self, ctx: commands.Context, message_id: str): # take as string and later convert to int due to discord bugs
        try:
            message_id_int = int(message_id) # int conversion
            suggestion_channel = self.bot.get_channel(self.suggestion_channel_id)
            suggestion_message = await suggestion_channel.fetch_message(message_id_int)
            if suggestion_message is None:
                await ctx.send("Suggestion not found.")
                return
            if ctx.interaction:
                modal = DecisionModal(self.bot, suggestion_message, "approve", self.approved_channel_id)
                await ctx.interaction.response.send_modal(modal)
            else:
                await ctx.send("This command can only be used as a slash command.")
        except ValueError:
            await ctx.send("Please provide a valid message ID as an integer.")
        except discord.NotFound:
            await ctx.send("No message found with that ID.")


    @commands.hybrid_command(name="deny", description="Deny a suggestion by its message ID.")
    async def deny(self, ctx: commands.Context, message_id: str):
        message_id_int = int(message_id)
        suggestion_channel = self.bot.get_channel(self.suggestion_channel_id)
        suggestion_message = await suggestion_channel.fetch_message(message_id)
        if suggestion_message is None:
            await ctx.send("Suggestion not found.")
            return
        if ctx.interaction:
            modal = DecisionModal(self.bot, suggestion_message, "deny", self.denied_channel_id)
            await ctx.interaction.response.send_modal(modal)
        else:
            await ctx.send("This command can only be used as a slash command.")

#MAIN THING TO RUN THE THE COG.
async def setup(bot):
    await bot.add_cog(SuggestionCog(bot))
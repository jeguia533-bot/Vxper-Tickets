import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

# =========================
# VXPER HARD-CODED SETTINGS
# =========================

MIN_STAFF_ROLE_ID = 1517947923009376289

TICKET_CATEGORY_ID = 1517947925437874279

APPLICATION_LOGS_CHANNEL_ID = 1517947925253066902
APPROVED_CHANNEL_ID = 1517947925437874277
DENIED_CHANNEL_ID = 1517947925437874278

BOT_PREFIX = "!"


# =========================
# BOT SETUP
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)


# =========================
# HELPERS
# =========================

def safe_channel_name(username: str) -> str:
    cleaned = "".join(ch for ch in username.lower() if ch.isalnum() or ch in ["-", "_"])
    return cleaned[:20] if cleaned else "user"


def can_manage_ticket(member: discord.Member) -> bool:
    required_role = member.guild.get_role(MIN_STAFF_ROLE_ID)

    if required_role is None:
        return False

    return member.top_role.position >= required_role.position


def get_staff_roles_for_ticket(guild: discord.Guild):
    """
    Discord channel overwrites do not automatically include higher roles.
    This adds the required role AND every role higher than it to the ticket.
    """
    required_role = guild.get_role(MIN_STAFF_ROLE_ID)

    if required_role is None:
        return []

    staff_roles = []

    for role in guild.roles:
        if role.name == "@everyone":
            continue

        if role.position >= required_role.position:
            staff_roles.append(role)

    return staff_roles


async def send_log(guild: discord.Guild, title: str, description: str, color: discord.Color):
    channel = guild.get_channel(APPLICATION_LOGS_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    await channel.send(embed=embed)


async def send_result_log(guild: discord.Guild, approved: bool, title: str, description: str, color: discord.Color):
    channel_id = APPROVED_CHANNEL_ID if approved else DENIED_CHANNEL_ID
    channel = guild.get_channel(channel_id)

    if channel is None:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    await channel.send(embed=embed)


async def create_ticket_channel(
    interaction: discord.Interaction,
    ticket_name: str,
    reason: str
):
    guild = interaction.guild
    user = interaction.user
    category = guild.get_channel(TICKET_CATEGORY_ID)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True
        )
    }

    for role in get_staff_roles_for_ticket(guild):
        overwrites[role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True
        )

    ticket_channel = await guild.create_text_channel(
        name=ticket_name,
        category=category,
        overwrites=overwrites,
        reason=reason
    )

    return ticket_channel


# =========================
# STAFF BUTTONS
# =========================

class TicketStaffButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Approve",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="vxper_ticket_approve"
    )
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_manage_ticket(interaction.user):
            return await interaction.response.send_message(
                "❌ You do not have permission to use this button.",
                ephemeral=True
            )

        is_rank = interaction.channel.name.startswith("rank-request-")

        if is_rank:
            public_message = (
                "✅ Your high rank request has been approved.\n\n"
                "A staff member will contact you shortly with the next steps."
            )
            log_title = "✅ High Rank Request Approved"
            result_title = "✅ High Rank Request Approved"
        else:
            public_message = (
                "✅ Congratulations!\n\n"
                "Your VXPER application has been approved.\n"
                "A staff member will contact you shortly with the next steps."
            )
            log_title = "✅ Guild Application Approved"
            result_title = "✅ Guild Application Approved"

        await interaction.response.send_message(public_message)

        result_description = (
            f"Ticket: {interaction.channel.mention}\n"
            f"Reviewed By: {interaction.user.mention}"
        )

        await send_result_log(
            interaction.guild,
            True,
            result_title,
            result_description,
            discord.Color.green()
        )

        await send_log(
            interaction.guild,
            log_title,
            f"Ticket: {interaction.channel.mention}\nStaff: {interaction.user.mention}",
            discord.Color.green()
        )

    @discord.ui.button(
        label="Needs Discussion",
        emoji="🟡",
        style=discord.ButtonStyle.primary,
        custom_id="vxper_ticket_discussion"
    )
    async def discussion(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_manage_ticket(interaction.user):
            return await interaction.response.send_message(
                "❌ You do not have permission to use this button.",
                ephemeral=True
            )

        is_rank = interaction.channel.name.startswith("rank-request-")

        if is_rank:
            public_message = (
                "🟡 Your high rank request needs further discussion with staff.\n\n"
                "Please wait while the team reviews your request."
            )
            log_title = "🟡 High Rank Request Needs Discussion"
        else:
            public_message = (
                "🟡 Your VXPER application needs further discussion with staff.\n\n"
                "Please wait while the team reviews your application."
            )
            log_title = "🟡 Guild Application Needs Discussion"

        await interaction.response.send_message(public_message)

        await send_log(
            interaction.guild,
            log_title,
            f"Ticket: {interaction.channel.mention}\nStaff: {interaction.user.mention}",
            discord.Color.gold()
        )

    @discord.ui.button(
        label="Deny",
        emoji="❌",
        style=discord.ButtonStyle.danger,
        custom_id="vxper_ticket_deny"
    )
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_manage_ticket(interaction.user):
            return await interaction.response.send_message(
                "❌ You do not have permission to use this button.",
                ephemeral=True
            )

        is_rank = interaction.channel.name.startswith("rank-request-")

        if is_rank:
            public_message = (
                "❌ Your high rank request has been denied at this time.\n\n"
                "You may request again in the future if your activity or contribution improves."
            )
            log_title = "❌ High Rank Request Denied"
            result_title = "❌ High Rank Request Denied"
        else:
            public_message = (
                "❌ Unfortunately, your VXPER application has not been approved at this time.\n\n"
                "Thank you for your interest in VXPER."
            )
            log_title = "❌ Guild Application Denied"
            result_title = "❌ Guild Application Denied"

        await interaction.response.send_message(public_message)

        result_description = (
            f"Ticket: {interaction.channel.mention}\n"
            f"Reviewed By: {interaction.user.mention}"
        )

        await send_result_log(
            interaction.guild,
            False,
            result_title,
            result_description,
            discord.Color.red()
        )

        await send_log(
            interaction.guild,
            log_title,
            f"Ticket: {interaction.channel.mention}\nStaff: {interaction.user.mention}",
            discord.Color.red()
        )

    @discord.ui.button(
        label="Close",
        emoji="🔒",
        style=discord.ButtonStyle.secondary,
        custom_id="vxper_ticket_close"
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_manage_ticket(interaction.user):
            return await interaction.response.send_message(
                "❌ You do not have permission to use this button.",
                ephemeral=True
            )

        await send_log(
            interaction.guild,
            "🔒 Ticket Closed",
            f"Ticket: #{interaction.channel.name}\nClosed By: {interaction.user.mention}",
            discord.Color.dark_gray()
        )

        await interaction.response.send_message("🔒 Closing this ticket...")
        await interaction.channel.delete(reason=f"VXPER ticket closed by {interaction.user}")


# =========================
# PANEL BUTTONS
# =========================

class GuildApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Apply To VXPER",
        emoji="📝",
        style=discord.ButtonStyle.primary,
        custom_id="vxper_guild_apply"
    )
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        ticket_name = f"application-{safe_channel_name(user.name)}"
        existing = discord.utils.get(guild.text_channels, name=ticket_name)

        if existing:
            return await interaction.response.send_message(
                f"❌ You already have an application ticket open: {existing.mention}",
                ephemeral=True
            )

        ticket_channel = await create_ticket_channel(
            interaction,
            ticket_name,
            f"VXPER guild application opened by {user}"
        )

        embed = discord.Embed(
            title="⚔️ VXPER Guild Application",
            description=(
                f"Welcome {user.mention} to your VXPER application ticket.\n\n"
                "Please answer these questions:\n\n"
                "• What is your username?\n"
                "• Why do you want to join VXPER?\n"
                "• How many carrots do you have?\n"
                "• Are you able to AFK consistently?\n"
                "• How active are you?\n"
                "• Anything else you'd like us to know?\n\n"
                "A staff member will review your application soon."
            ),
            color=discord.Color.blue()
        )

        await ticket_channel.send(
            content=user.mention,
            embed=embed,
            view=TicketStaffButtons()
        )

        await send_log(
            guild,
            "📝 Guild Application Opened",
            f"Applicant: {user.mention}\nTicket: {ticket_channel.mention}",
            discord.Color.blue()
        )

        await interaction.response.send_message(
            f"✅ Your VXPER application ticket has been created: {ticket_channel.mention}",
            ephemeral=True
        )


class HighRankRequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Request High Rank",
        emoji="👑",
        style=discord.ButtonStyle.primary,
        custom_id="vxper_high_rank_request"
    )
    async def request_rank(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        ticket_name = f"rank-request-{safe_channel_name(user.name)}"
        existing = discord.utils.get(guild.text_channels, name=ticket_name)

        if existing:
            return await interaction.response.send_message(
                f"❌ You already have a high rank request ticket open: {existing.mention}",
                ephemeral=True
            )

        ticket_channel = await create_ticket_channel(
            interaction,
            ticket_name,
            f"VXPER high rank request opened by {user}"
        )

        embed = discord.Embed(
            title="👑 VXPER High Rank Request",
            description=(
                f"Welcome {user.mention} to your high rank request ticket.\n\n"
                "Please answer these questions:\n\n"
                "• What is your current rank?\n"
                "• What rank are you requesting?\n"
                "• Why do you think you deserve high rank?\n"
                "• How have you helped VXPER?\n"
                "• How active are you?\n"
                "• Do you have any proof/screenshots?\n\n"
                "A staff member will review your request soon."
            ),
            color=discord.Color.gold()
        )

        await ticket_channel.send(
            content=user.mention,
            embed=embed,
            view=TicketStaffButtons()
        )

        await send_log(
            guild,
            "👑 High Rank Request Opened",
            f"Member: {user.mention}\nTicket: {ticket_channel.mention}",
            discord.Color.gold()
        )

        await interaction.response.send_message(
            f"✅ Your high rank request ticket has been created: {ticket_channel.mention}",
            ephemeral=True
        )


# =========================
# COMMANDS
# =========================

@bot.command(name="applypanel")
@commands.has_permissions(administrator=True)
async def applypanel(ctx: commands.Context):
    embed = discord.Embed(
        title="⚔️ VXPER Guild Applications",
        description=(
            "Want to join VXPER?\n\n"
            "Click the button below to open a guild application ticket.\n\n"
            "Please make sure you meet the requirements before applying:\n"
            "🥕 Carrots\n"
            "💤 Able to AFK\n"
            "🟢 Consistently active\n\n"
            "Good luck! ⚔️"
        ),
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed, view=GuildApplicationView())


@bot.command(name="rankpanel")
@commands.has_permissions(administrator=True)
async def rankpanel(ctx: commands.Context):
    embed = discord.Embed(
        title="👑 VXPER High Rank Requests",
        description=(
            "Want to request a higher rank in VXPER?\n\n"
            "Click the button below to open a high rank request ticket.\n\n"
            "Staff will review your activity, contribution, and reason for requesting high rank."
        ),
        color=discord.Color.gold()
    )

    await ctx.send(embed=embed, view=HighRankRequestView())


@applypanel.error
@rankpanel.error
async def panel_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need administrator permission to use this command.")
    else:
        await ctx.send("❌ Something went wrong while sending the panel.")
        raise error


# =========================
# EVENTS
# =========================

@bot.event
async def on_ready():
    bot.add_view(GuildApplicationView())
    bot.add_view(HighRankRequestView())
    bot.add_view(TicketStaffButtons())
    print(f"Logged in as {bot.user}")
    print("VXPER Ticket Bot is online.")


# =========================
# RUN BOT
# =========================

if not TOKEN:
    raise ValueError("Missing DISCORD_TOKEN environment variable.")

bot.run(TOKEN)

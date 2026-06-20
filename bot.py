import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

# =========================
# VXPER HARD-CODED SETTINGS
# =========================

MIN_STAFF_ROLE_ID = 1517932424414363818

APPLICATION_LOGS_CHANNEL_ID = 1517935931787706498
ACCEPTED_APPLICATIONS_CHANNEL_ID = 1517936071571411206
DENIED_APPLICATIONS_CHANNEL_ID = 1517936086473506976

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

def can_manage_application(member: discord.Member) -> bool:
    required_role = member.guild.get_role(MIN_STAFF_ROLE_ID)

    if required_role is None:
        return False

    return member.top_role.position >= required_role.position


def safe_channel_name(username: str) -> str:
    cleaned = "".join(ch for ch in username.lower() if ch.isalnum() or ch in ["-", "_"])
    return cleaned[:20] if cleaned else "user"


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


# =========================
# STAFF BUTTONS
# =========================

class ApplicationButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Accept Applicant",
        emoji="🔵",
        style=discord.ButtonStyle.success,
        custom_id="vxper_accept_applicant"
    )
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_manage_application(interaction.user):
            return await interaction.response.send_message(
                "❌ You do not have permission to use this button.",
                ephemeral=True
            )

        accepted_channel = interaction.guild.get_channel(ACCEPTED_APPLICATIONS_CHANNEL_ID)

        if accepted_channel:
            embed = discord.Embed(
                title="✅ Application Accepted",
                description=(
                    f"Applicant Ticket: {interaction.channel.mention}\n"
                    f"Reviewed By: {interaction.user.mention}\n\n"
                    "This applicant has been accepted into VXPER."
                ),
                color=discord.Color.green()
            )
            await accepted_channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Congratulations!\n\n"
            "Your application has been accepted into VXPER.\n"
            "A recruiter will contact you shortly with the next steps."
        )

        await send_log(
            interaction.guild,
            "✅ Application Accepted",
            f"Ticket: {interaction.channel.mention}\nStaff: {interaction.user.mention}",
            discord.Color.green()
        )

    @discord.ui.button(
        label="Needs Interview",
        emoji="🟡",
        style=discord.ButtonStyle.primary,
        custom_id="vxper_needs_interview"
    )
    async def interview(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_manage_application(interaction.user):
            return await interaction.response.send_message(
                "❌ You do not have permission to use this button.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🟡 Your application looks promising.\n\n"
            "We'd like to conduct a short interview before making a final decision."
        )

        await send_log(
            interaction.guild,
            "🟡 Interview Requested",
            f"Ticket: {interaction.channel.mention}\nStaff: {interaction.user.mention}",
            discord.Color.gold()
        )

    @discord.ui.button(
        label="Deny Applicant",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="vxper_deny_applicant"
    )
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_manage_application(interaction.user):
            return await interaction.response.send_message(
                "❌ You do not have permission to use this button.",
                ephemeral=True
            )

        denied_channel = interaction.guild.get_channel(DENIED_APPLICATIONS_CHANNEL_ID)

        if denied_channel:
            embed = discord.Embed(
                title="❌ Application Denied",
                description=(
                    f"Applicant Ticket: {interaction.channel.mention}\n"
                    f"Reviewed By: {interaction.user.mention}\n\n"
                    "This applicant has been denied."
                ),
                color=discord.Color.red()
            )
            await denied_channel.send(embed=embed)

        await interaction.response.send_message(
            "❌ Unfortunately your application has not been accepted at this time.\n\n"
            "Thank you for your interest in VXPER and feel free to apply again in the future."
        )

        await send_log(
            interaction.guild,
            "❌ Application Denied",
            f"Ticket: {interaction.channel.mention}\nStaff: {interaction.user.mention}",
            discord.Color.red()
        )

    @discord.ui.button(
        label="Close Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.secondary,
        custom_id="vxper_close_ticket"
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_manage_application(interaction.user):
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
        await interaction.channel.delete(reason=f"VXPER application closed by {interaction.user}")


# =========================
# APPLY VIEW
# =========================

class ApplyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Apply Now",
        emoji="📝",
        style=discord.ButtonStyle.primary,
        custom_id="vxper_apply_now"
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

        required_role = guild.get_role(MIN_STAFF_ROLE_ID)

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

        if required_role:
            overwrites[required_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        ticket_channel = await guild.create_text_channel(
            name=ticket_name,
            category=interaction.channel.category,
            overwrites=overwrites,
            reason=f"VXPER application opened by {user}"
        )

        embed = discord.Embed(
            title="⚔️ VXPER Application",
            description=(
                f"Welcome {user.mention} to your VXPER application ticket.\n\n"
                "Please tell us:\n\n"
                "• Your username\n"
                "• Why you want to join VXPER\n"
                "• Anything else you'd like us to know\n\n"
                "A recruiter will review your application as soon as possible."
            ),
            color=discord.Color.blue()
        )

        await ticket_channel.send(
            content=user.mention,
            embed=embed,
            view=ApplicationButtons()
        )

        await send_log(
            guild,
            "📝 Application Opened",
            f"Applicant: {user.mention}\nTicket: {ticket_channel.mention}",
            discord.Color.blue()
        )

        await interaction.response.send_message(
            f"✅ Your application ticket has been created: {ticket_channel.mention}",
            ephemeral=True
        )


# =========================
# COMMANDS
# =========================

@bot.command(name="panel")
@commands.has_permissions(administrator=True)
async def panel(ctx: commands.Context):
    embed = discord.Embed(
        title="⚔️ Welcome to VXPER Applications",
        description=(
            "Interested in joining VXPER?\n\n"
            "Click the button below to open an application ticket and speak with our recruitment team.\n\n"
            "Please be patient while we review your application.\n\n"
            "Good luck! ⚔️"
        ),
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed, view=ApplyView())


@panel.error
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
    bot.add_view(ApplyView())
    bot.add_view(ApplicationButtons())
    print(f"Logged in as {bot.user}")


# =========================
# RUN BOT
# =========================

if not TOKEN:
    raise ValueError("Missing DISCORD_TOKEN environment variable.")

bot.run(TOKEN)

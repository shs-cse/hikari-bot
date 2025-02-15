import hikari.errors
import sys, warnings, miru
import hikari, crescent
from bot_variables import state
from bot_variables.config import FileName, InfoField
from wrappers.utils import FormatText
from setup_validation.json_inputs import check_and_load_info


def main():
    # check if `-d` flag was used `python -dO main.py`
    state.is_debug = "d" in sys.orig_argv[1]
    # ignore pygsheets warnings in normal mode
    if not state.is_debug:
        warnings.simplefilter("ignore")
    # validate and update state.info
    check_and_load_info()
    # hikari + crescent -> create bot and client
    bot = hikari.GatewayBot(
        state.info[InfoField.BOT_TOKEN],
        intents=hikari.Intents.ALL,
        logs="INFO" if state.is_debug else "WARNING",
    )
    this_guild_id = int(state.info[InfoField.GUILD_ID])
    client = crescent.Client(bot, default_guild=this_guild_id)
    # load commands and pluins
    client.plugins.load_folder(FileName.EVENTS_FOLDER)
    client.plugins.load_folder(FileName.COMMANDS_FOLDER)
    if not state.is_debug:  # remove bulk delete from commands folder
        client.plugins.unload(FileName.BULK_DELETE)
    client.plugins.load(FileName.DISCORD_WRAPPER)
    client.plugins.load(FileName.DISCORD_SECTION_VALIDATION)
    # initialize miru for managing buttons and forms
    state.miru_client = miru.Client(bot)
    # run the bot
    try:
        bot.run(
            # enable asyncio debug to detect blocking and slow code.
            asyncio_debug=state.is_debug,
            # enable coroutine tracking, makes some asyncio errors clearer.
            coroutine_tracking_depth=20 if state.is_debug else None,
            # initial discord status of the bot
            status=hikari.Status.IDLE,
        )
    except hikari.errors.UnauthorizedError as auth_error:
        msg = FormatText.error(
            f"Bot authorization failed."
            + f" Please check {FileName.INFO_JSON} > '{InfoField.BOT_TOKEN}'"
        )
        raise Exception(msg) from auth_error


if __name__ == "__main__":
    main()

import sys
import glob
import importlib
from pathlib import Path
from pyrogram import idle
import logging
import logging.config
import time  
import asyncio
import pytz
from datetime import date, datetime
from aiohttp import web

# Import necessary modules from your project
from pyrogram import Client, version
from pyrogram.raw.all import layer
from database.ia_filterdb import Media, Media2, tempDict, choose_mediaDB, db as clientDB
from database.users_chats_db import db
from info import *
from utils import temp
from Script import script 
from plugins import web_server, check_expired_premium
from Deendayal_botz import DeendayalBot
from util.keepalive import ping_server
from Deendayal_botz.clients import initialize_clients

# Configure logging
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

botStartTime = time.time()

# Load plugin files dynamically
ppath = "plugins/*.py"
files = glob.glob(ppath)

async def Deendayal_start():
    print('\nInitializing Deendayal Dhakad Bot')

    # Start the bot and get bot information
    await DeendayalBot.start()  # Await the start method
    bot_info = await DeendayalBot.get_me()
    DeendayalBot.username = bot_info.username
    
    # Initialize clients
    await initialize_clients()
    
    # Import plugins dynamically
    for name in files:
        with open(name) as a:
            patt = Path(a.name)
            plugin_name = patt.stem.replace(".py", "")
            plugins_dir = Path(f"plugins/{plugin_name}.py")
            import_path = f"plugins.{plugin_name}"
            spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
            load = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(load)
            sys.modules["plugins." + plugin_name] = load
            print(f"Deendayal Dhakad Imported => {plugin_name}")

    # Ping server if on Heroku
    if ON_HEROKU:
        asyncio.create_task(ping_server())

    # Retrieve banned users and chats
    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats

    # Ensure indexes for Media collections
    await Media.ensure_indexes()
    await Media2.ensure_indexes()

    # Check database stats and manage database usage based on available space
    stats = await clientDB.command('dbStats')
    free_dbSize = round(512 - ((stats['dataSize'] / (1024 * 1024)) + (stats['indexSize'] / (1024 * 1024))), 2)
    
    if DATABASE_URI2 and free_dbSize < 62:
        tempDict["indexDB"] = DATABASE_URI2
        logging.info(f"Primary DB has only {free_dbSize} MB left; using Secondary DB for storage.")
    elif DATABASE_URI2 is None:
        logging.error("Missing second DB URI! Add SECONDDB_URI now! Exiting...")
        exit()
    else:
        logging.info(f"Primary DB has enough space ({free_dbSize} MB) left; using it for storage.")

    # Choose media database and get bot user details
    await choose_mediaDB()   
    me = await DeendayalBot.get_me()
    
    # Store bot user details in temp
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    temp.B_LINK = me.mention
    
    # Set bot username for later use
    DeendayalBot.username = '@' + me.username
    
    # Start the task to check expired premium users
    DeendayalBot.loop.create_task(check_expired_premium(DeendayalBot))

    # Log startup information
    logging.info(f"{me.first_name} with Pyrogram v{version} (Layer {layer}) started on {me.username}.")
    logging.info(LOG_STR)
    logging.info(script.LOGO)

    # Send restart message to the log channel with timestamp
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    time_str = now.strftime("%H:%M:%S %p")
    
    await DeendayalBot.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(temp.B_LINK, today, time_str))
    
    # Set up the web server application runner
    app = web.AppRunner(await web_server())

# Entry point for running the bot asynchronously
if name == 'main':
    try:
        asyncio.run(Deendayal_start())  # Use asyncio.run to start the async function directly.
        idle()  # Keep the bot running until interrupted
    except KeyboardInterrupt:
        logging.info('Service Stopped Bye 👋')

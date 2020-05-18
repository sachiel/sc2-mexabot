#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages about SARS-CoV-2

First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import os
import json
import logging

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

IBM_APIKEY = os.getenv('IBM_APIKEY')
IBM_URL  = os.getenv('IBM_URL')
IBM_ASSISTANTID = os.getenv('IBM_ASSISTANT_ID')


if not IBM_APIKEY or not IBM_URL:
    raise ValueError('IBM Auth or URL not defined')

if not IBM_ASSISTANTID:
    raise ValueError('Not Assistant ID defined')

ibm_authenticator = IAMAuthenticator(IBM_APIKEY)
ibm_assistant = AssistantV2(
        version='2020-04-01',
        authenticator = ibm_authenticator
)

ibm_assistant.set_service_url(IBM_URL)

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    message = (
        "Hola!, soy un bot y mi proposito es darte "
        "la información que necesitas "
        "sobre el COVID19, puedes preguntarme todo "
        "lo que quieras."
    )
    update.message.reply_text(message)


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


# Bot Communication
def botcomm(update, context):
    """Process with IBM WATSON the user message."""
    # unactive session last 5 min, ToDo: management sessions per 
    # telegram chatid
    session_response = ibm_assistant.create_session(
        assistant_id=IBM_ASSISTANTID
    ).get_result()

    if 'session_id' in session_response and session_response['session_id']:
        session_id = session_response['session_id']
    else:
        session_id = None

    if session_id:
        # send message
        message_response = ibm_assistant.message(
            assistant_id=IBM_ASSISTANTID,
            session_id=session_id,
            input={
                'message_type': 'text',
                'text': update.message.text
            }
        ).get_result()

        if 'output' in message_response and 'generic' in message_response['output']:
            output_generic = message_response['output']['generic']
            response = None

            if len(output_generic) > 0:
                first_output_generic = output_generic[0]
                if 'text' in first_output_generic and first_output_generic['text']:
                    response = first_output_generic['text']

            if response:
                update.message.reply_text(response)
            else:
                update.message.reply_text("Malformed WATSON message response. ECHO ".format(update.message.text))
        else:
            update.message.reply_text("Message Error. ECHO ".format(update.message.text))
    else:
        update.message.reply_text("Session Error. ECHO ".format(update.message.text))

    # destroy watson session? keep alive temporaly


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot."""
    # First, setup variables
    TLGM_APIKEY = os.getenv('TELEGRAM_APIKEY')

    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary

    if TLGM_APIKEY:
        updater = Updater(TLGM_APIKEY, use_context=True)

        # Get the dispatcher to register handlers
        dp = updater.dispatcher

        # on different commands - answer in Telegram
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", help))

        # on noncommand i.e message - Use Watson to process and response message on Telegram
        dp.add_handler(MessageHandler(Filters.text, botcomm))

        # log all errors
        dp.add_error_handler(error)

        # Start the Bot
        updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        updater.idle()
    else:
        raise ValueError("You must set a env variable called TELEGRAM_APIKEY")


if __name__ == '__main__':
    main()


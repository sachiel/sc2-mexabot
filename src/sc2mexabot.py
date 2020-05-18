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
import requests

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

    update.message.reply_text('Prueba tambien los comandos:')
    update.message.reply_text('/hospitales')
    update.message.reply_text('/capacidad')
    update.message.reply_text('/conteo')


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Prueba con:')
    update.message.reply_text('/hospitales')
    update.message.reply_text('/capacidad')
    update.message.reply_text('/conteo')


def conteo(update, context):
    endpoint_url = "https://api.covid19api.com/country/mexico"
    r = requests.get(endpoint_url)
    error = False
    text = ""

    if r.status_code == 200:
        data = r.json()
        if data and len(data) > 0:
            record = data[-1]  # only last item
            text = "Confirmados: {}. Fallecidos: {}. Recuperados: {}. Activos: {}. {}. Todo México.".format(
                record['Confirmed'],
                record['Deaths'],
                record['Recovered'],
                record['Active'],
                record['Date'],
            )

            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        else:
            error = True
            text = "Error obteniendo dataset"
    else:
        error = True
        text = "Error en consulta a API de api.covid19api.com"

    if error:
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def hospitales(update, context):
    hospitals_url = "https://datos.cdmx.gob.mx/api/records/1.0/search/?dataset=hospitales-covid-19&q=&facet=tipo&facet=abreviatura&facet=categoria&facet=entidad"
    r = requests.get(hospitals_url)
    error = False
    text = ""

    if r.status_code == 200:
        data = r.json()
        if 'records' in data and data['records']:
            for record in data['records']:
                text = "{}, {}, {}, {}.".format(
                    record['fields']['nombre_del_hospital'],
                    record['fields']['entidad'],
                    record['fields']['categoria'],
                    record['fields']['tipo'],
                )

                if 'coordenadas' in record['fields'] and len(record['fields']['coordenadas']) > 1:
                    point = record['fields']['coordenadas']
                    text = "{} https://maps.google.com/?q={},{}".format(text, point[0], point[1])

                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        else:
            error = True
            text = "Error obteniendo dataset de hospitales"
    else:
        error = True
        text = "Error en consulta a API de datos.cdmx.gob.mx"

    if error:
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def capacidad_hospitalaria(update, context):
    hospitals_url = "https://datos.cdmx.gob.mx/api/records/1.0/search/?dataset=capacidad-hospitalaria&q=&facet=fecha&facet=nombre_hospital&facet=institucion&facet=estatus_capacidad_hospitalaria&facet=estatus_capacidad_uci"
    r = requests.get(hospitals_url)
    error = False
    text = ""

    if r.status_code == 200:
        data = r.json()
        if 'records' in data and data['records']:
            for record in data['records']:
                text = "{}, {}. Capacidad: {}".format(
                    record['fields']['institucion'],
                    record['fields']['nombre_hospital'],
                    record['fields']['estatus_capacidad_hospitalaria'],
                )
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        else:
            error = True
            text = "Error obteniendo dataset de hospitales"
    else:
        error = True
        text = "Error en consulta a API de datos.cdmx.gob.mx"

    if error:
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)


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
        dp.add_handler(CommandHandler("hospitales", hospitales))
        dp.add_handler(CommandHandler("capacidad", capacidad_hospitalaria))
        dp.add_handler(CommandHandler("conteo", conteo))

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


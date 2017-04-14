#!/usr/bin/python

# Note: for setting up email with sendmail, see: http://linuxconfig.org/configuring-gmail-as-sendmail-email-relay

import argparse
import commands
import json
import logging
import smtplib
import sys

from datetime import datetime
from os import path
from subprocess import check_output


EMAIL_TEMPLATE = """
<p>There are class sessions available:</p>
<p>%s</p>
"""


def notify_send_email(settings, avail_classes, use_gmail=False):
    sender = settings.get('email_from')
    recipient = settings.get('email_to', sender)  # If recipient isn't provided, send to self.
    password = settings.get('gmail_password')
    avail_classes = avail_classes.replace('\n', '<br/>')

    if not password and use_gmail:
        print 'Trying to send from gmail, but password was not provided.'
        return

    try:
        if use_gmail:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender, password)
        else:
            server = smtplib.SMTP('localhost', 25)

        subject = "Alert: New La Petite Baleen Class Sessions Available"
        headers = "\r\n".join(["from: %s" % sender,
                               "subject: %s" % subject,
                               "to: %s" % recipient,
                               "mime-version: 1.0",
                               "content-type: text/html"])
        message = EMAIL_TEMPLATE % (avail_classes)
        content = headers + "\r\n\r\n" + message

        server.sendmail(sender, recipient, content)
        server.quit()
    except Exception:
        logging.exception('Failed to send succcess e-mail.')


def notify_osx(msg):
    commands.getstatusoutput("osascript -e 'display notification \"%s\" with title \"La Petite Baleen Notifier\"'" % msg)


def main(settings):
    try:
        # Run the phantom JS script - output will be formatted like 'July 20, 2015'
        # script_output = check_output(['phantomjs', '%s/ge-cancellation-checker.phantom.js' % pwd]).strip()
        script_output = check_output(['phantomjs', '%s/lapetite-checker.js' % pwd]).strip()

        if len(script_output) == 0:
            logging.info('No classes available.')
            return

        classes = script_output
    except OSError:
        logging.critical("Something went wrong when trying to run ge-cancellation-checker.phantom.js. Is phantomjs is installed?")
        return

    msg = 'Found new appointments: %s' % classes
    logging.info(msg + (' Sending email.' if not settings.get('no_email') else ' Not sending email.'))

    if settings.get('notify_osx'):
        notify_osx(msg)
    if not settings.get('no_email'):
        notify_send_email(settings, classes, use_gmail=settings.get('use_gmail'))

def _check_settings(config):
    required_settings = (
        'location',
        'earliestTime',
        'latestTime'
    )

    for setting in required_settings:
        if not config.get(setting):
            raise ValueError('Missing setting %s in config.json file.' % setting)

    if config.get('no_email') == False and not config.get('email_from'): # email_to is not required; will default to email_from if not set
        raise ValueError('email_to and email_from required for sending email. (Run with --no-email or no_email=True to disable email.)')

    if config.get('use_gmail') and not config.get('gmail_password'):
        raise ValueError('gmail_password not found in config but is required when running with use_gmail option')

if __name__ == '__main__':

    # Configure Basic Logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        stream=sys.stdout,
    )

    pwd = path.dirname(sys.argv[0])

    # Parse Arguments
    parser = argparse.ArgumentParser(description="Command line script to check for La Petite Baleen time slots.")
    parser.add_argument('--no-email', action='store_true', dest='no_email', default=False, help='Don\'t send an e-mail when the script runs.')
    parser.add_argument('--use-gmail', action='store_true', dest='use_gmail', default=False, help='Use the gmail SMTP server instead of sendmail.')
    parser.add_argument('--notify-osx', action='store_true', dest='notify_osx', default=False, help='If better date is found, notify on the osx desktop.')
    parser.add_argument('--config', dest='configfile', default='%s/config.json' % pwd, help='Config file to use (default is config.json)')
    arguments = vars(parser.parse_args())

    # Load Settings
    try:
        with open(arguments['configfile']) as json_file:
            settings = json.load(json_file)

            # merge args into settings IF they're True
            for key, val in arguments.iteritems():
                if not arguments.get(key): continue
                settings[key] = val

            _check_settings(settings)
    except Exception as e:
        logging.error('Error loading settings from config.json file: %s' % e)
        sys.exit()

    # Configure File Logging
    if settings.get('logfile'):
        handler = logging.FileHandler('%s/%s' % (pwd, settings.get('logfile')))
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        handler.setLevel(logging.DEBUG)
        logging.getLogger('').addHandler(handler)

    logging.debug('Running cron with arguments: %s' % arguments)

    main(settings)

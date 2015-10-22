# Imports
#############################################################################

import os
import sys
import base64
import urllib
import urllib2
import traceback


# Import aliases
#############################################################################

from xmlrpclib import ServerProxy


# Constants
#############################################################################

PROCESS_SUCCESS=93
PROCESS_ERROR=94
PROCESS_NONE=95


# Logging
#############################################################################

def log_detail(message):
    log_write('DETAIL', message)


def log_error(message):
    log_write('ERROR', message)


def log_info(message):
    log_write('INFO', message)


def log_warning(message):
    log_write('WARNING', message)


def log_write(type, message):
    print '[%s] %s' % (type, message)


# API
#############################################################################

def command(url_command):
    url = 'http://%s:%s/jsonrpc/%s' % (NZBGET_HOST, NZBGET_PORT, url_command)
    log_detail('Command: %s.' % url)

    auth = '%s:%s' % (NZBGET_USERNAME, NZBGET_PASSWORD)
    auth_token = base64.encodestring(auth).replace('\n', '')

    request = urllib2.Request(url)
    request.add_header('Authorization', 'Basic %s' % auth_token)

    response = urllib2.urlopen(request)

    return response.read()


def proxy():
    # Make sure we encode the username and password since it will be used in
    # the url we create.
    username = urllib.quote(NZBGET_USERNAME, safe='')
    password = urllib.quote(NZBGET_PASSWORD, safe='')
    url = 'http://%s:%s@%s:%s/xmlrpc' % (username, password, NZBGET_HOST, NZBGET_PORT)

    log_detail('Proxy: %s.' % url)

    return ServerProxy(url)


# Script checking
#############################################################################

def check_nzb_environment():
    """
    Check if the script is called from a compatible NZBGet version
    (as queue-script or as pp-script)
    """
    ArticleCacheDefined = 'NZBOP_ARTICLECACHE' in os.environ
    DirectoryDefined = 'NZBPP_DIRECTORY' in os.environ
    EventDefined = 'NZBNA_EVENT' in os.environ

    # TODO: This seems like a kind of retarded conditional.
    if not (DirectoryDefined or EventDefined) or not ArticleCacheDefined:
        print('[ERROR] *** NZBGet queue script ***')
        print('[ERROR] This script is supposed to be called from nzbget (14.0 or later).')
        sys.exit(PROCESS_FAIL_ENVIRONMENT)


def check_nzb_status():
    """
    If nzb was already marked as bad, don't do any further detection.
    """
    if os.environ.get('NZBPP_STATUS') == 'FAILURE/BAD':
        if os.environ.get('NZBPR_PPSTATUS_ARCHIVE_IGNORE') == 'yes':
            # Print the message again during post-processing to ad it into the
            # post-processing log (which is then used by notification scripts).
            print('[WARNING] Download has ignored files.')
        clean_up()
        sys.exit(PROCESS_SUCCESS)


def check_nzb_reprocess():
    """
    If nzb was reprocessed via the "Post-process again" action, the
    download might not exist anymore.
    """
    DirectoryDefined = 'NZBPP_DIRECTORY' in os.environ
    DirectoryExists = os.path.exists(os.environ.get('NZBPP_DIRECTORY'))
    if DirectoryDefined and not DirectoryExists:
        print('[WARNING] Destination directory does not exist.')
        clean_up()
        sys.exit(PROCESS_NONE)


def check_nzb_failed():
    """
    If nzb is already failed, don't do any further actions.
    """
    if os.environ.get('NZBPP_TOTALSTATUS') == 'FAILURE':
        clean_up()
        sys.exit(PROCESS_NONE)


# Event helpers
#############################################################################

def is_downloaded():
    """
    Checks to see if the nzb file is still downloading or has finished.
    """
    return os.environ.get('NZBNA_EVENT') == 'FILE_DOWNLOADED'


# Helpers
#############################################################################

def get_nzb_category():
    prefix = get_nzb_prefix()
    return os.environ[prefix + 'CATEGORY']


def get_nzb_directory():
    prefix = get_nzb_prefix()
    return os.environ[prefix + 'DIRECTORY']


def get_nzb_directory_final():
    prefix = get_nzb_prefix()
    return os.environ[prefix + 'FINALDIR']


def get_nzb_id():
    prefix = get_nzb_prefix()
    return os.environ[prefix + 'NZBID']


def get_nzb_name():
    prefix = get_nzb_prefix()
    return os.environ[prefix + 'NZBNAME']


def get_nzb_prefix():
    """
    Depending on the mode in which the script was called (queue-script
    or post-processing-script) a different set of parameters (env. vars)
    is passed. They also have different prefixes:
      - NZBNA_ in queue-script mode;
      - NZBPP_ in pp-script mode.
    """
    return 'NZBNA_' if 'NZBNA_EVENT' in os.environ else 'NZBPP_'


def get_nzb_status():
    prefix = get_nzb_prefix()
    return os.environ[prefix + 'STATUS']


def get_nzb_status_total():
    prefix = get_nzb_prefix()
    return os.environ[prefix + 'TOTALSTATUS']


def get_script_option(name):
    return os.environ.get('NZBPR_' + name)


def set_script_option(name, value):
    print '[NZB] NZBPR_%s=%s' % (name, value)

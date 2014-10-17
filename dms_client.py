#!/usr/bin/env python
"""
Module: Adlibre DMS File Upload Client
Project: Adlibre DMS File Upload Client
Copyright: Adlibre Pty Ltd 2012
License: See LICENSE for license information
"""

import urllib2
import os
import sys
import json
import mimetools
import mimetypes
import itertools
import ConfigParser
import datetime

__version__ = '0.7.3'

PROJECT_PATH = os.path.abspath(os.path.split(sys.argv[0])[0])
DEFAULT_CFG_FILE = 'dms_client.cfg'
DEFAULT_CFG_CHAPTER = 'main'
DEFAULT_CFG_OPTIONS = [
    'user',
    'pass',
    'host',
    'url',
    'directory',
    'mimetype',
    'files_type',
    'user_agent',
    'remove',
    'API_FILEINFO_LOCATION'
]
DEFAULT_API_LOCATION = 'api/file/'
DEFAULT_USER_AGENT = 'Adlibre DMS API file uploader version: %s' % __version__
DEFAULT_FILE_TYPE = 'pdf'
DEFAULT_MIMETYPE = 'application/pdf'
ERROR_FILE_PREFIX = '.error'
ERROR_FILE_MAIN = 'error.txt'
LOG_FILE_MAIN = 'dms_client.log'
DEFAULT_ERROR_MESSAGES = {
    'no_host': 'You should provide host to connect to. Please refer to help, running with -help',
    'no_config_or_console': 'Nothing to do. you should provide config and/or console parameters. Exiting.',
    'no_url': 'You should not provide an empty url',
    'no_mimetype': 'You should not provide an empty mimetype. Try to run with -h for help.',
    'no_data': 'You have missed data to be sent. Please provide -dir or -f to be sent into API. Refer to -h for help.',
    'no_username': 'You should provide username. Using config or -user param. Refer to -h for help.',
    'no_password': 'You should provide password. Using config or -pass param. Refer to -h for help.',
    'no_filetype': 'You must configure and/or provide extension of files to scan in the directory you have provided.',
    'no_proper_data': 'You have provided a directory instead of a file,\n' +
                      'reverse or target file/directory does not exist.\n' +
                      'Please recheck location in your config. Refer to -h for help.',
    'no_file': 'File does not exist.'
}

help_text = """
Command line Adlibre DMS file uploader utility.
Version """ + __version__ + """

Uploads file/directory into Adlibre DMS Api,
depending on options/config specified.

In order to function it must have configuration file,
usually called '""" + DEFAULT_CFG_FILE + """'.
You may override those settings by specifying
alternative configuration file with '-config' key parameter.

Available options:
(Config file options are marked in [] and are equivalent)

    -config
        alternative configuration file you must specify
        in your system absolute path,
        or simply it's filename in case it lays in this program directory.
        e.g. '-config myconfig.cfg'
        will try to load your alternative configuration file
        called 'myconfig.cfg' that lays in the program path.
        e.g. '-config C:\mydir\congigfile.cfg'
        will try to load file 'configfile.cfg' in your 'C:\mydir\'
    -chapter
        alternative configuration file chapter
        usually marked with [] scopes.
        e.g. [my-dms] is marking the section 'my-dms'
        in config and can be handled separately.
        you must call this section specifying it's
        name directly after parameters.
        e.g. '-chapter my-dms'
        This way you can call this to upload into
        any Adlibre DMS instance API,
        with only specifying it's section name in same configuration file.
    -s
        Silence option.
        Makes your program output nothing into console whatever happens.
        THis does not affect creating/outputting of error files in any way.
    -f
        Filename to upload.
        In case of this option set properly
        program uploads only this file and quits.
        you should pecify it with file name and path,
        e.g. '-f C:\some\path\myfile.pdf'
        or unix ver:
        e.g. '-f ../somedir/file.pdf
    -remove
    [remove=yes]
        Delete original files after successful send
        and receiving '200 OK' response from server.
    -dir
    [directory=C:\somepath\in\system\]] in config
        Directory to scan files into.
        Scans and sends into API all files,
        in case of this is specified and option -f (single file) not provided
        Can be relative and/or full path to the directory to scan files into.
        e.g.(for windows): C:\scan\documents\adlibre\

        e.g.(for unix): ../../somedir/files/lie/into/
    -user
    [user=your_user_name] in config
        DMS Username to access API
    -pass
    [pass=your_password] in config
        DMS Password to access API
    -host
    [host=http://.....] in config
        host of the api
    -url
    [url=api/file/] in config
        Your Adlibre DMS API location to connect to.
        Default is set to 'api/file/'
        Note you must specify it without the first
        '/' symbol in order to build the upload url normally.
    -fileinfo_location
    [API_FILEINFO_LOCATION=api/revision_count/] in config
        Adlibre DMS API location to get file revisions count.
        This option set and configured properly provides support of uncategorized file code into API.
        It stores file names of API returned uncetegorized code into the log file and warns user accordingly.
    -ft
    [file_type=pdf] in config
        Files type to scan for/suggest to API.
        Default is set to 'pdf'
        This needs to be set up if you have provided a -dir setting.
        (In order to know files to scan in provided directory)
    -mimetype
    [mimetype=application/pdf] in config
        mimetype of file to be sent. Default is: application/pdf

Note: Console commands are for overriding config settings.
e.g. In case you will run '""" + sys.argv[0] + """ -f somefile.pdf'
it will assume you want to send one file,
you have provided and ignore directory setting at config,
even with provided -config and/or -chapter setting.
"""


###########################################################################################
############################## MULTIPART FORM EMULATOR ####################################
###########################################################################################
class MultiPartForm(object):
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = mimetools.choose_boundary()
        return

    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, field_name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((field_name, value))
        return

    def add_file(self, field_name, file_name, file_handle, current_mimetype=None):
        """Add a file to be uploaded."""
        body = file_handle.read()
        if current_mimetype is None:
            current_mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((field_name, file_name, current_mimetype, body))
        return

    def __str__(self):
        """Return a string representing the form data, including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.
        parts = []
        part_boundary = '--' + self.boundary

        # Add the form fields
        parts.extend(
            [
                part_boundary,
                'Content-Disposition: form-data; name="%s"' % n,
                '',
                value,
            ] for n, value in self.form_fields
        )

        # Add the files to upload
        parts.extend(
            [
                part_boundary,
                'Content-Disposition: file; name="%s"; filename="%s"' % (field_name, file_name),
                'Content-Type: %s' % content_type,
                '',
                body,
            ] for field_name, file_name, content_type, body in self.files
        )

        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)


def check_file_uploaded(file_place, opts, opener):
    """Checking if file revision for uploaded code is greater then 0"""
    original_code = False
    original_filename = get_full_filename(file_place)
    if "." in original_filename:
        original_code, file_extension = os.path.splitext(original_filename)
    file_name = opts['uploaded_code']
    code = file_name
    if "." in file_name:
        code, file_extension = os.path.splitext(file_name)
    if code != original_code:
        msg = 'WARNING! File stored as uncategorized file code: %s for file:' % file_name
        if not opts['silent']:
            print msg + ' %s' % original_filename
        write_successlog(original_filename, msg)
    full_url = opts['host'] + opts['fileinfo_loc'] + code + '?only_metadata=true'
    request = urllib2.Request(full_url)
    response = opener.open(request)
    opener.close()
    if response:
        if response.code == 200:
            file_info = response.fp.read()
            revisions_count = int(file_info)
            if revisions_count > 0:
                return True
        else:
            return False
    return False


def upload_file(file_place, opt):
    """Main uploader function"""
    silent_ = opt['silent']

    # Creating Auth Opener
    # create a password manager
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    # Add the username and password.
    # If we knew the realm, we could use it instead of ``None``.
    password_mgr.add_password(None, opt['host'], opt['username'], opt['password'])
    handler = urllib2.HTTPBasicAuthHandler(password_mgr)
    # create "opener" (OpenerDirector instance)
    opener = urllib2.build_opener(handler)
    # Install the opener.
    # Now all calls to urllib2.urlopen use our opener.
    urllib2.install_opener(opener)

    # File upload
    # Opening file for operations
    work_file = open(file_place, "rb")
    # Initializing the form
    form = MultiPartForm()

    # Extracting filename
    file_name = get_full_filename(file_place)

    # Adding our file to form
    form.add_file('file', file_name, file_handle=work_file, current_mimetype=opt['mimetype'])

    # Build the request
    full_url = opt['url'] + file_name
    request = urllib2.Request(full_url)
    request.add_header('User-agent', opt['user_agent'])
    body = str(form)
    request.add_header('Content-type', form.get_content_type())
    request.add_header('Content-length', len(body))
    request.add_data(body)

    if not silent_:
        print 'SENDING FILE: %s' % file_place
    response = None
    try:
        response = opener.open(request)
        opener.close()
        work_file.close()
    # Usecases when connection with this URL is not established and URL is wrong
    except (urllib2.HTTPError, urllib2.URLError), e:
        if not silent_:
            print 'SERVER RESPONSE: %s' % e
            print 'Writing Error file'
        raise_error("%s : %s""" % (file_place, e))
        pass
    if response:
        if not silent_:
            print 'SERVER RESPONSE: OK'
        if response.code == 200:
            if opt['fileinfo_loc']:
                opt['uploaded_code'] = json.loads(response.fp.read())
                result = check_file_uploaded(file_place, opt, opener)
                if not result:
                    raise_error('File uploaded check failed %s' % file_name)
                    return False
            write_successlog(file_name)
            if opt['remove']:
                remove_file(file_place)


def get_full_filename(full_name):
    """Extracts only filename from full path"""
    result_name = full_name
    if os.sep or os.pardir in full_name:
        result_name = os.path.split(full_name)[1]
    return result_name


def getopts(argv):
    """Gets options from sys.argv and transfers them into handy dictionary"""
    opts = {}
    while argv:
        if argv[0][0] == '-':               # find "-name value" pairs
            try:
                # Getting value of this option
                if argv[1][0] == '-':  # Next option is an argv
                    opts[argv[0]] = ''
                    argv = argv[1:]
                else:
                    opts[argv[0]] = argv[1]     # dict key is "-name" arg
                    argv = argv[2:]
            except IndexError:
                # option has no argv left in the end
                opts[argv[0]] = None
                argv = argv[1:]
        else:
            argv = argv[1:]
    return opts


def parse_config(cfg_file_name=None, config_chapter=False, _silent=False):
    """Parses specified config file or uses system set."""

    def get_option(opt_config, opt, config_opts):
        # looks for option and appends it to options dictionary
        try:
            try:
                opt_value = opt_config.get(config_chapter or DEFAULT_CFG_CHAPTER, opt)
                config_opts[option] = opt_value
            except ConfigParser.NoOptionError:
                pass
        except ConfigParser.NoSectionError, err:
            if not _silent:
                print 'Config file Error:', err
            raise_error(err)

    config_instance = None
    # Getting conf file defined
    if cfg_file_name:
        config_file = cfg_file_name
    else:
        config_file = DEFAULT_CFG_FILE
    # Trying to open file and getting default config if failed.
    try:
        config_instance = open(os.path.join(PROJECT_PATH, config_file), "rb")

    except IOError, e:
        if not _silent:
            print e
            print 'Trying to read standard config file: ./' + DEFAULT_CFG_FILE
        # Trying to get config from default file if exists
        try:
            config_instance = open(DEFAULT_CFG_FILE, "rb")
        except IOError, e:
            if not _silent:
                print e
                print 'Not found standard config. can now function only with console params'
        pass

    if not config_instance:
        if not _silent:
            print 'config used ......................................................no'
        return None
    # Warning! allow_no_value may cause bugs in Python < 2.7
    cfg = ConfigParser.RawConfigParser()  # allow_no_value=True)
    cfg.readfp(config_instance)

    config_options = {}
    for option in DEFAULT_CFG_OPTIONS:
        get_option(cfg, option, config_options)

    if not _silent:
        print 'config used ......................................................yes'
    return config_options


def raise_error(message=None, error_level=1):
    """Breaks program with error, message provided.

    Writes down error text to file."""
    if message:
        if os.path.isfile(ERROR_FILE_MAIN):
            err_file = open(ERROR_FILE_MAIN, 'a')
        else:
            err_file = open(ERROR_FILE_MAIN, 'w')
            err_file.seek(0)

        err_file.write('\n-----------------------------------------------------------------------------\n')
        err_file.write(str(datetime.datetime.now())+'\n')
        err_file.write('-----------------------------------------------------------------------------\n')
        err_file.write(str(message))
        err_file.close()
        write_successlog('Error!', message=message)
    print message
    sys.exit(error_level)


def write_successlog(file_name, message=''):
    """Writes down action of succeeded sending."""
    if os.path.isfile(LOG_FILE_MAIN):
        log_file = open(LOG_FILE_MAIN, 'a')
    else:
        log_file = open(LOG_FILE_MAIN, 'w')
        log_file.seek(0)
    log_file.write('\n-----------------------------------------------------------------------------\n')
    log_file.write(str(datetime.datetime.now())+'\n')
    log_file.write('-----------------------------------------------------------------------------\n')
    if message:
        log_file.write(message + u' ' + unicode(file_name))
    else:
        log_file.write('UPLOAD SUCCESSFUL of file: %s' % str(file_name))
    log_file.close()


def walk_directory(rootdir, f_type=None):
    """Walks through directory with files of provided format and

    returns the list of their name with path (ready to open) or empty list."""
    file_list = []
    for root, subFolders, files in os.walk(rootdir):
        for f in files:
            if f_type:
                if '.' in f:
                    if os.path.splitext(f)[1] == ('.' + str(f_type)):
                        file_list.append(os.path.join(root, f))
            else:
                file_list.append(os.path.join(root, f))
    return file_list


def remove_file(file_path):
    """Deletes file with path specified from filesystem"""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            write_successlog(file_path, ' Success removing file:')
        except Exception, e:
            raise_error("%s : %s""" % (file_path, e))
    else:
        raise_error(DEFAULT_ERROR_MESSAGES['no_file'] + ': ' + file_path)


###########################################################################################
##################################### MAIN FUNCTION #######################################
###########################################################################################
if __name__ == '__main__':
    print 'dms-client v%s' % __version__

    app_args = getopts(sys.argv)

    silent = False
    if '-s' in app_args:
        silent = True

    cfg_chapter = False
    if '-chapter' in app_args:
        cfg_chapter = app_args['-chapter']

    config_file_name = False
    if '-config' in app_args:
        config_file_name = app_args['-config']

    filename = None
    if '-f' in app_args:
        filename = app_args['-f']

    if ('-h' or '-help') in app_args.iterkeys():
        print help_text
        if not silent:
            raw_input("Press Enter to exit...")
            sys.exit(0)

    config = parse_config(cfg_file_name=config_file_name, config_chapter=cfg_chapter, _silent=silent)

    if not app_args and not config:
        if not silent:
            raise_error(DEFAULT_ERROR_MESSAGES['no_config_or_console'])

    # Getting option from sys.argv first then trying config file
    username = ''
    if '-user' in app_args:
        username = app_args['-user']
    if not username:
        if 'user' in config:
            username = config['user']

    password = ''
    if '-pass' in app_args:
        password = app_args['-pass']
    if not password:
        if 'pass' in config:
            password = config['pass']

    # Setting/Reading and debugging HOST + URL combinations.
    host = ''
    if '-host' in app_args:
        host = app_args['-host']
    if not host:
        if 'host' in config:
            host = config['host']

    url = host + DEFAULT_API_LOCATION
    if '-url' in app_args:
        url = host + app_args['-url']
    if not url:
        if 'url' in config:
            url = host + config['url']
    if url == DEFAULT_API_LOCATION:
        raise_error(DEFAULT_ERROR_MESSAGES['no_host'])
    if url == host:
        if not silent:
            print 'Warning!:'
            print (DEFAULT_ERROR_MESSAGES['no_url'])
        url = host + DEFAULT_API_LOCATION
        if not silent:
            print 'Api url forced set to default: %s' % url

    # Reading file operational settings
    file_type = DEFAULT_FILE_TYPE
    if '-ft' in app_args:
        file_type = app_args['-ft']
    if not host:
        if 'file_type' in config:
            file_type = config['file_type']
    if not silent:
        print 'Uploading files of type: %s' % file_type

    mimetype = DEFAULT_MIMETYPE
    if '-mimetype' in app_args:
        mimetype = app_args['-mimetype']
    if not mimetype:
        if 'mimetype' in config:
            mimetype = config['mimetype']
    if not silent:
        print 'Using Mimetype: %s' % mimetype

    fileinfo_loc = None
    if '-fileinfo_location' in app_args:
        fileinfo_loc = app_args['-fileinfo_location']
    if not fileinfo_loc:
        if 'API_FILEINFO_LOCATION' in config:
            fileinfo_loc = config['API_FILEINFO_LOCATION']
    if not silent:
        print 'Using API FILEINFO URL: %s' % fileinfo_loc

    directory = ''
    if '-dir' in app_args:
        directory = app_args['-dir']
    if not directory:
        if 'directory' in config:
            directory = config['directory']
    if (not directory) and (not filename):
        if not silent:
            raise_error(DEFAULT_ERROR_MESSAGES['no_data'])
    # Forcing filename provided to override default sending directory of files
    if filename:
        if not os.path.isfile(filename):
            raise_error(DEFAULT_ERROR_MESSAGES['no_proper_data'])
        directory = ''

    remove = False
    if '-remove' in app_args:
        remove = True
    if not remove:
        if 'remove' in config:
            if config['remove'] == 'yes':
                remove = True
    # Do not remove a file if name provided from console and config says to remove original
    if remove:
        if filename:
            if not '-remove' in app_args:
                remove = False

    # Other miscellaneous error handling
    if directory:
        if not os.path.isdir(directory):
            raise_error(DEFAULT_ERROR_MESSAGES['no_proper_data'])
        if not file_type:
            raise_error(DEFAULT_ERROR_MESSAGES['no_filetype'])
    if not mimetype:
        raise_error(DEFAULT_ERROR_MESSAGES['no_mimetype'])
    if not username:
        raise_error(DEFAULT_ERROR_MESSAGES['no_username'])
    if not password:
        raise_error(DEFAULT_ERROR_MESSAGES['no_password'])
    if not host:
        raise_error(DEFAULT_ERROR_MESSAGES['no_host'])

    options = {
        'host': host,
        'username': username,
        'password': password,
        'url': url,
        'user_agent': DEFAULT_USER_AGENT,
        'mimetype': mimetype,
        'remove': remove,
        'silent': silent,
        'fileinfo_loc': fileinfo_loc,
    }

    # Calling main send function for either one file or directory with directory walker
    if filename:
        upload_file(filename, options)
    elif directory:
        filenames = walk_directory(directory, file_type)
        if not silent:
            print 'Sending files: %s' % filenames
        if not filenames:
            if not silent:
                print 'Nothing to send in this directory.'
            sys.exit(0)
        for name in filenames:
            upload_file(name, options)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# parsereport.py
#
# Codecheck assumptions:
# - All *.signed.zip files in download_directory are read
# - The last @author e-mail address in student files (alphabetically) will...
#   - (a) be valid (including &gt; & &lt;) and (b) not contain 'address'
#
"""
parsereport.py parses a directory of *.signed.zip files downloaded from
Codecheck.it, extracts and parses the report.html files from each, creates and
edits .md files w/ code and comments, and e-mails the resultinf .html file back
to students.
"""

__author__ = "David C. Petty"
__copyright__ = "Copyright 2020, David C. Petty"
__license__ = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
__version__ = "0.1.1"
__maintainer__ = "David C. Petty"
__email__ = "david_petty@psbma.org"
__status__ = "Hack"

import argparse, os, os.path, pathlib, re, smtplib, ssl, subprocess, sys, \
    xml.etree.ElementTree, xml.sax.saxutils, zipfile
from email.message import EmailMessage
from email.utils import formataddr

# Command lines for external applications on *my* system.
__jarsigner__ = ['/usr/bin/jarsigner', '-verify', ]
__macdown__ = ['open', '-W', '-a', '/Volumes/dcp/Applications/MacDown.app', ]


class Enum(tuple):
    """report.html parsing states."""
    __getattr__ = tuple.index


State = Enum(['INIT', 'STUDENT', 'PRE', 'CODE', 'DONE'])


class Zips:
    """Collects filenames from path matching _glob."""
    _glob = r'**/*.signed.zip'      # globbing path and subdirectories

    def __init__(self, path='.'):
        """Initialize Zips & paths property."""
        self._path = path
        zip_path = pathlib.Path(path)
        paths = zip_path.glob(self._glob)
        self._paths = [str(f) for f in sorted(set(paths))]

    @property
    def paths(self):
        """Return list of .ZIP file paths."""
        return self._paths


class Report:
    """Parse report.html extracted from path .ZIP file to extract values."""

    _bogus = 'address'              # text signifying a bogus e-mail address

    def __init__(self, path, verbose=False):
        """Initialize Report and parse values:
        name, email, id, pf, score, path, signed, code, error"""
        self._name = None
        self._email = None
        self._id = None
        self._pf = None
        self._score = None
        self._path = path
        self._signed = self._is_signed(path)
        self._code = list()
        self._error = list()
        self._verbose = verbose
        with zipfile.ZipFile(path) as myzip:
            with myzip.open('report.html') as myfile:
                self._text = myfile.read().decode('utf-8')
                self._parse(self._text)

    @staticmethod
    def _is_signed(path):
        """Use jarsigner to verify path is a signed .JAR."""
        ret = subprocess.run(__jarsigner__ + [path, ],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        return ret.returncode == 0

    def _parse(self, text):
        """Parse text according to Codecheck.it report.html format."""
        # Regular Expression for parsing @author line.
        author_regex = re.compile('@author[ ]+(([^\n<]*)[ ]+<([^\n>]*)>)',
                                  re.UNICODE + re.IGNORECASE)
        # Regular Expression for formatting author name.
        name_regex = re.compile('[^A-Za-z .]+', re.UNICODE)
        state = State.INIT
        # Parse XHTML text into an ElementTree.
        parser = xml.etree.ElementTree.XMLParser(encoding='utf-8')
        root = xml.etree.ElementTree.fromstring(text, parser)
        root.findall('.//{http://www.w3.org/1999/xhtml}meta')   # TODO: not used
        # Parse _id, _score, _code, _name, & _email.
        for element in root.iter():
            tag, attrib, text = element.tag, element.attrib, element.text
            # <meta name="ID" content="PROJECT">
            if tag.lower().endswith('meta'):
                if attrib.get('name', '').lower() == 'id':
                    self._id = attrib.get('content', None)
            # <p class="score">47/47</p> <!-- *exactly* equal to 'score' -->
            if tag.lower().endswith('p'):
                if attrib.get('class', None).lower() == 'score':
                    self._score = text
                    self._pf = 'FAIL'if eval(self._score) < 1 else 'PASS'
            # <pre class="output">cube(2) expected:&lt;8&gt; but was:&lt;4&gt;</pre>
            if tag.lower().endswith('pre') \
                    and text and text.find('expected:') >= 0:
                self._error += [text[: (text + '\n').find('\n')]]
            #
            # State machine to locate code within a student <pre> element.
            #
            # If the <pre> tags were replaced with <pre class="code"> (or,
            # better yet <pre class="student code">), then this five-state
            # machine could be replaced w/ the following single conditional:
            #
            # if 'code student' in attrib.get('class').split(' ')
            #
            if state is State.INIT:
                if tag.lower().endswith('div'):
                    if 'student' in attrib.get('class', None).lower():
                        state = State.STUDENT
            elif state is State.STUDENT and tag.lower().endswith('pre'):
                state = State.PRE
            elif state is State.PRE:
                if tag.lower().endswith('pre'):
                    # TODO: do we need to escape .HTML, if it is for .MD?
                    self._code += [xml.sax.saxutils.escape(text, {
                        '"': "&quot;", "'": "&apos;",
                    })]
                    state = State.STUDENT
                    # Parse @author fields in code text, if any.
                    match = author_regex.search(text)
                    if match:
                        if self._verbose:
                            print(f"@author match: {match.groups()}")
                        name, email = match.group(2), match.group(3)
                        if self._bogus not in email:
                            self._name = name_regex.sub('', name).strip()
                            self._email = email
            elif tag.lower().endswith('div'):
                if 'provided' in attrib.get('class', '').lower():
                    state = State.DONE

    def values(self):
        """Return name, email, id, pf, score, path, signed, code, error."""
        return self._name, self._email, self._id, self._pf, self._score, \
            self._path, self._signed, self._code, self._error,

    # TODO: not used
    @property
    def dirname(self):
        """Return os.path.dirname(self._path)."""
        return os.path.dirname(self._path)

    # TODO: not used
    @property
    def filename(self):
        """Return os.path.basename(self._path)."""
        return os.path.basename(self._path)

    @property
    def email(self):
        """Return formatted e-mail address if self._name and self._email,
        otherwise None."""
        return formataddr((self._name, self._email,)) \
            if self._name and self._email else None

    @property
    def has_email(self):
        """Return True if report has valid (YOUR NAME <your@email.address>)
        e-mail address, but not the default (above), otherwise False."""
        return self._name and self._email and self._bogus not in self._email


class Message:
    """Create and format text, markdown, and HTML messages."""
    _text_format = """Code\n{code}\nComment\n{comment}"""
    _text_code_format = """{listing}\n"""
    _md_format = """<h1 style="color: {color};">Code</h1>
{code}

<h1 style="color: {color};">Comment</h1>
{comment}
{errors}
Add comment here&hellip;"""
    _md_code_format = """```java
{listing}
```"""
    _html_comment_format = '<!-- {comment} -->'
    _html_comment = _html_comment_format.format(comment='ONLY EDIT BELOW')
    # TODO: HTML formatting _html_format is not used
    _html_format = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
  </head>
  <body>
    <h1 style="color: {color};">Code</h1>
    <div>
{content}
    </div>
  </body>
</html>"""
    _html_code_format = """<pre>{listing}</pre>\n"""

    def __init__(self, path, pf, description, code, error, resend=False):
        """Use path to edit corresponding .MD file to create corresponding
        .HTML file, seeding .MD file with code and error (if any), using pf
        to color-code, and including a comment w/ description (e-mail subject
        plus other student information, including whether path was properly
        signed). Create text_message, markdown_message, and html_message
        properties. Only edit .MD file if no .MD file exists or resend and
        set isnew property accordingly."""

        color = 'green' if pf == 'PASS' else 'red'

        # Create pathnames for md_path & html_path from path.
        basename, filename = os.path.split(path)
        prefix = os.path.splitext(os.path.splitext(filename)[0])[0]
        md_path = os.path.join(basename, prefix + '.md')
        html_path = os.path.join(basename, prefix + '.html')

        # Collect code listings.
        text_code, md_code, html_code, sep = '', '', '', ''
        for listing in code:
            # Add each listing to text format and html format
            text_code += self._text_code_format.format(listing=listing)
            md_code += sep + self._md_code_format.format(listing=
                xml.sax.saxutils.unescape(listing, {
                    "&quot;": '"',
                    "&apos;": "'",
                    }))
            html_code += sep + self._html_code_format.format(listing=listing)
            style = f'padding:0; margin:0; border:none; ' \
                    f'background-color:{color}; height:1px;'
            sep = f'\n<hr style="{style}">\n'

        # Cases (editing the .MD file requires a new .HTML file be exported):
        # resend |  .MD  | .HTML | Action
        #  ----- | ----- | ----- | ------
        #    F   |   F   |   F   | edit new .MD file, isnew = True
        #    F   |   F   |   T   | edit new .MD file, isnew = True
        #    F   |   T   |   F   | edit existng .MD file, isnew = True
        #    F   |   T   |   T   | do not edit existng .MD file, isnew = False
        #    T   |   F   |   F   | edit new .MD file, isnew = True
        #    T   |   F   |   T   | edit new .MD file, isnew = True
        #    T   |   T   |   F   | edit existng .MD file, isnew = True
        #    T   |   T   |   T   | edit existng .MD file, isnew = True

        nomd = not os.path.isfile(md_path)
        nohtml = not os.path.isfile(html_path)
        # not (not resend and not nomd and not nohtml)
        self._isnew = resend or nomd or nohtml

        if nomd:
            comments = \
                f"{self._html_comment_format.format(comment=description)}" \
                f"{self._html_comment}"
            errors = '\n'.join([f"> {s} <br>" for s in error]) + '\n'
            # Create new .MD file w/ empty comment section.
            with open(md_path, 'w') as md_file:
                md_file.write(self._md_format.format(code=md_code,
                                                     color=color,
                                                     comment=comments,
                                                     errors=errors))

        if self.isnew:
            # Edit .MD file and export as .HTML file.
            if os.path.isfile(html_path):
                os.remove(html_path)
            print(f"Editing {md_path}...\nMUST export {html_path}")
            ret = subprocess.run(__macdown__ + [md_path, ],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            assert ret.returncode == 0, f"error ({ret}) running MacDown"
            # TODO: assertion error message is not helpful, if .HTML not found
            assert os.path.isfile(html_path), f"file not found: {html_path}"

        # Initialize text_message, markdown_message, & html_message properties.
        with open(md_path, 'r') as md_file:
            self._md_message = md_file.read().strip()
        # Assumes self._html_comment is in .MD file.
        start = self._md_message.find(self._html_comment)
        comment = self._md_message[start + len(self._html_comment):]
        self._text_message = \
            self._text_format.format(code=text_code.strip(),
                                     comment=comment.strip()).strip()
        with open(html_path, 'r') as html_file:
            self._html_message = html_file.read().strip()

    @property
    def isnew(self):
        """Return True if message should be sent, False otherwise."""
        return self._isnew

    @property
    def text_message(self):
        """Return text message."""
        return self._text_message

    @property
    def markdown_message(self):
        """Return markdown message."""
        return self._md_message

    @property
    def html_message(self):
        """Return HTML message."""
        return self._html_message


class Mailer:
    """Create mailer capable of sending content."""
    # https://docs.python.org/3/library/email.examples.html
    _subject_format = '[codecheck] {}: {} ({}) in {} for {}'

    def __init__(self, name, email, ccid, pf, score, path, signed, code, error,
                 resend=False):
        """Initialize e-mail message to be sent based on:
        name, email, ccid, pf, score, path, signed, code, error."""
        self._name = name           # recipient name
        self._email = email         # recipient e-mail address
        self._id = ccid             # Codecheck project ID
        self._pf = pf               # PASS / FAIL string
        self._score = score         # score string (47/47)
        self._path = path           # report .ZIP path
        self._signed = signed       # result of jarsigner -verify
        self._code = code           # submitted code list
        self._error = error         # list of error strings
        self._subject = self._subject_format\
            .format(self._id, self._pf, self._score, self.filename, self._name)
        self._real_name = os.getenv('NAME', 'David C. Petty')
        self._username = os.getenv('ADDR', 'david_petty@psbma.org')
        self._password = os.getenv('PASS', None)
        self._sender = formataddr((self._real_name, self._username,))
        self._recipient = f'"{self._name}" <{self._email}>'
        self._recipient = formataddr((self._name, self._email,))
        self._message = EmailMessage()
        self._message["Subject"] = self._subject
        self._message["From"] = self._sender
        self._message["To"] = self._recipient
        self._message.preamble = 'Invisible to a MIME-aware mail reader.\n'

        # Create Message from data to prepare for send.
        tag = f"{self.subject} <{self._email}>" \
              f"{' NOT' if not self._signed else ''} SIGNED"
        message = Message(self._path, self._pf, tag, self._code, self._error,
                          resend)
        self._message_isnew = message.isnew

        self._message.set_content(message.text_message)
        self._message.add_alternative(message.html_message, subtype='html')

    def send(self):
        """Send message to recipient if message isnew."""
        if self.isnew:
            # Create secure connection with server and send email
            smtp, port = "smtp.gmail.com", 465
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp, port, context=context) as server:
                server.login(self._username, self._password)
                server.sendmail(
                    self._sender, self._recipient, self._message.as_string()
                )
            print(f'Sent to: {self._recipient}')

    @property
    def html_message(self):
        """Return message HTML body."""
        return self._message.get_body('html')

    @property
    def text_message(self):
        """Return message text body."""
        return self._message.get_body('text')

    @property
    def message(self):
        """Return message entire message string."""
        return str(self._message)

    @property
    def subject(self):
        """Return message subject attribute."""
        return self._message['Subject']

    @property
    def frm(self):
        """Return message subject attribute."""
        return self._message['From']

    @property
    def to(self):
        """Return message subject attribute."""
        return self._message['To']

    @property
    def filename(self):
        """Return os.path.basename(self._path)."""
        return os.path.basename(self._path)

    @property
    def isnew(self):
        """Return True if message body is new, False otherwise."""
        return self._message_isnew


class OptionParser(argparse.ArgumentParser):
    """Create OptionParser to parse command-line options."""
    def __init__(self, **kargs):
        argparse.ArgumentParser.__init__(self, **kargs)
        # self.remove_argument("-h")
        self.add_argument("-?", "--help", action="help",
                          help="show this help message and exit")
        self.add_argument('--version', action='version',
                          version=f"%(prog)s {__version__}")

    def error(self, msg):
        sys.stderr.write("%s: error: %s\n\n" % (self.prog, msg, ))
        self.print_help()
        sys.exit(2)


def main(argv):
    """ Parse command-line options to create reports and mail them ."""
    description = """Read .SIGNED.ZIP files from PATH; parse Codecheck.it
    report for e-mail address, score, and code; edit response and e-mail it 
    back."""
    formatter = lambda prog: \
        argparse.ArgumentDefaultsHelpFormatter(prog, max_help_position=30)
    parser = OptionParser(description=description, add_help=False,
                          formatter_class=formatter)
    arguments = [
        # c1, c2, action, dest, default, help
        ('-e', '--email', 'store', 'ADDR', None, 'SMTP e-mail', ),
        ('-p', '--password', 'store', 'PASS', None, 'SMTP password', ),
        ('-r', '--resend', 'store_true', 'RESEND', False, 'resend comment, if available', ),
        ('-v', '--verbose', 'store_true', 'VERBOSE', False, 'echo status information', ),
    ]
    # Add optional arguments with values.
    for c1, c2, a, v, d, h in arguments:
        parser.add_argument(c1, c2, action=a, dest=v, default=d, help=h,)
    # Add positional arguments. DIR is both the string and the variable.
    parser.add_argument("PATH", help="path to directory with .SIGNED.ZIP files")
    # Parse arguments.
    ns = parser.parse_args(args=argv[1: ])
    if ns.ADDR:
        os.environ['ADDR'] = ns.ADDR
    if ns.PASS:
        os.environ['PASS'] = ns.PASS

    # Process all zips in path.
    zips = Zips(ns.PATH)
    for p in zips.paths:
        print(f"Processing: {p}")
        report = Report(p, ns.VERBOSE)
        if ns.VERBOSE:
            print('values:', [f'{repr(x)}' for x in report.values()])
        if report.has_email:
            mailer = Mailer(*report.values(), ns.RESEND)
            if ns.VERBOSE:
                print('message:')
                print(mailer.message)
            mailer.send()
        else:
            print(f"* ERROR: '{report.email}' not a valid e-mail address")


if __name__ == '__main__':
    is_idle, is_pycharm, is_jupyter = (
        'idlelib' in sys.modules,
        int(os.getenv('PYCHARM', 0)),
        '__file__' not in globals()
    )
    if any((is_idle, is_pycharm, is_jupyter,)):
        main(['parsereport.py', '../data/',
              '-e', 'david_petty@psbma.org', ])
    else:
        main(sys.argv)

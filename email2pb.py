import argparse
import base64
import email
import logging
import re
import sys

from pushbullet import PushbulletAPIClient


logger = logging.getLogger(__name__)


parser = argparse.ArgumentParser(description='Send PushBullet PUSH based on email message')
parser.add_argument(
    'infile', nargs='?', type=argparse.FileType('r'), default=sys.stdin,
    help='MIME-encoded email file(if empty, stdin will be used)')
parser.add_argument('--key', help='API key for PushBullet', required=True)
parser.add_argument('--debug', help='Enable debug mode', action='store_true')
parser.add_argument("--debug_log", type=str)
args = parser.parse_args()

stdin_data = args.infile.read()


debug_mode = args.debug
if debug_mode:
    logger.debug('Debug mode enabled')
    logfile_path = args.debug_log or "debug.log"
    with open(logfile_path, "w") as debug_log:
        debug_log.write("\n")
        debug_log.write("Incoming message:\n")
        debug_log.write("-------------------------\n")
        debug_log.write(stdin_data)
        debug_log.write("-------------------------\n")

msg = email.message_from_string(stdin_data)
args.infile.close()

def decode_field(field_raw):
    match = re.match(r'\=\?([^\?]+)\?([BQ])\?([^\?]+)\?\=', field_raw)
    if match:
        charset, encoding, field_coded = match.groups()
        if encoding == 'B':
            field_coded = bytearray(field_coded, encoding=charset)
            field_coded = base64.decodestring(field_coded)
        return field_coded.decode(charset)
    else:
        return field_raw

subject_raw = msg.get('Subject', '')
subject = decode_field(subject_raw)

sender = decode_field(msg.get('From', ''))

body_text = ''
for part in msg.walk():
    if part.get_content_type() == 'text/plain':
        body_part = part.get_payload()
        part_encoding = part.get_content_charset()

        if part.get('Content-Transfer-Encoding') == 'base64':
            body_part = bytearray(body_part, encoding=part_encoding)
            body_part = base64.decodestring(body_part)
            body_part = body_part.decode(part_encoding)

        if body_text:
            body_text = '%s\n%s' % (body_text, body_part)
        else:
            body_text = body_part

body_text = '%s\nFrom: %s' % (body_text, sender)

client = PushbulletAPIClient(api_key=args.key)
client.push_note_to_device(None, body_text, title=subject)

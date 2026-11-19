"""See Layer 5 working, no server needed:
    python -m app.tools.try_hide "I am Rahim, call 01711223344"
    python -m app.tools.try_hide "I am Rahim, call 01711223344" Rahim     (second word = the profile name)
"""
import sys

from app.layers.cleaning import clean
from app.layers.privacy import hide_private, restore

arguments = sys.argv[1:]
if len(arguments) == 0:
    message = input("Type a message: ")
    profile_name = None
elif len(arguments) == 1:
    message = arguments[0]
    profile_name = None
else:
    message = arguments[0]
    profile_name = arguments[1]

hidden = hide_private(clean(message).text, profile_name)
print("sent on :", hidden.text)
print("mapping :", hidden.mapping)
print("restored:", restore(hidden.text, hidden.mapping))

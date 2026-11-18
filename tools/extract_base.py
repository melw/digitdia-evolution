"""extract_base.py - unpack the main firmware from your flash dump into base/fw_main.rbn.

  python tools/extract_base.py <8 MB flash dump>

Checks the result against the known firmware 2.0 image (SHA256 in build.py).
"""
import hashlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flashdump  # noqa: E402

KNOWN = '907b2267c65ef7629d308a789d93f4056ac61a64c6619db78a5868a10aada4c7'

rbn = flashdump.unbcl(flashdump.load(sys.argv[1]), flashdump.MAIN_FW)
h = hashlib.sha256(rbn).hexdigest()
out = os.path.join(HERE, '..', 'base', 'fw_main.rbn')
open(out, 'wb').write(rbn)
print('base/fw_main.rbn: %d bytes, SHA256 %s' % (len(rbn), h))
print('OK: firmware 2.0 (the version this project was made for)' if h == KNOWN else
      'WARNING: not the known firmware 2.0 image. The patches will refuse to apply (they check every original word).')

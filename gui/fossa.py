import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui.methods import Helpers
from gui.whoami import Who
from gui.objects.References import References


def main():
    print("Starting FOSSA GUI...")
    who = Who.Who()
    print(f"Current user: {who.options}")
    ref = References()
    print(f"Set up references")
    ref.who = who
    print(f"Set who")
    Helpers.FossaMain(ref)
    print("FOSSA GUI closed.")


if __name__ == "__main__":
    main()

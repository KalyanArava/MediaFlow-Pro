import urllib.request
import zipfile
from pathlib import Path

DENO_VERSION = "2.9.6"

ROOT = Path(__file__).resolve().parent
BIN_DIR = ROOT / "bin"
DENO_PATH = BIN_DIR / "deno"

URL = (
    f"https://github.com/denoland/deno/releases/download/"
    f"v{DENO_VERSION}/deno-x86_64-unknown-linux-gnu.zip"
)

def main():
    BIN_DIR.mkdir(parents=True, exist_ok=True)

    if DENO_PATH.exists():
        print(f"Deno already exists: {DENO_PATH}")
        return

    archive = ROOT / "deno-linux-x86_64.zip"

    print(f"Downloading Deno {DENO_VERSION} for Vercel Linux x86_64...")
    print(URL)

    urllib.request.urlretrieve(URL, archive)

    print("Extracting Deno...")

    with zipfile.ZipFile(archive, "r") as z:
        z.extractall(BIN_DIR)

    archive.unlink(missing_ok=True)

    if not DENO_PATH.exists():
        raise RuntimeError("Deno binary was not found after extraction.")

    DENO_PATH.chmod(0o755)

    print(f"Deno installed at: {DENO_PATH}")

if __name__ == "__main__":
    main()

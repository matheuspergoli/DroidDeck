"""Sign and verify the independent Heizmen package using fork-only secrets."""

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


PACKAGE = "com.droiddeck.launcher.heizmen"
REPOSITORY = "matheuspergoli/DroidDeck"
ROOT = Path(__file__).resolve().parents[2]


def run(arguments):
    result = subprocess.run([str(argument) for argument in arguments], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{Path(arguments[0]).name} failed with exit status {result.returncode}")
    return result.stdout


def main():
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise RuntimeError("Personal signing is restricted to our fork")
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise RuntimeError("Personal signing requires manual dispatch")
    if not os.environ.get("HEIZMEN_STORE_PASSWORD"):
        raise RuntimeError("Missing personal signing password")
    encoded = os.environ.get("HEIZMEN_KEYSTORE_B64", "")
    if not encoded:
        raise RuntimeError("Missing personal keystore")
    expected = (ROOT / "keystore/heizmen-signer.sha256").read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise RuntimeError("Invalid personal certificate commitment")
    apk = Path(sys.argv[1]).resolve(strict=True)
    tools = Path(os.environ["BUILD_TOOLS"])
    previous_umask = os.umask(0o077)
    try:
        with tempfile.TemporaryDirectory(prefix="heizmen-sign-", dir=os.environ.get("RUNNER_TEMP")) as folder:
            work = Path(folder)
            key = work / "signer.p12"
            key.write_bytes(base64.b64decode(encoded, validate=True))
            aligned, signed = work / "aligned.apk", work / "signed.apk"
            run([tools / "zipalign", "-p", "-f", "4", apk, aligned])
            run([
                tools / "apksigner", "sign", "--ks", key, "--ks-type", "PKCS12",
                "--ks-pass", "env:HEIZMEN_STORE_PASSWORD", "--ks-key-alias", "heizmen",
                "--key-pass", "env:HEIZMEN_STORE_PASSWORD", "--v1-signing-enabled", "true",
                "--v2-signing-enabled", "true", "--v3-signing-enabled", "true",
                "--v4-signing-enabled", "false", "--out", signed, aligned,
            ])
            verification = run([
                tools / "apksigner", "verify", "--min-sdk-version", "26",
                "--verbose", "--print-certs", signed,
            ])
            digests = re.findall(r"Signer #\d+ certificate SHA-256 digest: ([0-9a-fA-F]{64})", verification)
            if [digest.lower() for digest in digests] != [expected]:
                raise RuntimeError("APK signer does not match the committed personal certificate")
            for scheme in ("v1 scheme (JAR signing)", "v2 scheme (APK Signature Scheme v2)",
                           "v3 scheme (APK Signature Scheme v3)"):
                if f"Verified using {scheme}: true" not in verification:
                    raise RuntimeError(f"Personal APK is missing {scheme}")
            badging = run([tools / "aapt", "dump", "badging", signed])
            if f"package: name='{PACKAGE}'" not in badging:
                raise RuntimeError("Personal APK does not have its independent package ID")
            if "application-label:'DroidDeck Heizmen'" not in badging:
                raise RuntimeError("Personal APK launcher label is not distinct")
            manifest = run([tools / "aapt", "dump", "xmltree", signed, "AndroidManifest.xml"])
            identities = re.findall(r'android:(?:authorities|taskAffinity)[^=\n]*="([^"]+)"', manifest)
            if not identities or any(
                not identity.startswith(PACKAGE + ".")
                for group in identities for identity in group.split(";")
            ):
                raise RuntimeError("Manifest provider/task identities are not isolated")
            if "com.droiddeck.launcher.MainActivity" not in manifest:
                raise RuntimeError("Application class namespace was unexpectedly changed")
            with signed.open("rb") as source, apk.open("wb") as target:
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)
            version = re.search(r"versionName='([^']+)'", badging)
            code = re.search(r"versionCode='([^']+)'", badging)
            with apk.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            metadata = {
                "package": PACKAGE, "label": "DroidDeck Heizmen",
                "version_name": version.group(1) if version else None,
                "version_code": int(code.group(1)) if code else None,
                "source_commit": os.environ.get("GITHUB_SHA"),
                "certificate_sha256": expected, "apk_sha256": digest,
                "updater": "manual-personal-apk", "distribution": "heizmen-personal",
            }
            (apk.parent / "heizmen-build.json").write_text(json.dumps(metadata, indent=2) + "\n")
            (apk.parent / "SHA256SUMS.txt").write_text(f"{digest}  {apk.name}\n")
            print(json.dumps(metadata, indent=2))
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    main()

# DroidDeck Heizmen: independent personal distribution

The user chose a fresh installation and will sign in and install Hell Clock
again. Migration of the official installation is out of scope for this build.

## Identity

- Android application ID: `com.droiddeck.launcher.heizmen`.
- Launcher label: `DroidDeck Heizmen`.
- Source namespace and JNI class names: unchanged, `com.droiddeck.launcher`.
- Enabled by Gradle property `heizmenBuild=true`; ordinary builds keep their
  original application ID, label and updater behavior.
- Personal version code: `100000 + heizmenBuildNumber`; the workflow supplies
  its run number. Version name retains the upstream version and appends
  `-heizmen.<number>`. Future personal updates must preserve the package and
  signer and not decrease the version code.

The source base is upstream `facaa18a3c127da043c3edc471ac3bebcca4a295`.
This distribution composes PERF-001 and PERF-002 from their isolated candidates.
Their previous host/CI verification does not establish device performance for
this new combination. The functional integration branch remains separate.

## Signing

The private PKCS12 and password are outside the repository. Only the public
certificate SHA-256 is committed in `keystore/heizmen-signer.sha256`:

`010b2a2a426a6c91fbf7c32df10a424dd5120284952270d0ce51f7657befba10`

GitHub secrets `HEIZMEN_KEYSTORE_B64` and `HEIZMEN_STORE_PASSWORD` exist only in
`matheuspergoli/DroidDeck`. Personal signing requires a manual dispatch in that
repository and uses a temporary private directory on the runner. The APK is
signed directly with the personal key, without the public test key as a signing
ancestor. Keep the original local key and password backed up for future updates;
generating a different key is not an update-preserving replacement.

The upstream build still validates its intermediate test-key APK. A separate
final step re-signs the independent personal package, verifies the signer,
v1/v2/v3, application ID, distinct label, provider/task identities and retained
source class namespace, then publishes the final APK and metadata.

## Installation and updates

This APK is a new app, not an update of the official one. It has its own data,
runtime, preferences and Steam login. No data is copied from the official app.
The built-in official APK updater is inactive only in personal builds, with an
explanation on its page. Steam, game, driver and runtime update mechanisms are
not disabled. Future personal APKs can be installed over this app when identity,
signer and version-code requirements are met.

Installation on a real S25+ remains to be observed; passing the package/signing
checks is not a substitute for that observation.

## Workflow

Dispatch `Build APK` on `heizmen/personal` with input `heizmen_build=true`.
The artifact is `droiddeck-heizmen-apk`, containing the signed APK,
`heizmen-build.json` and `SHA256SUMS.txt`. Default dispatches remain standard
test-key builds and must not be confused with the personal artifact.

The composition and packaging changes are experimental. Keep individual
candidate branches and their controls for diagnosis and recovery.

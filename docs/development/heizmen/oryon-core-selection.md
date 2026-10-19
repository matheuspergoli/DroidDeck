# PERF-002: preserve inherited affinity on known Oryon SoCs

Status: experimental candidate; no device benchmark yet.

## Provenance

- Upstream base: `facaa18a3c127da043c3edc471ac3bebcca4a295`.
- Reference: [DroidDeck PR #953](https://github.com/Droid-Deck/DroidDeck/pull/953),
  first commit `b4729d31ba7cf36a66bcac7854a1b68a79e61953`, by ovurrsl.
- Reviewed PR head: `39f96a006bc720b46f04141cc13aaf14687da8f6`.
- This is a narrower adaptation, not a merge of the whole PR. GPU detection,
  display changes and other merged work from that branch are not included.

## Problem

The `program_cores` helper drops the lowest maximum-frequency tier when choosing
an automatic mask. On an Oryon six-plus-two layout this selects only the two
prime cores, although the six lower-frequency cores are performance cores.

The helper is used by desktop and direct-program launch paths. This does not
establish that a game launched through Steam, with an explicit affinity or a
different launch path, is affected.

## Change

`SessionService` passes its existing `SocNames.model()` result as `BL_SOC_MODEL`.
After honoring disabled pinning, missing taskset and an explicit `BL_GAME_CPUS`,
the helper returns no automatic mask for `SM8750`/`SM8850` (including hyphenated
suffixes). This keeps the inherited scheduler affinity rather than forcing a
mask containing every CPU. Android cpusets and inherited restrictions remain
in effect.

This differs from #953's topology heuristic: it does not classify an unknown
six-plus-two device as Oryon just from frequencies. Other models keep their
existing behavior. An unavailable/unrecognized SoC model also keeps the old
selection; the candidate does not claim to fix every possible detection gap.

Explicit user masks retain precedence. This is not a clock boost, priority
change, thermal-policy change or PRoot optimization.

## Verification

`tools/tests/test_program_cores.py` exercises the real Bash function with a
controlled sysfs tree; only its sysfs pathname is redirected into the fixture.
Before the change, known Oryon cases returned `6,7`. The candidate instead keeps
inherited affinity. Coverage also includes unknown six-plus-two models,
traditional little clusters, disabled pinning, explicit masks, homogeneous or
missing frequency data, and unavailable taskset.

Local checks:

```sh
python3 -m unittest discover -s tools/tests -p test_program_cores.py
python3 -m unittest discover -s tools/tests -p test_client_core_mask.py
python3 -m unittest discover -s tools/tests -p test_launcher_cores.py
bash -n tools/linuxfs/overlay/usr/local/bin/droiddeck-session
```

The local runs passed 7 new tests, 3 Steam mask tests and 11 launcher-governor
tests. These are controlled host tests, not measurements from a Galaxy S25+.
Full build results are recorded against the exact source commits below.

### Completed CI builds

| Target | Source | Run | Rust host | Python | Android/Gradle host |
| --- | --- | --- | --- | --- | --- |
| Control + CI adaptation | `daa6b5a` | [39211661860](https://github.com/matheuspergoli/DroidDeck/actions/runs/39211661860) | 152 passed | 930 tests | 1652 passed |
| Control + PERF-002 | `cbcfaf3` | [39211655349](https://github.com/matheuspergoli/DroidDeck/actions/runs/39211655349) | 152 passed | 937 tests | 1652 passed |

Both workflows succeeded. Android/Gradle reports show zero failures and zero
ignored tests. The seven additional Python tests are the new affinity suite.
Asset/library checks and test-key v1/v2/v3 signature verification passed.

APK SHA-256:

- Control: `a996ce15813bc70817c1e8ecc6379fd712a43c64ae60014ebd4a6cc3fd8d3a0e`.
- Candidate: `c5b7dfca740752e8b535a35e72d22953248df9946b7eed7e47cde8258b5ca862`.

These APKs retain the source's standard package ID and public test-key signing.
They are not official-release-signed updates or a completed personal install
channel. Documentation-only commits after these runs do not change the source
identity of their artifacts. Successful host suites are not device benchmarks.

## Acceptance and recovery

Confirm `BL_SOC_MODEL`, the actual launch path, configured user masks and the
live allowed CPU sets in the device. Compare the same desktop/direct-program
workload before and after, including temperature, frame cadence and competing
processes. Measure Steam workloads separately rather than promising a gain for
Hell Clock based on this helper alone.

No migration is introduced. Revert the functional commit to remove the extra
environment entry and restore the automatic frequency-tier filter. PERF-001
is an independent candidate and is not part of this branch.

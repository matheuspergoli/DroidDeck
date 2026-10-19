# PERF-001: bounded presentation timestamps

Status: experimental candidate; no Galaxy S25+ measurements yet.

## Provenance

- Upstream base: `e321f5025da30ef47e32cb71cf1794b2d8862371`.
- Reference: [DroidDeck PR #1033](https://github.com/Droid-Deck/DroidDeck/pull/1033),
  initial change by 0x1Nawaf, commit `fb8fe3b35a1f2a13c977b918cdfc266ca37c9db7`.
- Reviewed PR head: `1ceca9fcaee08c5e5a02184e8d065df0042f472d`.
- This is an adaptation, not an unchanged merge of that PR. The upstream main
  and exact 0.5.0 baseline branches remain separate from this candidate.

## Problem and change

`render_scene` supplies its scene-start timestamp to `presented_ns`. The previous
selection rejected every tick later than that start, even within one display
interval. PR #1033 permits nearby ticks and rejects missing callback timestamps.

The callback receipt time and the tick timestamp are separate facts: a recently
delivered callback can still carry an old tick. This candidate additionally
rejects ticks more than one nominal refresh interval behind the scene start.
Ticks more than one interval ahead also fall back, as in the PR. Existing
fallback for an old callback receipt is preserved.

The retained tick is an estimate for the presentation protocol, not a measurement
of when a pixel actually appears. This change does not increase rendering
throughput by itself, change GPU clocks, alter FG policy, or prove lower latency.

## Verification

`tools/tests/test_presentation_timestamps.py` extracts and compiles the actual
`nominal_refresh_ns` and `presented_ns` functions with controlled timestamps.
The original source failed the nearby-tick, stale-tick and missing-callback
scenarios before the implementation changed. The candidate passes those cases,
normal cadence, far-future rejection, fallback refresh and interval boundaries
at 60/90/120/144 Hz.

Run:

```sh
python3 -m unittest discover -s tools/tests -p test_presentation_timestamps.py
python3 -m unittest discover -s tools/tests -p test_output_refresh.py
```

These are native host tests with controlled inputs, not Android compositor or
game benchmarks. The normal CI discovers the additional Python test. Full APK
build and test results must be recorded separately after completion.

## Device acceptance still required

Compare unmodified upstream and candidate at the same component versions,
resolution, refresh and game scene. Test FG off first, then fixed and adaptive
FG separately. Examine presentation cadence, repeated frames, stalls, suspend
and resume, and refresh changes. Check that the change does not introduce
regressions into ordinary 60/120 Hz sessions. Hell Clock on the S25+ is the
first intended workload, not a tested success claim.

## Recovery

Revert the functional commit together with its regression test if rejected.
Keep the independent Debian-image CI adaptation. No data migration is introduced
by this candidate.

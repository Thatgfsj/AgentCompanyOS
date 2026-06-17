# Phase 5 — Personality

> ACO has a face. And a voice.

**Owner:** Thatgfsj
**Target start:** 2027-01-14
**Target end:** 2027-03-05
**Status:** Planned

---

## Goal

Each agent has a Live2D avatar that reacts to its state (idle,
thinking, speaking, error). The user can talk to ACO via voice
input and listen to its responses. The whole experience feels
alive.

## Deliverables

1. **Live2D avatars**
   * Chief: owl / lighthouse motif, blue theme
   * Critic A: hawk / magnifying glass, red theme
   * Critic B: owl / compass, purple theme
   * Workers: rotating cute-developer mascots
   * 4 states × 5 characters = 20 Live2D assets
   * Open-source license (CC-BY 4.0); swappable
   * Default: subtle pulse + status color
   * Reduced-motion: static fallback

2. **Voice input (Whisper)**
   * Local Whisper via `whisper.cpp` (no cloud, no API key)
   * Push-to-talk hotkey; "always on" toggle (with privacy note)
   * Languages: English (v0.5); Simplified Chinese (v0.6)
   * Result goes into the same Cmd input

3. **Voice output (TTS)**
   * Local Piper TTS (no cloud)
   * Each agent has a distinct voice
   * Toggle: mute all / chief only / all
   * Streaming: starts as soon as the first sentence is ready

4. **Streaming interactions**
   * Chief's "thinking" is visible as a **stream of bullets**,
     not a single completion
   * Each new bullet appears in the Reasoning panel within 1s
   * User can interrupt the stream ("stop, do X instead")

5. **Accessibility**
   * Full `prefers-reduced-motion` honor
   * Voice + visual: subtitles for all TTS
   * Avatar optional (can be hidden)

## Done criteria

* Open the app; Chief's avatar pulses while thinking.
* Push-to-talk: "Add a hello world function to utils.ts" → workflow
  runs → voice reply "Done — added helloWorld and a test."
* Reduced-motion users see a static avatar with status colors
  only.
* All assets are open-source and on GitHub.

## Tasks

| #  | Task                                                       | Estimate | Blocked by |
|----|------------------------------------------------------------|----------|------------|
| 5.1| Live2D asset pipeline (open-source CC-BY 4.0)              | 10 d     | —          |
| 5.2| Avatar component (React + pixi.js + Live2D Cubism)        | 6 d      | 5.1        |
| 5.3| Avatar state machine (idle / thinking / speaking / error) | 3 d      | 5.2        |
| 5.4| Whisper integration (local whisper.cpp)                   | 4 d      | —          |
| 5.5| Push-to-talk hotkey + UX                                   | 3 d      | 5.4        |
| 5.6| TTS integration (local Piper)                              | 3 d      | —          |
| 5.7| Per-agent voice assignments                                | 2 d      | 5.6        |
| 5.8| Streaming Chief thinking (visible bullets)                 | 4 d      | Phase 1    |
| 5.9| Interrupt support                                          | 2 d      | 5.8        |
| 5.10| Subtitles for all TTS                                      | 2 d      | 5.6        |
| 5.11| Accessibility: reduced-motion                              | 1 d      | 5.2        |
| 5.12| Avatar hide toggle                                         | 1 d      | 5.2        |

**Total estimate:** ~41 days

## Out of scope (Phase 5)

* Multi-tenant / enterprise SSO
* Cloud sync
* Real-time collaboration

## Risks

| Risk                                          | Mitigation                                  |
|-----------------------------------------------|----------------------------------------------|
| Live2D Cubism licensing                       | Use Cubism SDK only with CC0/CC-BY assets; document in plugin spec |
| Whisper perf on low-end laptops               | Default to `tiny` model; user can pick `base`/`small`/`medium` |
| Voice UX feels gimmicky                       | Make it opt-in; default to text             |
| Avatar asset creation is slow                 | Commission an artist or use AI-generated base + manual polish |

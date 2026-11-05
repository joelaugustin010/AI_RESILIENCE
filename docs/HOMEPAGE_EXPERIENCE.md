# Homepage experience

The homepage is the default entry point of AI RESILIENCE. It is designed as a
guided, cinematic introduction to Kerala and to the evidence-first workspaces
behind the platform — not as a dashboard of ordinary metric cards.

- Entry point: `app.py` (registers `app_pages/home.py` as the default page)
- Page implementation: `app_pages/home.py`
- Shared visual system: the scoped `<style>` block in `app.py`
- Static assets: `static/images/`, `static/videos/`
- Hero video drop-in: `assets/videos/kerala_hero.mp4`
- Licensing record: `assets/IMAGE_CREDITS.md`

## Story sequence

The page moves through four deliberate chapters, followed by a footer and an
optional credits expander.

1. **Hero — AI RESILIENCE**
   - Title: `AI RESILIENCE`
   - Subtitle: “Protecting Kerala. Predicting Risks. Building a Resilient Future.”
   - One short platform description and four capability chips.
   - Two calls to action: **Explore Intelligence** opens the Decision Workflow;
     **Explore Kerala's Risks** opens the Kochi Map.
   - A four-part signal strip (districts, hazard families, workspaces, open by
     design) separates the hero from the narrative.
2. **01 · The beauty of Kerala**
   - A six-image editorial gallery: backwaters, the Western Ghats, Athirappilly,
     the Varkala coast, Silent Valley forest and Kochi.
   - Captions describe the landscape and its context; they do not claim to show
     current conditions or a specific event.
3. **02 · The threats we face**
   - A photographic band with six custom SVG hazard cards: floods and
     waterlogging, landslides, cyclones and coastal hazards, air and industrial
     pollution, extreme rainfall, and environmental degradation.
4. **03 · Why AI_RESILIENCE matters**
   - A four-step evidence chain: Monitor → Assess → Protect → Prepare.
   - A transparency panel restates the scientific safeguards.
5. **04 · Explore the intelligence platform**
   - Four grouped workspace cards linking every non-home page (11 links):
     Risk & readiness, Place & environment, People & critical services, and
     Plan & design.
6. **Footer and photography credits**
   - Project positioning and SDG references, plus an expander with image
     licences and source links.

All chapter headings use the shared `ar-` design system: dark atmospheric
backgrounds, teal/sand accents, generous whitespace and restrained borders.

## Hero media behaviour

The hero is composed of layered elements inside `.ar-cine-hero`:

1. poster image (`.ar-cine-poster`) — always present;
2. optional local video (`.ar-cine-video`) — only emitted when a real file
   exists;
3. gradient scrim, vignette and a very light film-grain texture;
4. copy and actions on top.

### Video

Place the film at:

```
assets/videos/kerala_hero.mp4
```

On the next run the page copies it to `static/videos/kerala_hero.mp4` and emits:

```html
<video autoplay muted loop playsinline preload="metadata" ...>
```

The source is local and relative (`app/static/videos/kerala_hero.mp4`). The page
never references a remote URL, never commits a placeholder `.mp4`, and never
renders a `<video>` element with a missing source. If no video exists at either
location, only the local photograph is shown. The generated copy under
`static/videos/` is ignored by Git; to revert to the photograph after testing a
film, remove both copies.

The poster is the same photograph, so the first frame is meaningful and there
is no blank flash. `object-fit: cover` fills the hero at every viewport size.
The gradient scrim is deliberately strong on the left, where the title sits.

Recommended export settings and an `ffmpeg` example are in
[`assets/videos/README.md`](../assets/videos/README.md).

### Reduced motion

When `prefers-reduced-motion: reduce` is active:

- the video is hidden and the photograph remains;
- the Ken Burns pan is removed;
- title/subtitle entrance animations are removed;
- hover transforms and the looping status dot keep a static presentation.

## Accessibility

- Real headings (`h1`, `h2`, `h3`), landmarks (`section`) and lists (`ol`).
- Every gallery image has descriptive alternative text; the decorative hero
  poster and threat background intentionally use empty `alt` text.
- Hero actions are native Streamlit buttons with keyboard focus and a visible
  primary/secondary hierarchy.
- Text over imagery sits on a multi-stop dark gradient designed to preserve
  contrast regardless of the video frame.
- `prefers-reduced-motion` is respected at both the shared and page level.
- Decorative overlays use `aria-hidden` or `pointer-events: none`.

## Responsive behaviour

- Gallery: four columns at desktop, two at tablet, one at mobile; the
  backwaters tile is the editorial anchor at larger sizes.
- Hazard and flow grids: three/four columns at desktop, two at tablet, one at
  mobile.
- Workspace cards: two columns at desktop, stacked on narrow screens.
- The CTA dock overlaps the hero bottom edge on desktop; on small screens it
  becomes a normal stacked block with the note underneath the buttons.
- Coordinates, the scroll cue and the hero footer are hidden on small screens
  to protect readability.
- The shared top navigation collapses to Streamlit's mobile menu without
  duplicating navigation state.

## Performance

- All photography is local; no external image or font request is required.
- Gallery and threat images use `loading="lazy"` and `decoding="async"`.
- The hero poster is the only eager image, with `fetchpriority="high"`.
- The video uses `preload="metadata"`, not a full preload.
- CSS animations are limited to opacity/transform and a light grain overlay;
  there is no JavaScript animation loop.
- The combined local image payload is about 2 MB, with individual files
  between roughly 77 KB and 440 KB. Re-encode large files if you replace them.

## Scientific safeguards kept on the homepage

The page explicitly states that:

- this is a research prototype, not an official warning service;
- scenario outputs are not automatically validated probabilities;
- historical observations do not prove current conditions or identify a
  pollution source;
- in an emergency, users should follow KSDMA, IMD and district-administration
  guidance;
- photography is illustrative context, not evidence of a specific event.

These statements are part of the experience, not a footnote added after the
design.

## How to customise

| Change | Where |
| --- | --- |
| Hero copy and CTA labels | `app_pages/home.py`, hero and CTA sections |
| Chapter copy | `app_pages/home.py`, sections 01–04 |
| Gallery images | Replace files in `static/images/` and update `src`/`alt`/credits |
| Threat cards and icons | `app_pages/home.py` (`ICON_*`, `.ar-hazard` markup) |
| Workspace groups and links | `navigation_groups` in `app_pages/home.py` |
| Shared colours, buttons, nav, motion | `app.py` `<style>` block |
| Hero video | Drop `assets/videos/kerala_hero.mp4` in place — no code change |
| Theme and static serving | `.streamlit/config.toml` |

Keep `enableStaticServing = true` in `.streamlit/config.toml` for both images
and video. Static files are served under `app/static/<path>`.

## Verification

The implementation was checked with:

```bash
python3 -m py_compile app.py app_pages/home.py
```

and with Streamlit's `AppTest` harness (see `test_homepage.py`):

- the app entry point runs with no exceptions;
- the homepage is the default page;
- all 11 workspace links resolve;
- both CTAs navigate to their target pages;
- the local hero photograph is always referenced;
- no `<video>` element is emitted when no source file exists;
- when a source file is present, it is copied to `static/videos/` and the
  `<video>` element is emitted with a local source and the local poster;
- every registered workspace page runs without an exception under the shared
  CSS and navigation.

A headless Chrome pass against a running server also confirmed:

- the hero poster, optional video and threat background compute to
  `object-fit: cover`;
- all eight local images load with no broken requests and no horizontal
  overflow at 1440, 820 and 390 px;
- the gallery and hazard grids collapse to the intended column counts;
- the top-nav section buttons show hover and expanded states, and the dropdown
  popover uses the dark surface styling;
- `prefers-reduced-motion: reduce` hides the video, stops the Ken Burns pan and
  entrance animations, and leaves the static composition readable.

The targeted Streamlit regression suite was run with:

```bash
pytest -q test_homepage.py test_decision_workflow_streamlit.py \
  test_hospital_module_ui.py test_flood_readiness_ui.py
```

Run the full project suite before presenting or deploying:

```bash
pytest
```

Visual appearance still needs a browser check on the target display sizes,
because automated tests cannot judge composition, image crops or contrast over
every video frame.

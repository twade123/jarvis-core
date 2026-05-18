---
name: remotion
description: Create and edit videos programmatically using React with Remotion. Use when the user mentions "remotion," "make a video," "create a video," "video from code," "programmatic video," "animate with React," "render video," "video composition," "video editing with code," "generate video," "React video," "motion graphics," "animated explainer," "slideshow video," "social media video," "video template," or asks to build, edit, or render any video content. Also use when working with existing Remotion projects, adding scenes, transitions, or animations, or rendering compositions to MP4/WebM. Covers project setup, compositions, animations, transitions, media handling, and CLI rendering.
---

# Remotion — Programmatic Video with React

Create videos by writing React components. Each frame is a React render. All of CSS, Canvas, SVG, and WebGL work.

**Official LLM rules from Remotion**: All output must be valid React + TypeScript. Never use `Math.random()` — use `random(seed)` from remotion for deterministic renders.

## Quick Start

```bash
npx create-video@latest       # Create new project
npm start                      # Preview at localhost:3000
npx remotion render MyComp     # Render to out/MyComp.mp4
```

## Project Structure

```
my-video/
├── src/
│   ├── index.ts          # registerRoot(Root)
│   ├── Root.tsx           # Composition definitions
│   └── MyComp.tsx         # Video component
├── public/                # Static assets (use staticFile())
└── remotion.config.ts     # Optional config
```

## Composition Registration (Root.tsx)

```tsx
import {Composition} from 'remotion';
import {MyVideo} from './MyVideo';

export const Root: React.FC = () => (
  <>
    <Composition
      id="MyVideo"
      component={MyVideo}
      durationInFrames={300}   // 10 seconds at 30fps
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{title: "Hello"}}
    />
  </>
);
```

## Core Hooks

```tsx
import {useCurrentFrame, useVideoConfig} from 'remotion';

const frame = useCurrentFrame();           // 0-indexed frame number
const {fps, width, height, durationInFrames} = useVideoConfig();
```

## Animation

### interpolate() — Linear mapping

```tsx
import {interpolate} from 'remotion';

// Fade in over first 30 frames
const opacity = interpolate(frame, [0, 30], [0, 1], {
  extrapolateRight: 'clamp',
});

// Slide from left
const translateX = interpolate(frame, [0, 60], [-200, 0], {
  extrapolateLeft: 'clamp',
  extrapolateRight: 'clamp',
});
```

### spring() — Physics-based motion

```tsx
import {spring} from 'remotion';

const scale = spring({fps, frame, config: {damping: 200}});
// Returns 0→1 with overshoot. Use for entrances, bounces.
```

## Timing & Sequencing

### Sequence — Time-shift components

```tsx
import {Sequence, AbsoluteFill} from 'remotion';

<AbsoluteFill>
  <Sequence from={0} durationInFrames={90}>
    <Scene1 />
  </Sequence>
  <Sequence from={90} durationInFrames={90}>
    <Scene2 />
  </Sequence>
</AbsoluteFill>
```

Children's `useCurrentFrame()` resets to 0 at the Sequence start.

### Series — Sequential playback

```tsx
import {Series} from 'remotion';

<Series>
  <Series.Sequence durationInFrames={90}><Scene1 /></Series.Sequence>
  <Series.Sequence durationInFrames={90}><Scene2 /></Series.Sequence>
</Series>
```

### TransitionSeries — Animated transitions between scenes

```tsx
import {TransitionSeries} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide} from '@remotion/transitions/slide';
import {springTiming} from '@remotion/transitions';

<TransitionSeries>
  <TransitionSeries.Sequence durationInFrames={90}>
    <Scene1 />
  </TransitionSeries.Sequence>
  <TransitionSeries.Transition
    presentation={fade()}
    timing={springTiming({config: {damping: 200}})}
  />
  <TransitionSeries.Sequence durationInFrames={90}>
    <Scene2 />
  </TransitionSeries.Sequence>
</TransitionSeries>
```

**Presentations**: `fade()`, `slide()`, `wipe()`, `flip()`, `clockWipe()`, `iris()`, `cube()`, `none()`

## Media

### Assets — use staticFile() for public/ folder

```tsx
import {Img, staticFile} from 'remotion';
import {Audio} from '@remotion/media';
import {OffthreadVideo} from '@remotion/media';

<Img src={staticFile('logo.png')} />
<Audio src={staticFile('music.mp3')} volume={0.5} />
<OffthreadVideo src={staticFile('clip.mp4')} />

// Remote URLs work too
<Img src="https://example.com/image.png" />
```

### Layout

```tsx
import {AbsoluteFill} from 'remotion';

// Full-frame layer (stack multiple for layering)
<AbsoluteFill style={{backgroundColor: '#000'}}>
  <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
    <h1 style={{color: 'white', fontSize: 80}}>Title</h1>
  </AbsoluteFill>
</AbsoluteFill>
```

## Rendering

```bash
# Render specific composition
npx remotion render MyVideo out/video.mp4

# With props
npx remotion render MyVideo --props='{"title":"Hello"}'

# Different codecs
npx remotion render MyVideo out/video.webm --codec=vp8
npx remotion render MyVideo out/video.mov --codec=prores

# Scale output (1.5x = 1920x1080 → 2880x1620)
npx remotion render MyVideo --scale=1.5

# Render still image
npx remotion still MyVideo out/thumb.png --frame=60

# GIF
npx remotion render MyVideo out/anim.gif --codec=gif
```

**Codecs**: `h264` (default), `h265`, `vp8`, `vp9`, `prores`, `gif`, `png` (image sequence)

## Rules for AI-Generated Remotion Code

1. All code must be valid React + TypeScript
2. Never use `Math.random()` — use `random(seed)` from remotion
3. Use `<Img>` not `<img>`, `<OffthreadVideo>` not `<video>`
4. Always set `extrapolateRight: 'clamp'` on interpolate to prevent overshoot
5. Frame 0 is the first frame, `durationInFrames - 1` is the last
6. Use `staticFile()` for local assets, not relative paths
7. Keep components pure — no side effects, no fetch in render

## Common Patterns

For detailed examples of specific video types (slideshows, data visualizations, social clips, text animations, kinetic typography), see `references/patterns.md`.

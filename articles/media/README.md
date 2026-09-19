# articles/media/

Screenshots (`.png`/`.jpg`) are tracked in git normally.

Video clips (`.mp4`/`.mov`/`.webm`) from Day 3's `gemini-omni-1.1-flash`
renders are **not** committed — they're git-ignored (see `.gitignore`) and
synced between hosts with rsync instead, the same convention used for
`hisp_training_video` (large binaries don't belong in git history).

dev-box is the source of truth (that's where the render step runs). To pull
the latest clips onto another host:

```bash
rsync -avz --progress dev-box:~/workspace/lab/jev-storyboard-lab/articles/media/ \
  ~/workspace/lab/jev-storyboard-lab/articles/media/
```

(swap `dev-box` for the alias set in that host's `~/.ssh/config`, e.g. run
this *from* ts-m1 pulling *from* dev-box.)

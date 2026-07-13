# Contributing

## Principles

1. **Skills** describe job procedure and I/O contracts — keep them short.
2. **Knowledge** holds reusable film grammar (JSON rules preferred for camera/look).
3. **FilmBible** holds per-project state only.
4. Agents must not freely chat; the orchestrator owns sequencing.

## Add a new style pack

1. Create `knowledge/style_packs/<id>.json`
2. Run: `film-pipeline run --script ... --project demo --style <id>`

## Add a knowledge rule

Edit `knowledge/camera/emotion_to_camera.json` or `knowledge/look/emotion_to_look.json`.
Offline dry-run cinematography/look stubs will pick them up immediately.

## Add / change a skill

1. Edit `skills/<stage>/SKILL.md`
2. Keep `skills/<stage>/schema.json` in sync
3. Update merger in `film_pipeline/runtime/agent_runner.py` if write fields change
4. Update offline stub if dry-run should demonstrate the change

## Tests

```bash
pytest
```

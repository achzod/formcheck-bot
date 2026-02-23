# TASK: Fix morpho_profiler.py for MediaPipe Tasks API

## Problem
`src/analysis/morpho_profiler.py` uses the OLD MediaPipe API (`mp.solutions.pose`) which doesn't exist in MediaPipe 0.10.32. The new API uses `mediapipe.tasks.python.vision.PoseLandmarker`.

## Reference
Look at `src/analysis/pose_extractor.py` — it already uses the correct Tasks API with:
- `mediapipe.tasks.python.vision.PoseLandmarker`
- `pose_landmarker_heavy.task` model downloaded to `src/analysis/models/`
- `mp.Image` for image input
- Landmarks accessed via `result.pose_landmarks[0]` (list of NormalizedLandmark)

## What to fix in morpho_profiler.py
1. Replace `mp.solutions.pose` with the Tasks API (`PoseLandmarker`)
2. Use the same model path as pose_extractor (`src/analysis/models/pose_landmarker_heavy.task`)
3. Update `_extract_landmarks_from_image()` to use `PoseLandmarker.create_from_options()` with `static_image_mode` equivalent
4. Landmark access: in Tasks API landmarks are `NormalizedLandmark` objects with `.x`, `.y`, `.z`, `.visibility`
5. Landmark indices: use integer indices (same as before: 0=nose, 7=left_ear, 11=left_shoulder, 12=right_shoulder, 23=left_hip, 24=right_hip, 25=left_knee, 26=right_knee, 27=left_ankle, 28=right_ankle, 13=left_elbow, 14=right_elbow, 15=left_wrist, 16=right_wrist)
6. Keep ALL existing logic (measurements, ratios, posture, recommendations) — only change the MediaPipe interface

## Key differences in Tasks API
- Create landmarker: `PoseLandmarker.create_from_options(options)`
- Options: `PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=path), running_mode=VisionRunningMode.IMAGE, num_poses=1)`
- Detect: `result = landmarker.detect(mp_image)` where `mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_array)`
- Landmarks: `result.pose_landmarks[0]` is a list of NormalizedLandmark
- Each landmark: `.x`, `.y`, `.z`, `.visibility` (same as before)

## Constraints
- Do NOT change any analysis logic, just the MediaPipe interface
- Do NOT break any existing imports or function signatures
- Test that `from src.analysis.morpho_profiler import analyze_morphology, MorphoProfile` works
- Use the venv at `./venv/` (Python 3.14, MediaPipe 0.10.32)

## Test
```bash
source venv/bin/activate
python3 -c "from src.analysis.morpho_profiler import analyze_morphology, MorphoProfile; print('OK')"
```

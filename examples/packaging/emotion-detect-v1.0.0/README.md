# Emotion Detection — Artic Module Example

A simple keyword-based emotion detection module, packaged in `.amod` format per the [Artic Protocol](https://github.com/SpicySugar16/artic-protocol) packaging spec.

## Usage

```bash
# Install
engine install emotion-detect-v1.0.0.amod

# Test
echo '{"id":"test-1","kind":"request","to":"emotion.detect","payload":{"text":"I am so happy!"}}' | python3 module/main.py
# → {"id":"test-1","from":"emotion.detect","kind":"response","payload":{"primary":"joy","scores":{"joy":0.5,...},"confidence":0.5}}
```

## Structure

```
emotion-detect-v1.0.0/
├── manifest.toml       # Module metadata and declaration
├── module/
│   └── main.py         # Entry point
├── tests/
│   └── test_detect.py  # Unit tests
├── assets/
│   └── icons/          # Module icon
└── README.md
```

## Build

```bash
cd examples/packaging
tar -czf emotion-detect-v1.0.0.amod emotion-detect-v1.0.0/
```

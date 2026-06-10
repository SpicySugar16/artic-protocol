"""Tests for emotion-detect module."""
import json
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from module.main import detect_emotion


class TestEmotionDetect(unittest.TestCase):

    def test_joy(self):
        result = detect_emotion("I am so happy and wonderful!")
        self.assertEqual(result["primary"], "joy")
        self.assertGreater(result["confidence"], 0)

    def test_sadness(self):
        result = detect_emotion("I feel so sad and miss you")
        self.assertEqual(result["primary"], "sadness")

    def test_neutral(self):
        result = detect_emotion("The weather is fine today.")
        self.assertEqual(result["primary"], "neutral")
        self.assertEqual(result["confidence"], 0.0)

    def test_emoji_detection(self):
        result = detect_emotion("That's incredible! 😲")
        self.assertEqual(result["primary"], "surprise")

    def test_mixed_emotions(self):
        result = detect_emotion("I love you but I'm also angry")
        self.assertIn(result["primary"], ["joy", "anger"])


if __name__ == "__main__":
    unittest.main()

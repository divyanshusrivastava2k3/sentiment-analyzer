"""Sentiment analysis engine built on Hugging Face Transformers.

Loads a 3-class sentiment model once at startup and scores text batches.
"""
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from config import Config

# Model label order for cardiffnlp/twitter-roberta-base-sentiment-latest
LABEL_MAP = {"negative": "negative", "neutral": "neutral", "positive": "positive"}


class SentimentEngine:
    """Wraps a Hugging Face sentiment classification pipeline."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or Config.MODEL_NAME
        self._tokenizer = None
        self._model = None

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        return self._tokenizer

    @property
    def model(self):
        if self._model is None:
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name
            )
            self._model.eval()
        return self._model

    def analyze_batch(self, texts):
        """Score a list of texts. Returns list of dicts with label + confidence."""
        results = []
        batch_size = 16
        for start in range(0, len(texts), batch_size):
            chunk = [t[:512] for t in texts[start:start + batch_size]]
            inputs = self.tokenizer(
                chunk,
                padding=True,
                truncation=True,
                max_length=256,
                return_tensors="pt",
            )
            with torch.no_grad():
                logits = self.model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)
            for row in probs:
                idx = int(row.argmax())
                label = self.model.config.id2label[idx].lower()
                # Normalize e.g. "LABEL_0"/"negative" -> canonical name
                label = LABEL_MAP.get(label, label)
                results.append({"label": label, "confidence": round(float(row[idx]), 4)})
        return results


engine = SentimentEngine()

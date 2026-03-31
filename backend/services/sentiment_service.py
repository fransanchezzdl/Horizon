"""
Servicio de análisis de sentimiento usando FinBERT.

FinBERT es un modelo BERT fine-tuned en datos financieros.
Disponible en HuggingFace: ProsusAI/finbert
"""

import logging
from typing import List, Dict, Optional, Tuple
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

# Cache de modelo para no recargar en cada call
_finbert_model = None
_finbert_tokenizer = None


class SentimentService:
    """Servicio para análisis de sentimiento financiero."""
    
    # Mapeo de labels a scores numéricos
    LABEL_TO_SCORE = {
        "positive": 1.0,
        "neutral": 0.0,
        "negative": -1.0,
    }
    
    @staticmethod
    def initialize_model() -> bool:
        """
        Inicializa el modelo FinBERT y tokenizer.
        
        Returns:
            bool: True si éxito, False si error
        """
        
        global _finbert_model, _finbert_tokenizer
        
        if _finbert_model is not None and _finbert_tokenizer is not None:
            logger.debug("FinBERT model already loaded")
            return True
        
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            
            logger.info("Loading FinBERT model from HuggingFace...")
            
            model_name = "ProsusAI/finbert"
            
            _finbert_tokenizer = AutoTokenizer.from_pretrained(model_name)
            _finbert_model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            # Move to CPU (o GPU si disponible)
            try:
                import torch
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                _finbert_model = _finbert_model.to(device)
                logger.info(f"Model loaded on device: {device}")
            except ImportError:
                logger.warning("PyTorch not available, using default device")
            
            logger.info("FinBERT model initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error initializing FinBERT model: {str(e)}")
            logger.warning("Sentiment analysis will not work without FinBERT")
            return False
    
    @staticmethod
    def analyze_text(text: str, max_length: int = 512) -> Dict:
        """
        Analiza sentimiento de un texto.
        
        Args:
            text: Texto a analizar (headline o descripción)
            max_length: Max tokens
        
        Returns:
            Dict con:
            {
                "label": "positive" | "neutral" | "negative",
                "score": float (-1 to 1),
                "confidence": float (0 to 1)
            }
        """
        
        try:
            if _finbert_model is None or _finbert_tokenizer is None:
                logger.warning("FinBERT not initialized")
                return {
                    "label": "neutral",
                    "score": 0.0,
                    "confidence": 0.0
                }
            
            import torch
            
            # Tokenizar
            inputs = _finbert_tokenizer(
                text,
                max_length=max_length,
                truncation=True,
                return_tensors="pt"
            )
            
            # Predicción
            with torch.no_grad():
                outputs = _finbert_model(**inputs)
                logits = outputs.logits
            
            # Sofmax para confidencia
            probs = torch.nn.functional.softmax(logits, dim=-1)
            predicted_class = torch.argmax(logits, dim=-1).item()
            confidence = probs[0, predicted_class].item()
            
            # Mapear a labels
            labels = ["positive", "negative", "neutral"]  # Order in FinBERT
            label = labels[predicted_class]
            score = SentimentService.LABEL_TO_SCORE.get(label, 0.0)
            
            return {
                "label": label,
                "score": score,
                "confidence": confidence
            }
        
        except Exception as e:
            logger.error(f"Error analyzing text: {str(e)}")
            return {
                "label": "neutral",
                "score": 0.0,
                "confidence": 0.0
            }
    
    @staticmethod
    def analyze_articles(articles: List[Dict]) -> List[Dict]:
        """
        Analiza sentimiento de múltiples artículos.
        
        Args:
            articles: List of articles from NewsService
        
        Returns:
            Mismo list pero con campo "sentiment" llenado
        """
        
        logger.info(f"Analyzing sentiment for {len(articles)} articles...")
        
        for i, article in enumerate(articles):
            # Usar headline + descripción
            text_to_analyze = f"{article.get('title', '')} {article.get('description', '')}"
            
            if not text_to_analyze.strip():
                article["sentiment"] = {
                    "label": "neutral",
                    "score": 0.0,
                    "confidence": 0.0
                }
                continue
            
            sentiment = SentimentService.analyze_text(text_to_analyze)
            article["sentiment"] = sentiment
            
            if (i + 1) % 10 == 0:
                logger.debug(f"  Analyzed {i + 1}/{len(articles)} articles")
        
        logger.info(f"Sentiment analysis complete for {len(articles)} articles")
        return articles
    
    @staticmethod
    def aggregate_daily_sentiment(
        articles: List[Dict],
        date_field: str = "publishedAt"
    ) -> Dict[str, Dict]:
        """
        Agrega sentimiento por día.
        
        Args:
            articles: Artículos con sentimiento
            date_field: Campo con fecha (ISO 8601)
        
        Returns:
            Dict[date] -> {
                "positive_count": int,
                "negative_count": int,
                "neutral_count": int,
                "avg_score": float,
                "std_score": float,
                "total_articles": int
            }
        """
        
        daily_stats = {}
        
        for article in articles:
            if article.get("sentiment") is None:
                continue
            
            # Extraer fecha
            pub_date = article.get(date_field, "")
            if not pub_date:
                continue
            
            # ISO format: "2026-03-30T10:30:00Z" -> "2026-03-30"
            date_str = pub_date.split("T")[0] if "T" in pub_date else pub_date
            
            if date_str not in daily_stats:
                daily_stats[date_str] = {
                    "positive_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                    "scores": [],
                    "articles": []
                }
            
            sentiment = article["sentiment"]
            label = sentiment.get("label", "neutral")
            score = sentiment.get("score", 0.0)
            
            # Contar
            if label == "positive":
                daily_stats[date_str]["positive_count"] += 1
            elif label == "negative":
                daily_stats[date_str]["negative_count"] += 1
            else:
                daily_stats[date_str]["neutral_count"] += 1
            
            daily_stats[date_str]["scores"].append(score)
            daily_stats[date_str]["articles"].append(article)
        
        # Calcular stats
        for date_str, stats in daily_stats.items():
            total = stats["positive_count"] + stats["negative_count"] + stats["neutral_count"]
            stats["total_articles"] = total
            
            if stats["scores"]:
                stats["avg_score"] = float(np.mean(stats["scores"]))
                stats["std_score"] = float(np.std(stats["scores"]))
            else:
                stats["avg_score"] = 0.0
                stats["std_score"] = 0.0
            
            # Limpiar scores para serialización
            del stats["scores"]
            del stats["articles"]
        
        return daily_stats
    
    @staticmethod
    def rolling_sentiment_features(
        daily_stats: Dict[str, Dict],
        windows: List[int] = [5, 10, 20]
    ) -> Dict[str, Dict]:
        """
        Calcula features de sentimiento en ventanas rolling.
        
        Args:
            daily_stats: Dict de stats diarios
            windows: Ventanas (5, 10, 20 días)
        
        Returns:
            Dict[date] -> {
                "sentiment_rolling_5d": float,
                "positive_pct_5d": float,
                "negative_pct_5d": float,
                "sentiment_rolling_10d": float,
                ...
            }
        """
        
        # Ordenar por fecha
        dates = sorted(daily_stats.keys())
        date_to_idx = {d: i for i, d in enumerate(dates)}
        
        rolling_features = {}
        
        for date_str in dates:
            idx = date_to_idx[date_str]
            rolling_features[date_str] = {}
            
            for window in windows:
                # Ventana: últimos `window` días
                start_idx = max(0, idx - window + 1)
                window_dates = dates[start_idx:idx + 1]
                
                window_stats = [daily_stats[d] for d in window_dates]
                
                # Agregados
                total_articles = sum(s["total_articles"] for s in window_stats)
                total_pos = sum(s["positive_count"] for s in window_stats)
                total_neg = sum(s["negative_count"] for s in window_stats)
                total_neutral = sum(s["neutral_count"] for s in window_stats)
                
                avg_scores = [s["avg_score"] for s in window_stats if s["total_articles"] > 0]
                
                # Features
                key_prefix = f"sentiment_{window}d"
                
                rolling_features[date_str][f"{key_prefix}_avg"] = \
                    float(np.mean(avg_scores)) if avg_scores else 0.0
                
                rolling_features[date_str][f"{key_prefix}_std"] = \
                    float(np.std(avg_scores)) if avg_scores else 0.0
                
                rolling_features[date_str][f"positive_pct_{window}d"] = \
                    float(total_pos / total_articles) if total_articles > 0 else 0.0
                
                rolling_features[date_str][f"negative_pct_{window}d"] = \
                    float(total_neg / total_articles) if total_articles > 0 else 0.0
                
                rolling_features[date_str][f"positive_count_{window}d"] = total_pos
                rolling_features[date_str][f"negative_count_{window}d"] = total_neg
        
        return rolling_features


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    
    print("Testing SentimentService...")
    
    # Inicializar modelo
    success = SentimentService.initialize_model()
    if not success:
        print("Failed to initialize model. Check installation.")
        exit(1)
    
    # Test single text
    test_texts = [
        "Apple announces record profits and launches new product",
        "Tesla stock crashes after disappointing earnings",
        "Microsoft continues regular business as expected"
    ]
    
    print("\nSingle text analysis:")
    for text in test_texts:
        result = SentimentService.analyze_text(text)
        print(f"  '{text[:50]}...' -> {result['label']} ({result['score']:.2f})")
    
    # Test articles
    test_articles = [
        {
            "title": "Apple beats expectations",
            "description": "Stock surges on strong earnings",
            "publishedAt": "2026-03-30T10:00:00Z"
        },
        {
            "title": "Market crash fears",
            "description": "Economic crisis looms",
            "publishedAt": "2026-03-30T11:00:00Z"
        }
    ]
    
    print("\nArticle analysis:")
    articles = SentimentService.analyze_articles(test_articles)
    for article in articles:
        print(f"  {article['title'][:40]} -> {article['sentiment']['label']}")

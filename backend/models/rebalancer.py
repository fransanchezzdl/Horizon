"""
Rebalanceo avanzado de clases con SMOTE y técnicas adaptativas.
Detecta desbalanceo y aplica estrategias según severidad.
"""

import numpy as np
import warnings
from typing import Tuple, Optional
from sklearn.utils import resample

warnings.filterwarnings('ignore')


class AdaptiveClassRebalancer:
    """
    Rebalanceo adaptativo según ratio de desbalanceo.
    
    - Leve (1.5-2.5x): class_weight + data augmentation leve
    - Moderado (2.5-4x): SMOTE básico
    - Severo (4x+): SMOTE + oversampling agresivo + threshold ajustado
    """
    
    @staticmethod
    def calculate_imbalance_ratio(y: np.ndarray) -> Tuple[float, dict]:
        """Calcula ratio de desbalanceo y distribución"""
        unique, counts = np.unique(y, return_counts=True)
        distribution = dict(zip(unique, counts))
        
        # Garantizar que todas las clases existen
        for i in range(3):
            if i not in distribution:
                distribution[i] = 0
        
        max_count = max(distribution.values())
        min_count = min([c for c in distribution.values() if c > 0])
        
        ratio = max_count / (min_count + 1e-6)
        
        return ratio, distribution
    
    @staticmethod
    def get_rebalance_strategy(imbalance_ratio: float, ticker: str = "") -> str:
        """Determina estrategia según severidad y tipo de activo"""
        # Para commodities, usar solo class_weights (sin generar sintéticos)
        if ticker in ['GC=F', 'SI=F']:
            return "light"  # Solo class_weights, no SMOTE
        
        if imbalance_ratio < 1.5:
            return "none"
        elif imbalance_ratio < 2.5:
            return "light"
        elif imbalance_ratio < 4:
            return "moderate"
        else:
            return "severe"
    
    @staticmethod
    def get_class_weights(y: np.ndarray) -> dict:
        """
        Calcula pesos de clase para balancear automaticamente en loss.
        Estándar de sklearn: weight = n_samples / (n_classes * n_samples_class)
        """
        unique, counts = np.unique(y, return_counts=True)
        n_samples = len(y)
        n_classes = len(unique)
        
        weights = {}
        for cls, count in zip(unique, counts):
            weights[int(cls)] = n_samples / (n_classes * count) if count > 0 else 1.0
        
        # Normalizar para que el promedio sea 1
        avg_weight = sum(weights.values()) / len(weights)
        weights = {k: v / avg_weight for k, v in weights.items()}
        
        return weights
    
    @staticmethod
    def simple_smote(X: np.ndarray, y: np.ndarray, target_ratio: float = 0.8) -> Tuple[np.ndarray, np.ndarray]:
        """
        SMOTE simple: generar puntos sintéticos entre minoritaria y mayoría.
        
        Args:
            X: Features (n_samples, n_features)
            y: Labels (n_samples,)
            target_ratio: Ratio objetivo minoritaria/mayoría (default 0.8, i.e., 80% de mayoría)
            
        Returns:
            X_balanced, y_balanced
        """
        unique, counts = np.unique(y, return_counts=True)
        
        if len(unique) == 1:  # Solo una clase, no hacer nada
            return X, y
        
        # Encontrar clase minoritaria
        min_class = unique[np.argmin(counts)]
        max_class = unique[np.argmax(counts)]
        
        n_min = counts[unique == min_class][0]
        n_max = counts[unique == max_class][0]
        
        # Calcular cuántas muestras sintéticas crear
        target_n_min = max(n_min, int(n_max * target_ratio))
        n_synthetic = target_n_min - n_min
        
        if n_synthetic <= 0:
            return X, y
        
        # Índices de clase minoritaria
        min_idx = np.where(y == min_class)[0]
        
        # Crear puntos sintéticos
        synthetic_X = []
        for _ in range(n_synthetic):
            # Seleccionar dos puntos aleatorios de la minoritaria
            idx1, idx2 = np.random.choice(min_idx, 2, replace=True)
            
            # Interpolar entre ellos
            alpha = np.random.random()
            synthetic_point = alpha * X[idx1] + (1 - alpha) * X[idx2]
            synthetic_X.append(synthetic_point)
        
        # Combinar datos originales con sintéticos
        X_synthetic = np.vstack(synthetic_X)
        y_synthetic = np.ones(n_synthetic, dtype=int) * min_class
        
        X_balanced = np.vstack([X, X_synthetic])
        y_balanced = np.hstack([y, y_synthetic])
        
        # Shuffle
        idx = np.random.permutation(len(y_balanced))
        
        return X_balanced[idx], y_balanced[idx]
    
    @staticmethod
    def rebalance(
        X: np.ndarray,
        y: np.ndarray,
        strategy: Optional[str] = None,
        return_class_weights: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, dict]:
        """
        Rebalanceia datos según estrategia adaptativa.
        
        Args:
            X: Features
            y: Labels (0=BAJISTA, 1=LATERAL, 2=ALCISTA)
            strategy: None (auto-detect), 'none', 'light', 'moderate', 'severe'
            return_class_weights: Devolver también pesos de clase para loss
            
        Returns:
            X_balanced, y_balanced, class_weights_dict
        """
        ratio, distribution = AdaptiveClassRebalancer.calculate_imbalance_ratio(y)
        
        if strategy is None:
            strategy = AdaptiveClassRebalancer.get_rebalance_strategy(ratio)
        
        class_weights = AdaptiveClassRebalancer.get_class_weights(y)
        
        if strategy == "none":
            return X, y, class_weights
        
        elif strategy == "light":
            # Solo usar class_weights, no aumentar datos
            return X, y, class_weights
        
        elif strategy == "moderate":
            # SMOTE ligero (target ratio 0.8)
            X_balanced, y_balanced = AdaptiveClassRebalancer.simple_smote(
                X, y, target_ratio=0.8
            )
            # Recalcular pesos
            class_weights = AdaptiveClassRebalancer.get_class_weights(y_balanced)
            return X_balanced, y_balanced, class_weights
        
        else:  # severe
            # SMOTE agresivo (target ratio 1.0 - todas las clases iguales)
            X_balanced, y_balanced = AdaptiveClassRebalancer.simple_smote(
                X, y, target_ratio=1.0
            )
            # Recalcular pesos
            class_weights = AdaptiveClassRebalancer.get_class_weights(y_balanced)
            return X_balanced, y_balanced, class_weights


def describe_rebalancing(original_distribution: dict, new_distribution: dict) -> str:
    """Describe cambios en distribución de clases"""
    class_names = {0: 'BAJISTA', 1: 'LATERAL', 2: 'ALCISTA'}
    
    msg = "Rebalancing summary:\n"
    for cls in range(3):
        orig = original_distribution.get(cls, 0)
        new = new_distribution.get(cls, 0)
        pct_orig = 100 * orig / sum(original_distribution.values())
        pct_new = 100 * new / sum(new_distribution.values())
        
        change = "↑" if new > orig else "↓" if new < orig else "→"
        msg += f"  {class_names[cls]:8s}: {orig:5d} ({pct_orig:5.1f}%) → {new:5d} ({pct_new:5.1f}%) {change}\n"
    
    return msg


if __name__ == "__main__":
    # Test simple
    print("Testing AdaptiveClassRebalancer\n")
    
    # Simulación desbalanceada: 1000 LATERAL, 200 ALCISTA, 150 BAJISTA
    y_test = np.hstack([
        np.zeros(150, dtype=int),  # BAJISTA
        np.ones(1000, dtype=int),   # LATERAL
        np.ones(200, dtype=int) * 2  # ALCISTA
    ])
    X_test = np.random.randn(len(y_test), 25)  # 25 features
    
    ratio, dist = AdaptiveClassRebalancer.calculate_imbalance_ratio(y_test)
    print(f"Original imbalance ratio: {ratio:.2f}x")
    print(f"Original distribution: BAJISTA={dist[0]}, LATERAL={dist[1]}, ALCISTA={dist[2]}")
    
    strategy = AdaptiveClassRebalancer.get_rebalance_strategy(ratio)
    print(f"Detected strategy: {strategy}\n")
    
    X_bal, y_bal, weights = AdaptiveClassRebalancer.rebalance(X_test, y_test)
    
    ratio_new, dist_new = AdaptiveClassRebalancer.calculate_imbalance_ratio(y_bal)
    print(f"New imbalance ratio: {ratio_new:.2f}x")
    print(f"New distribution: BAJISTA={dist_new[0]}, LATERAL={dist_new[1]}, ALCISTA={dist_new[2]}")
    print(f"Class weights: {weights}")
    print("\n" + describe_rebalancing(dist, dist_new))
